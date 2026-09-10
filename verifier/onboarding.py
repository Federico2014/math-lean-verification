"""Generate pending environment drafts without fetching or executing candidate code."""
import json
from pathlib import Path
import re

from .environments import inspect_project
from .registry import file_digest, read_json, require, safe_file, schema_validate


def write_new(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


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
