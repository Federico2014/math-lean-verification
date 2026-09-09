"""Run builds/exports and both proof checkers in separate disposable containers.

No candidate program, Lake configuration, olean, or stdout verdict is trusted.
Only the trusted controller's comparison and checker exit statuses grant a pass.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import subprocess
import tempfile
import time
import uuid

from .registry import (RegistryError, VerificationError, STANDARD_AXIOMS,
                       require, canonical_digest)

PROFILE = 'lean-4-34-rc2-stdlib'
NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_']*(?:\.[A-Za-z_][A-Za-z0-9_']*)*\Z")
MAX_LOG = 2 * 1024 * 1024
DEFAULT_RESOURCES = {'memory_mb': 4096, 'cpus': 2, 'work_mb': 1024,
                     'timeout_seconds': 1800, 'max_files': 100,
                     'max_source_mb': 8, 'max_export_mb': 128}


def sandbox(image: str, inputs: Path, command: list[str], *, timeout=600,
            max_stdout=MAX_LOG, resources=None) -> tuple[int, bytes, bytes]:
    resources = resources or DEFAULT_RESOURCES
    from jsonschema import Draft202012Validator
    from .registry import ROOT, read_json
    limits = read_json(ROOT / 'schemas/environment.schema.json')['properties']['resources']
    require(Draft202012Validator(limits).is_valid(resources), 'Invalid sandbox resource policy')
    require(bool(re.fullmatch(r'sha256:[0-9a-f]{64}', image)), 'Expected immutable local image ID')
    require(inputs.is_dir() and not inputs.is_symlink(), 'Invalid sandbox input directory')
    name = 'lean-gate-' + uuid.uuid4().hex
    args = ['docker', 'run', '--name', name, '--rm', '--network=none', '--read-only',
            '--user=10001:10001', '--cap-drop=ALL', '--security-opt=no-new-privileges',
            '--security-opt=seccomp=' + str(Path(__file__).resolve().parents[1] / 'backend/seccomp.json'),
            '--pids-limit=128', f"--memory={resources['memory_mb']}m",
            f"--memory-swap={resources['memory_mb']}m", f"--cpus={resources['cpus']}",
            '--ulimit=nofile=256:256', '--ulimit=fsize=268435456:268435456',
            f"--tmpfs=/work:rw,nosuid,nodev,size={resources['work_mb'] * 1024**2},mode=1777",
            '--tmpfs=/tmp:rw,nosuid,nodev,noexec,size=268435456,mode=1777',
            '--mount', f'type=bind,src={inputs.resolve()},dst=/input,readonly',
            '--workdir=/work', image, *command]
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    chunks = {proc.stdout: bytearray(), proc.stderr: bytearray()}
    selector = selectors.DefaultSelector()
    for stream in chunks:
        selector.register(stream, selectors.EVENT_READ)
    deadline = time.monotonic() + timeout
    try:
        while selector.get_map():
            if time.monotonic() >= deadline:
                raise VerificationError('Sandbox execution timed out', 'infrastructure_error')
            for key, _ in selector.select(timeout=0.25):
                data = os.read(key.fileobj.fileno(), 65536)
                if not data:
                    selector.unregister(key.fileobj)
                    continue
                chunks[key.fileobj].extend(data)
                limit = max_stdout if key.fileobj is proc.stdout else MAX_LOG
                if len(chunks[key.fileobj]) > limit:
                    raise VerificationError('Sandbox output exceeds limit', 'infrastructure_error')
        code = proc.wait(timeout=max(1, deadline - time.monotonic()))
        return code, bytes(chunks[proc.stdout]), bytes(chunks[proc.stderr])
    finally:
        selector.close()
        if proc.poll() is None:
            proc.kill()
        proc.wait()
        proc.stdout.close()
        proc.stderr.close()
        subprocess.run(['docker', 'rm', '-f', name], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=30, check=False)


def copy_sources(source: Path, destination: Path, resources=None) -> None:
    """Only Lean source is accepted; never copy upstream builds or Lake programs."""
    require(source.is_dir() and not source.is_symlink(), 'Missing source directory')
    destination.mkdir()
    count = total = 0
    resources = resources or DEFAULT_RESOURCES
    for item in sorted(source.rglob('*')):
        require(not item.is_symlink(), 'Symlink in Lean source')
        if not item.is_file():
            continue
        rel = item.relative_to(source)
        require(item.suffix == '.lean', 'Only Lean source files are supported by the stdlib profile')
        require(all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', p) for p in rel.with_suffix('').parts),
                'Invalid Lean source path')
        total += item.stat().st_size
        count += 1
        require(count <= resources['max_files'] and total <= resources['max_source_mb'] * 1024**2,
                'Lean source package exceeds limit')
        out = destination / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(item, out)


def verify(image: str, challenge_sources: Path, solution_sources: Path,
           module: str, theorems: list[str], evidence: Path, environment=None,
           solution_declarations=None) -> dict:
    require(bool(NAME.fullmatch(module)), 'Invalid solution module')
    require(0 < len(theorems) <= 100 and len(theorems) == len(set(theorems)), 'Invalid targets')
    require(all(NAME.fullmatch(n) for n in theorems), 'Invalid theorem name')
    solution_declarations = solution_declarations or []
    require(len(solution_declarations) <= 100 and all(NAME.fullmatch(n) for n in solution_declarations),
            'Invalid upstream target declarations')
    require(not evidence.exists(), 'Evidence directory already exists')
    evidence.mkdir(parents=True)
    cfg = {'challenge_module': 'Challenge', 'solution_module': module,
           'theorem_names': theorems, 'definition_names': [], 'permitted_axioms': sorted(STANDARD_AXIOMS)}
    stages = []
    resources = environment['resources'] if environment else DEFAULT_RESOURCES
    result = {'schema_version': 1, 'profile': environment['environment_id'] if environment else PROFILE,
              'environment_digest': canonical_digest(environment) if environment else None,
              'resources': resources, 'image_id': image,
              'targets': theorems, 'candidate_targets': solution_declarations,
              'machine_status': 'failed', 'stages': stages,
              'seccomp_sha256': hashlib.sha256((Path(__file__).resolve().parents[1] / 'backend/seccomp.json').read_bytes()).hexdigest()}
    started = time.monotonic()
    executions = []
    result['executions'] = executions
    def execute(inputs, command, **kwargs):
        kwargs['timeout'] = min(kwargs.get('timeout', resources['timeout_seconds']), resources['timeout_seconds'])
        beginning = time.monotonic()
        index = len(executions)
        try:
            code, out, err = sandbox(image, inputs, command, resources=resources, **kwargs)
        except (RegistryError, OSError, ValueError, subprocess.SubprocessError) as exc:
            log = {'command': command, 'exit_code': None,
                   'duration_seconds': round(time.monotonic() - beginning, 3), 'error': str(exc)}
            (evidence / f'execution-{index}.json').write_text(json.dumps(log, indent=2) + '\n')
            executions.append(log)
            raise
        log = {'command': command, 'exit_code': code, 'duration_seconds': round(time.monotonic() - beginning, 3),
               'stdout_bytes': len(out), 'stderr': err.decode('utf-8', errors='replace')}
        if kwargs.get('max_stdout', MAX_LOG) <= MAX_LOG:
            log['stdout'] = out.decode('utf-8', errors='replace')
        (evidence / f'execution-{index}.json').write_text(json.dumps(log, indent=2) + '\n')
        executions.append({k: v for k, v in log.items() if k not in ('stdout', 'stderr')})
        if code:
            status = 'infrastructure_error' if code in (125, 126, 127, 137) or code < 0 else 'failed'
            raise VerificationError(f'Isolated stage rejected input (exit {code}): ' +
                                    json.dumps((err + out)[-8000:].decode('utf-8', errors='replace')), status)
        return out
    probe = ['python3', '/opt/gate/probe.py', str(resources['memory_mb']), str(resources['cpus'])]
    stage = 'sandbox_probes'
    try:
        with tempfile.TemporaryDirectory(prefix='lean-gate-') as temporary:
            root = Path(temporary)
            control = root / 'control'
            control.mkdir()
            (control / 'config.json').write_text(json.dumps(cfg))
            (evidence / 'config.json').write_text(json.dumps(cfg, indent=2) + '\n')
            execute(control, probe)
            stages.append('sandbox_probes')
            if environment:
                stage = 'environment_identity'
                identity = execute(control, ['cat', '/opt/environment/identity.json'])
                require(json.loads(identity)['environment_digest'] == canonical_digest(environment),
                        'Image does not match the approved environment')
                (evidence / 'environment.json').write_text(json.dumps(environment, indent=2) + '\n')
            stage = 'tool_identity'
            for filename in ['toolchain.json', 'binaries.sha256', 'system-packages.txt']:
                (evidence / filename).write_bytes(execute(control, ['cat', '/opt/gate/' + filename]))
            targets = execute(control, ['/opt/bin/gate-replay', '/input/config.json', 'targets'])
            target_names = json.loads(targets)
            require(isinstance(target_names, list) and all(isinstance(x, str) and NAME.fullmatch(x)
                    for x in target_names), 'Invalid trusted export target list')
            for kind, source, mod in [('challenge', challenge_sources, 'Challenge'),
                                      ('solution', solution_sources, module)]:
                stage = kind + '_source_preparation'
                package = root / kind
                package.mkdir()
                copy_sources(source, package / 'source', resources)
                export_targets = list(dict.fromkeys(target_names + (solution_declarations if kind == 'solution' else [])))
                (package / 'targets.json').write_text(json.dumps(export_targets))
                # Probe each actual input mount before executing any Lean source.
                stage = kind + '_sandbox_probes'
                execute(package, probe)
                stage = kind + '_clean_build_export'
                export = execute(package, ['python3', '/opt/gate/export.py', mod],
                                 max_stdout=resources['max_export_mb'] * 1024**2)
                require(bool(export), 'Empty proof export')
                (control / (kind + '.ndjson')).write_bytes(export)
                (evidence / (kind + '.ndjson')).write_bytes(export)
                stages.append(kind + '_clean_build_export')
            (control / 'required-targets.json').write_text(json.dumps(list(dict.fromkeys(theorems + solution_declarations))))
            shutil.copyfile(control / 'required-targets.json', evidence / 'required-targets.json')
            stage = 'candidate_target_coverage'
            execute(control, ['/opt/bin/gate-replay', '/input/config.json', 'required-targets',
                              '/input/solution.ndjson', '/input/required-targets.json'], timeout=1200)
            stages.append('candidate_target_coverage')
            stage = 'statement_axioms_and_official_replay'
            execute(control, ['/opt/bin/gate-replay', '/input/config.json',
                                     '/input/challenge.ndjson', '/input/solution.ndjson'], timeout=1200)
            stages.extend(['statement_comparison', 'transitive_axiom_audit', 'official_kernel_replay'])
            nanoda = {'use_stdin': False, 'export_file_path': '/input/solution.ndjson',
                      'permitted_axioms': sorted(STANDARD_AXIOMS), 'unpermitted_axiom_hard_error': True,
                      'num_threads': 2, 'nat_extension': True, 'string_extension': True}
            (control / 'nanoda.json').write_text(json.dumps(nanoda))
            stage = 'independent_nanoda_replay'
            execute(control, ['/opt/bin/nanoda_bin', '/input/nanoda.json'], timeout=1200)
            stages.append('independent_nanoda_replay')
            result['machine_status'] = 'passed'
    except (RegistryError, OSError, ValueError, subprocess.SubprocessError) as exc:
        result['error'] = str(exc)
        result['failed_stage'] = stage
        result['failure_status'] = (exc.status if isinstance(exc, VerificationError) else
                                    'infrastructure_error' if isinstance(exc, (OSError, subprocess.SubprocessError)) else 'failed')
    result['duration_seconds'] = round(time.monotonic() - started, 3)
    result['exports'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in evidence.glob('*.ndjson')}
    (evidence / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result
