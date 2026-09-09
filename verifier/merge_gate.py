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
from .environments import matches, relative_path
from .source_adaptation import adapt, transforms_by_path
from .registry import (ROOT, RegistryError, VerificationError, canonical_digest,
                       read_json, require, review_approval_kind, safe_file, validate_registry)

MAX_DOWNLOAD = 16 * 1024 * 1024


def write_report(path, identifier, proof):
    """Human-readable evidence; JSON remains the machine-readable record."""
    lines = ['# Lean verification report', '', '```json', json.dumps({
        'submission_id': identifier,
        'verification_status': proof['verification_status'],
        'machine_status': proof['machine_status'],
        'review_status': proof['review_status'],
        'review_approval_kind': proof.get('review_approval_kind', 'independent_review' if proof['review_status'] == 'approved' else 'unapproved'),
        'review_administrator': proof.get('review_administrator'),
        'formal_status': proof['formal_status'],
        'bindings': proof['bindings'],
        'required_theorems': proof['targets'],
        'candidate_targets': proof['candidate_targets'],
        'error': proof.get('error'),
    }, indent=2), '```', '',
        'This report does not grant formal acceptance or decide award eligibility.', '',
        'See result.json and execution-*.json for stage outcomes. The controller records',
        'aggregate target checks; per-theorem axiom inventories are not yet available.', '']
    path.write_text('\n'.join(lines))


class GitHub:
    def __init__(self, repository):
        require(bool(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository)), 'Invalid GitHub repository')
        self.repository = repository

    def get(self, path):
        return self.request(path)

    def request(self, path, data=None, method=None):
        require(not path.startswith('/') and '..' not in path.split('/') and '://' not in path,
                'Unsafe GitHub API path')
        request = urllib.request.Request('https://api.github.com/repos/' + self.repository + '/' + path,
                                         data=json.dumps(data).encode() if data is not None else None,
                                         method=method,
                                         headers={'Accept': 'application/vnd.github+json',
                                                  'User-Agent': 'math-lean-verification'})
        token = os.environ.get('GH_TOKEN')
        if token:
            request.add_header('Authorization', 'Bearer ' + token)
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read(MAX_DOWNLOAD + 1)
        require(len(data) <= MAX_DOWNLOAD, 'GitHub response exceeds size limit')
        return json.loads(data) if data else None

    def pages(self, path, key=None, max_pages=100):
        separator = '&' if '?' in path else '?'
        for page in range(1, max_pages + 1):
            value = self.get(f'{path}{separator}per_page=100&page={page}')
            values = value[key] if key else value
            require(isinstance(values, list), 'Invalid paginated response')
            yield from values
            if len(values) < 100:
                return
        raise RegistryError('GitHub pagination limit reached; results are incomplete')

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
    for folder in ['problems', 'submissions', 'proofs', 'records', 'policy', 'environments', 'candidates']:
        (root / folder).mkdir()
    total = count = 0
    for path, item in tree.items():
        if not path.startswith(('problems/', 'submissions/', 'proofs/', 'records/', 'environments/', 'candidates/')):
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
        environment_id = submission['toolchain_id']
        changed = changed or (proposed.get('environments', {}).get(environment_id) !=
                              trusted.get('environments', {}).get(environment_id))
        changed = changed or proposed['policy'] != trusted['policy']
        if changed:
            affected.append(identifier)
    return sorted(affected)


def proposal_snapshot(api, head, number, root):
    """Apply only the PR delta to current trusted data; waiting PRs need no rebase."""
    folders = ('problems', 'submissions', 'proofs', 'records', 'environments', 'policy', 'candidates', 'intake-mappings')
    for folder in folders:
        if (ROOT / folder).exists():
            shutil.copytree(ROOT / folder, root / folder)
        else:
            (root / folder).mkdir()
    files = []
    for page in range(1, 32):
        batch = api.get(f'pulls/{number}/files?per_page=100&page={page}')
        require(isinstance(batch, list), 'Invalid PR file listing')
        files.extend(batch)
        if len(batch) < 100:
            break
    require(len(files) < 3000, 'PR file listing may be truncated')
    tree = api.tree(head)
    changed = set()
    total = 0
    for item in files:
        paths = [item['filename']]
        if item.get('previous_filename'):
            paths.append(item['previous_filename'])
        for path in paths:
            if not path.startswith(tuple(f + '/' for f in folders)):
                continue
            relative_path(path)
            changed.add(path)
            # These policies are read exclusively from the protected controller.
            if path.startswith(('policy/', 'intake-mappings/')):
                continue
            destination = root / path
            if path not in tree:
                if destination.exists():
                    require(destination.is_file(), 'Unexpected removed directory')
                    destination.unlink()
                continue
            data = api.blob(tree[path])
            total += len(data)
            require(total <= 32 * 1024**2, 'PR metadata exceeds limit')
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
    return changed


