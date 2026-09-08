"""Reusable, hash-bound environments and static (non-executing) discovery."""
from __future__ import annotations

import fnmatch
from functools import lru_cache
import json
from pathlib import Path
import re
import tomllib

from .registry import (RegistryError, canonical_digest, file_digest, read_json,
                       require, safe_file, schema_validate)


def relative_path(value, *, pattern=False, root=False):
    if root and value == '.':
        return value
    require(isinstance(value, str) and len(value) <= 256, 'Invalid source path')
    require(all(p not in ('', '.', '..', '.git', '.lake') for p in value.split('/')),
            'Unsafe source path component')
    regex = r'[A-Za-z0-9_][A-Za-z0-9_.*-]*' if pattern else r'[A-Za-z0-9_][A-Za-z0-9_.-]*'
    require(all(re.fullmatch(regex, p) or (pattern and p in ('*', '**'))
                for p in value.split('/')), 'Unsupported source path')
    return value


def matches(path, patterns):
    # ** is a recursive prefix; other patterns match individual path segments.
    @lru_cache(maxsize=None)
    def match(parts, glob):
        if not glob:
            return not parts
        if glob[0] == '**':
            return match(parts, glob[1:]) or bool(parts) and match(parts[1:], glob)
        return bool(parts) and fnmatch.fnmatchcase(parts[0], glob[0]) and match(parts[1:], glob[1:])
    return any(match(tuple(path.split('/')), tuple(p.split('/'))) for p in patterns)


def load_environments(root):
    base = root / 'environments'
    if not base.exists():
        return {}
    require(not base.is_symlink(), 'Symlink in environments')
    result = {}
    for path in sorted(base.glob('*/environment.json')):
        path = safe_file(root, path.relative_to(root).as_posix())
        env = read_json(path)
        schema_validate('environment', env)
        require(path.parent.name == env['environment_id'], 'Environment ID differs from directory')
        declared = {f['path']: f['sha256'] for f in env['files']}
        require(len(declared) == len(env['files']), 'Duplicate environment file')
        actual = set()
        for file in path.parent.rglob('*'):
            require(not file.is_symlink(), 'Symlink in environment')
            if file.is_file() and file != path:
                actual.add(file.relative_to(path.parent).as_posix())
        require(actual == set(declared), 'Unbound environment file')
        for name, digest in declared.items():
            require(file_digest(safe_file(path.parent, name)) == digest, 'Environment file hash mismatch')
        if env['status'] == 'approved':
            require(env['evidence_url'] is not None, 'Approved environment requires onboarding evidence')
        if env['dependency_mode'] == 'mathlib-cache':
            require({'lakefile.toml', 'lake-manifest.json'} <= set(declared), 'Missing dependency workspace')
            inspection = inspect_project(path.parent)
            require(inspection['lean_toolchain'] == 'leanprover/lean4:' + env['lean_release'], 'Environment toolchain mismatch')
            require(any(d['name'] == 'mathlib' for d in inspection['dependencies']), 'Missing locked Mathlib dependency')
        result[env['environment_id']] = env
    return result


def inspect_project(project):
    """Inspect only bounded text data. Never evaluate lakefile.lean or fetch dependencies."""
    project = Path(project)
    result = {'schema_version': 1, 'machine_status': 'not_run', 'lean_toolchain': None,
              'dependencies': [], 'warnings': [], 'matches': []}
    if (project / 'lean-toolchain').exists():
        toolchain = safe_file(project, 'lean-toolchain').read_text().strip()
        require(re.fullmatch(r'leanprover/lean4:v4\.\d+\.\d+(?:-rc\d+)?', toolchain),
                'Unsupported or mutable Lean toolchain')
        result['lean_toolchain'] = toolchain
    else:
        result['warnings'].append('missing_lean_toolchain')
    if (project / 'lakefile.toml').exists():
        try:
            config = tomllib.loads(safe_file(project, 'lakefile.toml').read_text())
        except (ValueError, UnicodeError) as exc:
            raise RegistryError('Invalid static Lake configuration') from exc
        result['project_name'] = config.get('name')
    elif (project / 'lakefile.lean').exists():
        safe_file(project, 'lakefile.lean')
        result['warnings'].append('dynamic_lakefile_requires_review')
    else:
        result['warnings'].append('missing_lake_configuration')
    if (project / 'lake-manifest.json').exists():
        manifest_path = safe_file(project, 'lake-manifest.json')
        manifest = read_json(manifest_path)
        require(isinstance(manifest, dict) and isinstance(manifest.get('packages'), list), 'Invalid dependency lock')
        require(len(manifest['packages']) <= 100, 'Too many dependencies')
        names = set()
        for dep in manifest['packages']:
            require(isinstance(dep, dict), 'Invalid dependency entry')
            require(dep.get('type') == 'git' and re.fullmatch(r'[0-9a-f]{40}', dep.get('rev', '')),
                    'Dependency must use a fixed Git commit')
            require(re.fullmatch(r'https://github\.com/[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+', dep.get('url', '')),
                    'Dependency repository must be public GitHub HTTPS')
            name = dep.get('name', '')
            require(re.fullmatch('[A-Za-z][A-Za-z0-9_-]*', name) and name not in names, 'Invalid dependency name')
            require(dep.get('subDir') in (None, ''), 'Dependency subdirectories require a dedicated backend')
            names.add(name)
            result['dependencies'].append({k: dep[k] for k in ('name', 'url', 'rev')})
        result['manifest_sha256'] = file_digest(manifest_path)
    else:
        result['warnings'].append('missing_dependency_lock')
    result['dependencies'].sort(key=lambda x: x['name'])
    return result


def discover(project, root):
    result = inspect_project(project)
    for identifier, env in load_environments(root).items():
        if result['lean_toolchain'] != 'leanprover/lean4:' + env['lean_release']:
            continue
        expected = next((f['sha256'] for f in env['files'] if f['path'] == 'lake-manifest.json'), None)
        # Matching is deliberately conservative. Cache/module coverage and tool
        # compatibility still require review even when dependency locks match.
        if expected == result.get('manifest_sha256') and not result['warnings']:
            result['matches'].append({'environment_id': identifier, 'status': env['status'],
                                      'environment_digest': canonical_digest(env)})
    result['next_step'] = 'review_environment_match' if result['matches'] else 'review_new_environment_configuration'
    return result
