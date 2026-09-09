"""Generate reviewable intake drafts without fetching or executing candidate code."""
import copy
import json
import os
from pathlib import Path
import re

from .environments import discover, inspect_project
from .registry import ROOT, file_digest, read_json, require, safe_file, schema_validate
from .source_adaptation import lean_path


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def submission_draft(project, root, *, repository, commit, identifier, problem_id,
                     statement_version, targets):
    template = copy.deepcopy(read_json(ROOT / 'templates/submission.json'))
    template.update({'submission_id': identifier, 'problem_id': problem_id,
        'statement_version': statement_version, 'repository': repository, 'commit': commit,
        'targets': [{'module': module, 'declaration': declaration, 'official_theorem': official}
                    for module, declaration, official in targets]})
    # Validate supplied identities before using them in paths. Placeholders remain
    # explicitly draft metadata and can never attest authorization or authorship.
    schema_validate('submission', template)
    inspection = discover(project, root)
    blockers = list(inspection['warnings'])
    approved = [match for match in inspection['matches'] if match['status'] == 'approved']
    if len(approved) == 1:
        template['toolchain_id'] = approved[0]['environment_id']
    else:
        blockers.append('environment_selection_required')
    modules = []
    # Include all local Lean inputs as an explicit proposal, not just the target
    # files. Imports are not parsed as an authoritative dependency closure.
    project = Path(project)
    count = 0
    for folder, directories, files in os.walk(project, followlinks=False):
        directories[:] = [d for d in directories if not d.startswith('.')]
        for directory in directories:
            require(not (Path(folder) / directory).is_symlink(), 'Symlink in project sources')
        count += len(directories) + len(files)
        require(count <= 10000, 'Project discovery exceeds file limit')
        for name in files:
            if not name.endswith('.lean') or name == 'lakefile.lean' or name.startswith('.'):
                continue
            relative = (Path(folder) / name).relative_to(project).as_posix()
            lean_path(relative)
            safe_file(project, relative)
            modules.append(relative)
    require(bool(modules), 'No Lean source files found')
    for module, _, _ in targets:
        require(module.replace('.', '/') + '.lean' in modules, 'Target module source is missing')
    patterns = sorted({path if '/' not in path else path.split('/')[0] + '/**' for path in modules})
    template['execution'] = {'project_root': '.', 'include': patterns, 'proof_files': []}
    schema_validate('submission', template)
    statement_path = root / 'problems' / problem_id / statement_version / 'problem.json'
    if not statement_path.exists():
        blockers.append('official_workspace_required')
    else:
        from .registry import validate_registry
        registry = validate_registry(root)
        problem = registry['problems'][(problem_id, statement_version)]
        require({t[2] for t in targets} == set(problem['required_theorems']) and
                len(targets) == len(problem['required_theorems']), 'Draft must map every official target exactly once')
        if problem['toolchain_id'] != template['toolchain_id']:
            blockers.append('workspace_environment_mismatch')
        if problem['review']['status'] != 'approved':
            blockers.append('statement_review_pending')
        if set(modules) & {f['path'] for f in problem['trusted_files']}:
            blockers.append('source_adaptation_required')
    # This is intentionally not a valid registration until the submitter completes
    # provenance and permission fields. Do not fabricate author or license claims.
    template['contribution']['public_source_authorized'] = False
    blockers += ['complete_attribution_and_publication_permission', 'review_source_scope_and_bridge']
    return {'schema_version': 1, 'kind': 'submission_draft', 'machine_status': 'not_run',
            'blockers': blockers, 'inspection': inspection, 'submission': template}


def environment_draft(project, output, *, identifier, archive_sha256, exporter_commit, cache_modules):
    require(bool(re.fullmatch(r'[a-z][a-z0-9]*(?:-[a-z0-9]+)*', identifier)), 'Invalid environment ID')
    inspection = inspect_project(project)
    require(inspection['lean_toolchain'] is not None, 'A fixed Lean toolchain is required')
    require(not inspection['warnings'], 'Resolve static environment inspection warnings before drafting')
    dependencies = inspection['dependencies']
    require(not dependencies or any(d['name'] == 'mathlib' for d in dependencies),
            'Non-Mathlib dependencies require a dedicated environment backend')
    env = {'schema_version': 1, 'environment_id': identifier,
        'description': 'Pending environment; review dependencies, cache scope and compatibility evidence.',
        'status': 'pending', 'evidence_url': None,
        'lean_release': inspection['lean_toolchain'].split(':')[1],
        'lean_archive_sha256': archive_sha256, 'exporter_commit': exporter_commit,
        'dependency_mode': 'mathlib-cache' if dependencies else 'none',
        'files': [], 'cache_modules': list(dict.fromkeys(cache_modules)),
        'resources': {'memory_mb': 6144, 'cpus': 2, 'work_mb': 2048, 'timeout_seconds': 3600,
                      'max_files': 2000, 'max_source_mb': 32, 'max_export_mb': 512}}
    if dependencies:
        require(bool(cache_modules), 'Specify the Mathlib module scope explicitly')
        if 'Mathlib.Data.Nat.Basic' not in env['cache_modules']:
            env['cache_modules'].append('Mathlib.Data.Nat.Basic')
    else:
        require(not cache_modules, 'Core/Std environments cannot request a Mathlib cache')
    schema_validate('environment', env)
    # Generate a minimal static workspace; never copy executable Lake programs or
    # project-defined build hooks into the privileged image preparation stage.
    files = {'lean-toolchain': inspection['lean_toolchain'] + '\n',
             'lakefile.toml': 'name = "verification"\nversion = "0.1.0"\n'}
    if dependencies:
        lock = read_json(safe_file(Path(project), 'lake-manifest.json'))
        require(lock.get('version') in ('1.1.0', '1.2.0'), 'Unsupported Lake lock format')
        packages = []
        for dep in lock['packages']:
            require(dep.get('configFile', 'lakefile.lean') in ('lakefile.lean', 'lakefile.toml'),
                    'Unsupported dependency configuration path')
            packages.append({'name': dep['name'], 'url': dep['url'], 'type': 'git',
                'rev': dep['rev'], 'inputRev': dep['rev'], 'subDir': None,
                'scope': dep['url'].split('/')[-2], 'inherited': False,
                'manifestFile': 'lake-manifest.json', 'configFile': dep.get('configFile', 'lakefile.lean')})
        lock = {'version': lock['version'], 'name': 'verification', 'packagesDir': '.lake/packages',
                'lakeDir': '.lake', 'packages': packages, 'fixedToolchain': False}
        files['lake-manifest.json'] = json.dumps(lock, indent=2) + '\n'
        for dep in dependencies:
            files['lakefile.toml'] += '\n[[require]]\n' + '\n'.join(
                key + ' = ' + json.dumps(dep[source])
                for key, source in [('name', 'name'), ('git', 'url'), ('rev', 'rev')]) + '\n'
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    for name, content in files.items():
        (output / name).write_text(content)
        env['files'].append({'path': name, 'sha256': file_digest(output / name)})
    write_new(output / 'environment.json', env)
    return env
