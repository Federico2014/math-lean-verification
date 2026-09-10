"""Select environments for non-authorizing backend regression CI."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

from .environments import load_environments
from .registry import ROOT, read_json, require

STATIC_ENTRYPOINTS = {
    'verifier/__main__.py', 'verifier/catalog.py',
    'verifier/onboarding.py', 'verifier/resume.py',
}
SHARED_FILES = {'scripts/backend_smoke.py', 'requirements-ci.lock',
                '.github/workflows/backend-ci.yml'}


def shared_change(path):
    if path.endswith('.md') or path in STATIC_ENTRYPOINTS:
        return False
    return path in SHARED_FILES or path.startswith(('backend/', 'verifier/', 'schemas/', 'policy/'))


def changed_files(root, base, head):
    require(all(isinstance(sha, str) and re.fullmatch('[0-9a-f]{40}', sha)
                for sha in (base, head)), 'Expected fixed PR base and head revisions')
    # Three-dot diff selects the whole PR, not only its latest commit. Disabling
    # rename detection includes both old and new paths, including moves of shared code.
    result = subprocess.check_output(
        ['git', 'diff', '--no-ext-diff', '--no-textconv', '--no-renames',
         '--name-only', '-z', base + '...' + head, '--'], cwd=root, timeout=30)
    require(len(result) <= 8 * 1024**2, 'PR changed-path list exceeds limit')
    return [path.decode('utf-8') for path in result.split(b'\0') if path]


def matrix(root=ROOT, *, environment=None, changed_paths=None):
    environments = load_environments(root)
    require(0 < len(environments) <= 256, 'Environment test matrix must contain 1 to 256 entries')
    require(environment is None or changed_paths is None,
            'Manual selection cannot override automatic PR selection')
    if environment is not None:
        require(environment in environments, 'Unknown environment: ' + environment)
        selected = {environment}
    elif changed_paths is None:
        selected = set(environments)
    else:
        selected = set()
        select_all = any(shared_change(path) for path in changed_paths)
        for path in changed_paths:
            if not path.startswith('environments/') or path.endswith('.md'):
                continue
            parts = path.split('/')
            if len(parts) < 3:
                # A shared file directly under environments/ may affect every profile.
                select_all = True
                continue
            identifier = parts[1]
            require(bool(re.fullmatch('[a-z][a-z0-9]*(?:-[a-z0-9]+)*', identifier)),
                    'Invalid changed environment directory')
            require(identifier in environments or not (root / 'environments' / identifier).exists(),
                    'Changed environment is missing its descriptor: ' + identifier)
            if identifier in environments:
                selected.add(identifier)
        if select_all:
            selected = set(environments)
    return {'include': [{'environment': identifier} for identifier in sorted(selected)]}


def selection(root, event_name, event, environment=None):
    if event_name == 'pull_request':
        require(environment is None, 'PR environment selection must be automatic')
        pr = event['pull_request']
        paths = changed_files(root, pr['base']['sha'], pr['head']['sha'])
        return matrix(root, changed_paths=paths), 'pull_request'
    require(event_name in ('', 'workflow_dispatch'), 'Unsupported backend test event')
    if event_name == 'workflow_dispatch':
        require(environment is None, 'Workflow selection must come from its dispatch input')
        environment = (event.get('inputs') or {}).get('environment') or None
        require(environment is None or isinstance(environment, str), 'Invalid environment input')
    return matrix(root, environment=environment), 'manual' if environment is not None else 'all'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--environment', help='Test one exact environment ID; omit to test all locally')
    args = parser.parse_args()
    event_name = os.environ.get('GITHUB_EVENT_NAME', '')
    event = read_json(Path(os.environ['GITHUB_EVENT_PATH'])) if event_name else {}
    value, mode = selection(ROOT, event_name, event, args.environment)
    has_work = bool(value['include'])
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
            stream.write('matrix=' + json.dumps(value) + '\n')
            stream.write('has_work=' + str(has_work).lower() + '\n')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as stream:
            stream.write('## Backend environment selection\n\nMode: `' + mode + '`\n\n')
            for item in value['include']:
                stream.write('- `' + item['environment'] + '`\n')
            if not has_work:
                stream.write('No affected environments remain. Backend execution is skipped; no environment was verified.\n')
            stream.write('\nOnly executed jobs provide regression evidence. This selection grants no approval.\n')
    print(json.dumps({'mode': mode, 'has_work': has_work, 'matrix': value}))


if __name__ == '__main__':
    main()