def prerequisites(trusted, proposed, identifier):
    submission = proposed['submissions'][identifier]
    key = (submission['problem_id'], submission['statement_version'])
    require(key in trusted['problems'], 'Official statement must be independently reviewed and merged before candidate registration')
    problem = trusted['problems'][key]
    require(problem == proposed['problems'][key], 'Candidate PR cannot change its official statement or review')
    require(trusted['policy']['backend'] == 'comparator-export-v1', 'Lean backend is not configured')
    if submission['adapter_id'] is not None:
        raise VerificationError('Legacy adapters are unsupported; use hashed proof overlays', 'unsupported')
    identifier = submission['toolchain_id']
    if identifier not in trusted['policy']['toolchains']:
        raise VerificationError('Candidate has no approved supported toolchain', 'unsupported')
    if 'workspace' in problem:
        environment = trusted.get('environments', {}).get(identifier)
        if environment is None or environment['status'] != 'approved':
            raise VerificationError('Environment is unsupported or awaiting onboarding', 'unsupported')
        require(environment == proposed.get('environments', {}).get(identifier), 'Candidate PR cannot change its execution environment')
        require(canonical_digest(environment) == problem['workspace']['environment_digest'], 'Stale environment binding')
        require('execution' in submission, 'Explicit source mapping is required')
        # Pending mathematical review permits diagnostics, never a merge pass.
        return submission, problem, problem['workspace']['solution_module']
    require(problem['review']['status'] == 'approved', 'Independent statement review is pending')
    if identifier != PROFILE:
        raise VerificationError('Legacy registration requires the supported stdlib toolchain', 'unsupported')
    modules = {target['module'] for target in submission['targets']}
    require(len(modules) == 1, 'Legacy registration supports one target module')
    require(all(t['declaration'] == t['official_theorem'] for t in submission['targets']),
            'A reviewed bridge to official theorem names is required')
    return submission, problem, next(iter(modules))


def candidate_sources(submission, destination, *, problem=None, environment=None, registry_root=None,
                      original_sources=None, adaptations=None):
    api = GitHub(submission['repository'].removeprefix('https://github.com/'))
    tree = api.tree(submission['commit'])
    execution = submission.get('execution', {'project_root': '.', 'include': ['**'], 'proof_files': []})
    root = relative_path(execution['project_root'], root=True)
    prefix = '' if root == '.' else root + '/'
    for pattern in execution['include']:
        relative_path(pattern, pattern=True)
    selected = {}
    for path, item in tree.items():
        if not path.startswith(prefix):
            continue
        relative = path[len(prefix):]
        if not matches(relative, execution['include']):
            continue
        # Never load upstream Lake programs or precompiled artifacts.
        if not relative.endswith('.lean') or relative == 'lakefile.lean' or '.lake' in relative.split('/') or '.git' in relative.split('/'):
            continue
        relative_path(relative)
        selected[relative] = item
    limits = environment['resources'] if environment else {'max_files': 100, 'max_source_mb': 8}
    require(0 < len(selected) <= limits['max_files'], 'Unsupported source tree size')
    transforms = transforms_by_path(execution)
    require(set(transforms) <= set(selected), 'Source transform does not refer to a selected upstream file')
    protected = {f['path'] for f in problem['trusted_files']} if problem else set()
    allowed = problem['workspace']['submission_paths'] if problem and 'workspace' in problem else ['**']
    source_hashes = {}
    total = 0
    def write(path, data):
        nonlocal total
        relative_path(path)
        require(path not in protected, 'Candidate cannot overwrite a trusted workspace file')
        require(matches(path, allowed), 'Source is outside the approved submission paths')
        require(path not in source_hashes, 'Duplicate upstream and proof-overlay path')
        total += len(data)
        require(total <= limits['max_source_mb'] * 1024**2 and len(source_hashes) < limits['max_files'], 'Source package exceeds limit')
        output = destination / path
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)
        source_hashes[path] = hashlib.sha256(data).hexdigest()
    original_total = 0
    for path, item in selected.items():
        data = api.blob(item)
        original_total += len(data)
        require(original_total <= limits['max_source_mb'] * 1024**2, 'Original source package exceeds limit')
        if original_sources is not None:
            original = original_sources / path
            original.parent.mkdir(parents=True, exist_ok=True)
            original.write_bytes(data)
        target, adapted = adapt(path, data, transforms.get(path), max_bytes=limits['max_source_mb'] * 1024**2)
        write(target, adapted)
        if adaptations is not None:
            adaptations.append({'path': path, 'destination': target,
                'original_sha256': hashlib.sha256(data).hexdigest(),
                'adapted_sha256': hashlib.sha256(adapted).hexdigest()})
    for proof in execution['proof_files']:
        require(registry_root is not None, 'Missing proof overlay root')
        source = safe_file(registry_root, 'proofs/' + submission['submission_id'] + '/' + proof['path'])
        data = source.read_bytes()
        require(hashlib.sha256(data).hexdigest() == proof['sha256'], 'Stale proof overlay')
        write(proof['path'], data)
    for target in submission.get('targets', []):
        path = target['module'].replace('.', '/') + '.lean'
        path = transforms.get(path, {}).get('destination', path)
        require(path in source_hashes, 'Required target module is absent from selected candidate sources: ' + path)
    return source_hashes


