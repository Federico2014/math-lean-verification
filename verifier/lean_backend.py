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

from .registry import RegistryError, require

PROFILE = 'lean-4-34-rc2-stdlib'
AXIOMS = ['propext', 'Classical.choice', 'Quot.sound']
NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_']*(?:\.[A-Za-z_][A-Za-z0-9_']*)*\Z")
MAX_EXPORT = 128 * 1024 * 1024
MAX_LOG = 2 * 1024 * 1024


def sandbox(image: str, inputs: Path, command: list[str], *, timeout=600,
            max_stdout=MAX_LOG) -> tuple[int, bytes, bytes]:
    require(bool(re.fullmatch(r'sha256:[0-9a-f]{64}', image)), 'Expected immutable local image ID')
    require(inputs.is_dir() and not inputs.is_symlink(), 'Invalid sandbox input directory')
    name = 'lean-gate-' + uuid.uuid4().hex
    args = ['docker', 'run', '--name', name, '--rm', '--network=none', '--read-only',
            '--user=10001:10001', '--cap-drop=ALL', '--security-opt=no-new-privileges',
            '--security-opt=seccomp=' + str(Path(__file__).resolve().parents[1] / 'backend/seccomp.json'),
            '--pids-limit=128', '--memory=4g', '--memory-swap=4g', '--cpus=2',
            '--ulimit=nofile=256:256', '--ulimit=fsize=268435456:268435456',
            '--tmpfs=/work:rw,nosuid,nodev,size=1073741824,mode=1777',
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
            require(time.monotonic() < deadline, 'Sandbox execution timed out')
            for key, _ in selector.select(timeout=0.25):
                data = os.read(key.fileobj.fileno(), 65536)
                if not data:
                    selector.unregister(key.fileobj)
                    continue
                chunks[key.fileobj].extend(data)
                limit = max_stdout if key.fileobj is proc.stdout else MAX_LOG
                require(len(chunks[key.fileobj]) <= limit, 'Sandbox output exceeds limit')
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


def checked(image, inputs, command, **kwargs):
    code, out, err = sandbox(image, inputs, command, **kwargs)
    if code:
        # JSON escaping prevents Actions command injection through untrusted logs.
        detail = json.dumps((err + out)[-8000:].decode('utf-8', errors='replace'))
        raise RegistryError(f'Isolated stage rejected input (exit {code}): {detail}')
    return out


def copy_sources(source: Path, destination: Path) -> None:
    """Only Lean source is accepted; never copy upstream builds or Lake programs."""
    require(source.is_dir() and not source.is_symlink(), 'Missing source directory')
    destination.mkdir()
    count = total = 0
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
        require(count <= 100 and total <= 8 * 1024 * 1024, 'Lean source package exceeds limit')
        out = destination / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(item, out)


def verify(image: str, challenge_sources: Path, solution_sources: Path,
           module: str, theorems: list[str], evidence: Path) -> dict:
    require(bool(NAME.fullmatch(module)), 'Invalid solution module')
    require(0 < len(theorems) <= 100 and len(theorems) == len(set(theorems)), 'Invalid targets')
    require(all(NAME.fullmatch(n) for n in theorems), 'Invalid theorem name')
    require(not evidence.exists(), 'Evidence directory already exists')
    evidence.mkdir(parents=True)
    cfg = {'challenge_module': 'Challenge', 'solution_module': module,
           'theorem_names': theorems, 'definition_names': [], 'permitted_axioms': AXIOMS}
    stages = []
    result = {'schema_version': 1, 'profile': PROFILE, 'image_id': image,
              'targets': theorems, 'machine_status': 'failed', 'stages': stages,
              'seccomp_sha256': hashlib.sha256((Path(__file__).resolve().parents[1] / 'backend/seccomp.json').read_bytes()).hexdigest()}
    try:
        with tempfile.TemporaryDirectory(prefix='lean-gate-') as temporary:
            root = Path(temporary)
            control = root / 'control'
            control.mkdir()
            (control / 'config.json').write_text(json.dumps(cfg))
            checked(image, control, ['python3', '/opt/gate/probe.py'])
            stages.append('sandbox_probes')
            for filename in ['toolchain.json', 'binaries.sha256', 'system-packages.txt']:
                (evidence / filename).write_bytes(checked(image, control, ['cat', '/opt/gate/' + filename]))
            targets = checked(image, control, ['/opt/bin/gate-replay', '/input/config.json', 'targets'])
            target_names = json.loads(targets)
            require(isinstance(target_names, list) and all(isinstance(x, str) and NAME.fullmatch(x)
                    for x in target_names), 'Invalid trusted export target list')
            for kind, source, mod in [('challenge', challenge_sources, 'Challenge'),
                                      ('solution', solution_sources, module)]:
                package = root / kind
                package.mkdir()
                copy_sources(source, package / 'source')
                (package / 'targets.json').write_bytes(targets)
                # Probe each actual input mount before executing any Lean source.
                checked(image, package, ['python3', '/opt/gate/probe.py'])
                export = checked(image, package, ['python3', '/opt/gate/export.py', mod],
                                 timeout=1800, max_stdout=MAX_EXPORT)
                require(bool(export), 'Empty proof export')
                (control / (kind + '.ndjson')).write_bytes(export)
                (evidence / (kind + '.ndjson')).write_bytes(export)
                stages.append(kind + '_clean_build_export')
            checked(image, control, ['/opt/bin/gate-replay', '/input/config.json',
                                     '/input/challenge.ndjson', '/input/solution.ndjson'], timeout=1200)
            stages.extend(['statement_comparison', 'transitive_axiom_audit', 'official_kernel_replay'])
            nanoda = {'use_stdin': False, 'export_file_path': '/input/solution.ndjson',
                      'permitted_axioms': AXIOMS, 'unpermitted_axiom_hard_error': True,
                      'num_threads': 2, 'nat_extension': True, 'string_extension': True}
            (control / 'nanoda.json').write_text(json.dumps(nanoda))
            checked(image, control, ['/opt/bin/nanoda_bin', '/input/nanoda.json'], timeout=1200)
            stages.append('independent_nanoda_replay')
            result['machine_status'] = 'passed'
    except (RegistryError, OSError, ValueError, subprocess.SubprocessError) as exc:
        result['error'] = str(exc)
    result['exports'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in evidence.glob('*.ndjson')}
    (evidence / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return result
