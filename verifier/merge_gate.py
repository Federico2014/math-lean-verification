"""Trusted PR controller. Run from the protected base, never from the PR checkout."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import urllib.request

from .lean_backend import PROFILE, verify
from .registry import ROOT, RegistryError, canonical_digest, read_json, require, validate_registry

MAX_DOWNLOAD = 16 * 1024 * 1024


class GitHub:
    def __init__(self, repository):
        require(bool(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository)), 'Invalid GitHub repository')
        self.repository = repository

    def get(self, path):
        request = urllib.request.Request('https://api.github.com/repos/' + self.repository + '/' + path,
                                         headers={'Accept': 'application/vnd.github+json',
                                                  'User-Agent': 'math-lean-verification'})
        token = os.environ.get('GH_TOKEN')
        if token:
            request.add_header('Authorization', 'Bearer ' + token)
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read(MAX_DOWNLOAD + 1)
        require(len(data) <= MAX_DOWNLOAD, 'GitHub response exceeds size limit')
        return json.loads(data)

    def tree(self, commit):
        require(bool(re.fullmatch('[0-9a-f]{40}', commit)), 'Expected fixed commit')
        result = self.get('git/trees/' + commit + '?recursive=1')
        require(result.get('truncated') is False, 'Truncated source tree')
        return {item['path']: item for item in result['tree'] if item['type'] != 'tree'}

    def blob(self, item):
        require(item['type'] == 'blob' and item['mode'] == '100644', 'Only regular non-executable source files are supported')
        require(0 <= item['size'] <= 8 * 1024 * 1024, 'Source file exceeds limit')
        require(bool(re.fullmatch('[0-9a-f]{40}', item['sha'])), 'Invalid blob identity')
        result = self.get('git/blobs/' + item['sha'])
        require(result['encoding'] == 'base64', 'Unsupported blob encoding')
        data = base64.b64decode(result['content'])
        require(len(data) == item['size'], 'Blob size mismatch')
        digest = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        require(digest == item['sha'], 'Blob identity mismatch')
        return data


def write_snapshot(api, tree, root):
    for folder in ['problems', 'submissions', 'records', 'policy']:
        (root / folder).mkdir()
    total = count = 0
    for path, item in tree.items():
        if not path.startswith(('problems/', 'submissions/', 'records/')):
            continue
        require(all(re.fullmatch('[A-Za-z0-9_][A-Za-z0-9_.-]*', p) and p not in ('.', '..')
                    for p in path.split('/')), 'Unsafe registry path')
        count += 1
        total += item.get('size', 0)
        require(count <= 5000 and total <= 32 * 1024 * 1024, 'Registry snapshot exceeds limit')
        destination = root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(api.blob(item))
    # The PR cannot supply its own acceptance policy or schema.
    shutil.copyfile(ROOT / 'policy/verification.json', root / 'policy/verification.json')


def select_submissions(trusted, proposed):
    old = trusted['submissions']
    new = proposed['submissions']
    require(set(old) <= set(new), 'Removing registered candidates requires a separate maintenance process')
    affected = []
    for identifier, submission in new.items():
        key = (submission['problem_id'], submission['statement_version'])
        changed = submission != old.get(identifier) or proposed['problems'][key] != trusted['problems'].get(key)
        if changed:
            affected.append(identifier)
    return sorted(affected)


def prerequisites(trusted, proposed, identifier):
    submission = proposed['submissions'][identifier]
    key = (submission['problem_id'], submission['statement_version'])
    require(key in trusted['problems'], 'Official statement must be independently reviewed and merged before candidate registration')
    problem = trusted['problems'][key]
    require(problem == proposed['problems'][key], 'Candidate PR cannot change its official statement or review')
    require(problem['review']['status'] == 'approved', 'Independent statement review is pending')
    require(submission['toolchain_id'] == PROFILE and PROFILE in trusted['policy']['toolchains'],
            'Candidate has no approved supported toolchain')
    require(trusted['policy']['backend'] == 'comparator-export-v1', 'Lean backend is not configured')
    require(submission['adapter_id'] is None, 'Adapter must be integrated and reviewed before use')
    modules = {target['module'] for target in submission['targets']}
    require(len(modules) == 1, 'This backend profile supports one target module')
    require(all(t['declaration'] == t['official_theorem'] for t in submission['targets']),
            'A reviewed bridge to official theorem names is required')
    return submission, problem, next(iter(modules))


def candidate_sources(submission, destination):
    api = GitHub(submission['repository'].removeprefix('https://github.com/'))
    tree = api.tree(submission['commit'])
    selected = {p: item for p, item in tree.items() if p.endswith('.lean') and not p.startswith('.lake/')}
    require(0 < len(selected) <= 100, 'Unsupported source tree size')
    total = 0
    for path, item in selected.items():
        require(all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', x)
                    for x in Path(path).with_suffix('').parts), 'Unsupported source path')
        # Upstream Lake scripts are not part of the accepted source-only profile.
        if path == 'lakefile.lean':
            continue
        data = api.blob(item)
        total += len(data)
        require(total <= 8 * 1024 * 1024, 'Source package exceeds limit')
        output = destination / path
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)


def run(repository, pr_number, head, image, output, check_only=False):
    api = GitHub(repository)
    pr = api.get('pulls/' + str(pr_number))
    require(pr['state'] == 'open' and pr['head']['sha'] == head, 'Stale or closed PR')
    require(pr['base']['repo']['full_name'] == repository and pr['base']['ref'] == 'main', 'Unexpected PR base')
    base = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    require(pr['base']['sha'] == base, 'Base moved; rerun verification on current main')
    trusted = validate_registry(ROOT)
    with tempfile.TemporaryDirectory(prefix='lean-pr-') as temporary:
        root = Path(temporary)
        write_snapshot(api, api.tree(head), root)
        proposed = validate_registry(root)
        affected = select_submissions(trusted, proposed)
        result = {'schema_version': 1, 'head_sha': head, 'verifier_sha': base,
                  'status': 'not_applicable' if not affected else ('ready' if check_only else 'passed'), 'submissions': {}}
        for identifier in affected:
            try:
                submission, problem, module = prerequisites(trusted, proposed, identifier)
                if check_only:
                    result['submissions'][identifier] = {'machine_status': 'not_run', 'prerequisites': 'ready'}
                    continue
                require(image is not None, 'Missing immutable verifier image')
                with tempfile.TemporaryDirectory(prefix='lean-materials-') as sources:
                    source_root = Path(sources)
                    challenge = source_root / 'challenge'
                    challenge.mkdir()
                    problem_dir = ROOT / 'problems' / problem['problem_id'] / problem['statement_version']
                    for item in problem['trusted_files']:
                        if item['path'].endswith('.lean'):
                            dst = challenge / item['path']
                            dst.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copyfile(problem_dir / item['path'], dst)
                    solution = source_root / 'solution'
                    solution.mkdir()
                    candidate_sources(submission, solution)
                    proof = verify(image, challenge, solution, module,
                                   problem['required_theorems'], output / identifier)
                    proof['input_digest'] = canonical_digest({'submission': submission,
                        'problem': problem, 'policy': trusted['policy'], 'verifier_sha': base})
                    proof['candidate_commit'] = submission['commit']
                    (output / identifier / 'result.json').write_text(json.dumps(proof, indent=2) + '\n')
                    result['submissions'][identifier] = proof
                    if proof['machine_status'] != 'passed':
                        result['status'] = 'failed'
            except (RegistryError, OSError, ValueError) as exc:
                result['status'] = 'failed'
                result['submissions'][identifier] = {'machine_status': 'not_run', 'error': str(exc)}
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--pr', type=int, required=True)
    parser.add_argument('--head', required=True)
    parser.add_argument('--image')
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(args.pr > 0 and bool(re.fullmatch('[0-9a-f]{40}', args.head)), 'Invalid PR identity')
    args.output.mkdir(parents=True, exist_ok=False)
    try:
        result = run(args.repository, args.pr, args.head, args.image, args.output, args.check_only)
    except Exception as exc:
        result = {'schema_version': 1, 'head_sha': args.head, 'status': 'failed', 'error': str(exc)}
    (args.output / 'gate.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
            stream.write('status=' + result['status'] + '\n')
    allowed = ('passed', 'not_applicable', 'ready') if args.check_only else ('passed', 'not_applicable')
    return 0 if result['status'] in allowed else 1


if __name__ == '__main__':
    raise SystemExit(main())