def run(repository, pr_number, head, image, output, check_only=False, submission_id=None, images=None):
    api = GitHub(repository)
    pr = api.get('pulls/' + str(pr_number))
    require(pr['state'] == 'open' and pr['head']['sha'] == head, 'Stale or closed PR')
    require(pr['base']['repo']['full_name'] == repository and pr['base']['ref'] == 'main', 'Unexpected PR base')
    base = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    require(pr['base']['sha'] == base, 'Base moved; rerun verification on current main')
    trusted = validate_registry(ROOT)
    with tempfile.TemporaryDirectory(prefix='lean-pr-') as temporary:
        root = Path(temporary)
        changed = proposal_snapshot(api, head, pr_number, root)
        proposed = validate_registry(root)
        affected = select_submissions(trusted, proposed)
        old_candidates = trusted.get('candidates', {})
        new_candidates = proposed.get('candidates', {})
        require(set(old_candidates) <= set(new_candidates), 'Removing registered candidates requires a separate maintenance process')
        simple = [i for i, c in new_candidates.items() if c != old_candidates.get(i) or
                  any(p.startswith('proofs/' + i + '/') for p in changed)]
        if simple:
            require(not any(p.startswith(('problems/', 'environments/', 'policy/', 'intake-mappings/')) for p in changed),
                    'Candidate PR cannot change protected preparation inputs')
        from .intake import prepare_registry
        # Preparation is recomputed for each execution using current protected data.
        proposed = prepare_registry(proposed, ROOT, root, root, simple)
        affected = sorted(set(affected) | set(simple))
        blocked = {i: proposed['intake'][i] for i in simple if proposed['intake'][i]['intake_status'] != 'ready'}
        if submission_id:
            require(submission_id in affected, 'Requested candidate is not in the trusted execution plan')
            affected = [submission_id]
        ready = [i for i in affected if i not in blocked]
        result = execute_candidates(trusted, proposed, root, ready, base, head, image,
                                    output, check_only=check_only, images=images)
        result['intake'] = proposed['intake']
        result['blocked'] = {i: value for i, value in blocked.items() if i in affected}
        if result['blocked']:
            result['status'] = 'blocked'
        # A single fixed snapshot must cover PR files, not a mixture of updates.
        latest = api.get('pulls/' + str(pr_number))
        require(latest['state'] == 'open' and latest['head']['sha'] == head and latest['base']['sha'] == base,
                'PR or base moved during verification')
        return result


def execute_candidates(trusted, proposed, registry_root, affected, base, head, image,
                       output, *, check_only=False, images=None):
    """Shared PR and protected-base execution; never selects or approves inputs."""
    result = {'schema_version': 1, 'head_sha': head, 'verifier_sha': base,
              'status': 'not_applicable' if not affected else ('ready' if check_only else 'passed'), 'submissions': {}}
    result['matrix'] = {'include': [{'submission': s, 'environment': proposed['submissions'][s]['toolchain_id'] or ''} for s in affected]}
    for identifier in affected:
        submission = proposed['submissions'][identifier]
        key = (submission['problem_id'], submission['statement_version'])
        problem = trusted['problems'].get(key, proposed['problems'][key])
        environment = trusted.get('environments', {}).get(submission['toolchain_id']) if 'workspace' in problem else None
        bindings = {'pr_head': head, 'base_sha': base, 'upstream_commit': submission['commit'],
            'workspace_digest': canonical_digest(problem), 'environment_digest': canonical_digest(environment),
            'policy_digest': canonical_digest(trusted['policy']), 'run_id': os.environ.get('GITHUB_RUN_ID'),
            'run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT')}
        try:
            submission, problem, module = prerequisites(trusted, proposed, identifier)
            if check_only:
                result['submissions'][identifier] = {'machine_status': 'not_run', 'prerequisites': 'ready'}
                continue
            selected_image = (images or {}).get(submission['toolchain_id'], image)
            require(selected_image is not None, 'Missing immutable verifier image')
            with tempfile.TemporaryDirectory(prefix='lean-materials-') as sources:
                source_root = Path(sources)
                original_sources = source_root / 'original'
                adaptations = []
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
                source_hashes = candidate_sources(submission, solution, problem=problem if environment else None,
                    environment=environment, registry_root=registry_root, original_sources=original_sources, adaptations=adaptations)
                if environment:
                    # Shared trusted definitions are copied after the candidate overlay;
                    # collision checking above prohibits their replacement.
                    for item in problem['trusted_files']:
                        if item['path'].endswith('.lean') and item['path'] != 'Challenge.lean':
                            dst = solution / item['path']
                            dst.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copyfile(problem_dir / item['path'], dst)
                proof = verify(selected_image, challenge, solution, module,
                               problem['required_theorems'], output / identifier, environment=environment,
                               solution_declarations=[t['declaration'] for t in submission['targets']])
                proof['source_hashes'] = source_hashes
                proof['source_adaptations'] = adaptations
                if original_sources.exists():
                    shutil.copytree(original_sources, output / identifier / 'inputs/original')
                proof['verification_status'] = ('verified' if problem['review']['status'] == 'approved' else 'review_pending') if proof['machine_status'] == 'passed' else proof.get('failure_status', 'failed')
                shutil.copytree(challenge, output / identifier / 'inputs/challenge')
                shutil.copytree(solution, output / identifier / 'inputs/solution')
                (output / identifier / 'inputs/submission.json').write_text(json.dumps(submission, indent=2))
                (output / identifier / 'inputs/problem.json').write_text(json.dumps(problem, indent=2))
                proof['input_digest'] = canonical_digest({'submission': submission,
                    'problem': problem, 'environment': environment, 'sources': source_hashes, 'policy': trusted['policy'], 'verifier_sha': base,
                    'intake': proposed.get('intake', {}).get(identifier)})
                if identifier in proposed.get('intake', {}):
                    intake = proposed['intake'][identifier]
                    (output / identifier / 'inputs/intake.json').write_text(json.dumps(intake, indent=2) + '\n')
                    (output / identifier / 'inputs/candidate.json').write_text(json.dumps(proposed['candidates'][identifier], indent=2) + '\n')
                proof['candidate_commit'] = submission['commit']
                result['submissions'][identifier] = proof
                if proof['verification_status'] != 'verified':
                    result['status'] = 'failed'
        except (RegistryError, OSError, ValueError) as exc:
            result['status'] = 'failed'
            classification = (exc.status if isinstance(exc, VerificationError) else
                              'infrastructure_error' if isinstance(exc, OSError) else 'not_run')
            result['submissions'][identifier] = {'machine_status': 'not_run', 'verification_status': classification, 'error': str(exc)}
        proof = result['submissions'][identifier]
        proof.update({'bindings': bindings, 'targets': problem['required_theorems'],
                      'candidate_targets': [t['declaration'] for t in submission['targets']],
                      'review_status': problem['review']['status'], 'formal_status': 'pending'})
        proof['review_approval_kind'] = review_approval_kind(problem['review'])
        proof['review_administrator'] = (problem['review'].get('administrator')
            if proof['review_approval_kind'] == 'administrator_exception' else None)
        if not check_only:
            evidence = output / identifier
            evidence.mkdir(parents=True, exist_ok=True)
            (evidence / 'result.json').write_text(json.dumps(proof, indent=2) + '\n')
            write_report(evidence / 'report.md', identifier, proof)
            from .results import write_result
            write_result(evidence / 'verification-result.json', identifier, proof)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--pr', type=int, required=True)
    parser.add_argument('--head', required=True)
    parser.add_argument('--image')
    parser.add_argument('--images', type=Path)
    parser.add_argument('--submission')
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(args.pr > 0 and bool(re.fullmatch('[0-9a-f]{40}', args.head)), 'Invalid PR identity')
    args.output.mkdir(parents=True, exist_ok=False)
    try:
        result = run(args.repository, args.pr, args.head, args.image, args.output, args.check_only, args.submission, read_json(args.images) if args.images else None)
    except Exception as exc:
        result = {'schema_version': 1, 'head_sha': args.head, 'status': 'failed', 'error': str(exc)}
    (args.output / 'gate.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
            stream.write('status=' + result['status'] + '\n')
            matrix = result.get('matrix', {'include': []})
            if not matrix['include']:
                matrix = {'include': [{'submission': '', 'environment': ''}]}
            stream.write('matrix=' + json.dumps(matrix) + '\n')
    allowed = ('passed', 'not_applicable', 'ready') if args.check_only else ('passed', 'not_applicable')
    return 0 if result['status'] in allowed else 1


if __name__ == '__main__':
    raise SystemExit(main())
