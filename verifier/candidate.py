"""One operator entrypoint for the four-stage candidate workflow.

GitHub writes use the operator's gh login, never candidate containers or CI write
credentials. Candidate files are bounded data; no Git hooks, Lake or Lean run here.
"""
import hashlib
import json
import re
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from .merge_gate import GitHub
from .registry import ID, RegistryError, read_json, require, safe_file, schema_validate
from .registration import problem_identity, render, update
from .workflow import from_plan

MAX_BYTES = 128 * 1024**2


class Session(GitHub):
    """Use gh's authenticated transport without exposing or copying its token."""
    def call(self, args, *, output=None, timeout_seconds=180):
        with tempfile.TemporaryFile() as errors:
            process = subprocess.Popen(['gh', 'api', *args], stdout=subprocess.PIPE, stderr=errors)
            timeout = threading.Timer(timeout_seconds, process.kill)
            timeout.start()
            data = bytearray()
            size = 0
            try:
                while block := process.stdout.read(65536):
                    size += len(block)
                    require(size <= MAX_BYTES, 'GitHub response exceeds publication limit')
                    if output:
                        output.write(block)
                    else:
                        data.extend(block)
                if process.wait(timeout=60) != 0:
                    errors.seek(0)
                    match = re.search(rb'HTTP [0-9]{3}', errors.read(8192))
                    detail = ' (' + match.group().decode() + ')' if match else ''
                    raise RegistryError('GitHub API request failed' + detail + '; check endpoint access and gh authentication')
            finally:
                timeout.cancel()
                process.stdout.close()
                if process.poll() is None:
                    process.kill()
                    process.wait()
            return bytes(data)

    def request(self, path, data=None, method=None):
        require(not path.startswith('/') and '..' not in path.split('/') and '://' not in path,
                'Unsafe GitHub API path')
        args = ['repos/' + self.repository + ('/' + path if path else '')]
        if method:
            args += ['--method', method]
        if data is None:
            raw = self.call(args)
        else:
            with tempfile.TemporaryDirectory(prefix='candidate-request-') as temporary:
                payload = Path(temporary) / 'payload.json'
                payload.write_text(json.dumps(data), encoding='utf-8')
                raw = self.call(args + ['--input', str(payload)])
        return json.loads(raw) if raw else None

    def viewer(self):
        return json.loads(self.call(['user']))

    def download(self, path, output):
        require(re.fullmatch(r'(actions/artifacts/[1-9][0-9]*/zip|releases/assets/[1-9][0-9]*)', path),
                'Unexpected binary endpoint')
        with output.open('xb') as stream:
            args = ['repos/' + self.repository + '/' + path]
            # Artifact ZIP endpoints require the normal JSON API Accept header
            # before redirecting; release assets require explicit binary media.
            if path.startswith('releases/assets/'):
                args += ['-H', 'Accept: application/octet-stream']
            self.call(args, output=stream, timeout_seconds=600)

    def upload(self, release_id, path):
        require(isinstance(release_id, int) and release_id > 0, 'Invalid release ID')
        require(re.fullmatch(r'[A-Za-z0-9_.-]+', path.name), 'Invalid asset name')
        require(path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_BYTES,
                'Invalid publication asset')
        endpoint = f'https://uploads.github.com/repos/{self.repository}/releases/{release_id}/assets?name={path.name}'
        return json.loads(self.call([endpoint, '--method', 'POST', '-H',
                                    'Content-Type: application/octet-stream', '--input', str(path)], timeout_seconds=600))


def target(api):
    branch = api.get('')['default_branch']
    require(branch in ('main', 'develop'), 'Unsupported default branch')
    info = api.get('branches/' + branch)
    require(info.get('protected') is True, 'Default branch must be protected')
    base = info['commit']['sha']
    require(bool(re.fullmatch('[0-9a-f]{40}', base)), 'Invalid protected revision')
    return branch, base


def current(api, branch, base):
    require(target(api) == (branch, base), 'Protected default branch moved; rerun the command')


def decode(data):
    # Reuse bounded, duplicate-key-rejecting registry JSON parsing.
    with tempfile.TemporaryDirectory(prefix='candidate-json-') as temporary:
        p = Path(temporary) / 'data.json'
        p.write_bytes(data)
        return read_json(p)


def snapshot(api, branch, base):
    tree = api.tree(base)
    registry = {'candidates': {}, 'submissions': {}, 'problems': {}, 'intake_mappings': {}}
    for path, item in tree.items():
        if re.fullmatch(r'candidates/[^/]+\.json', path):
            identifier = Path(path).stem
            require(bool(ID.fullmatch(identifier)), 'Invalid candidate ID')
            value = decode(api.blob(item))
            schema_validate('candidate', value)
            registry['candidates'][identifier] = value
        elif re.fullmatch(r'problems/[^/]+/[^/]+/problem\.json', path):
            value = decode(api.blob(item))
            schema_validate('problem', value)
            registry['problems'][value['problem_id'], value['statement_version']] = value
        elif re.fullmatch(r'intake-mappings/[^/]+\.json', path):
            value = decode(api.blob(item))
            schema_validate('intake-mapping', value)
            registry['intake_mappings'][Path(path).stem] = value
        elif re.fullmatch(r'submissions/[^/]+/[^/]+\.json', path):
            value = decode(api.blob(item))
            schema_validate('submission', value)
            identifier = value['submission_id']
            require(identifier not in registry['submissions'], 'Duplicate submission ID')
            registry['submissions'][identifier] = value
    require(not (registry['candidates'].keys() & registry['submissions'].keys()), 'Duplicate registration ID')
    publications = decode(api.blob(tree['docs/acceptance-publications.json']))
    schema_validate('acceptance-publications', publications)
    readme = api.blob(tree['README.md']).decode('utf-8')
    current(api, branch, base)
    return registry, publications, readme


def open_change(api, branch, base, files, *, title, body, prefix):
    """Create an isolated commit and normal PR, never update a protected ref."""
    current(api, branch, base)
    identity = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()[:16]
    ref = prefix + '-' + base[:12] + '-' + identity
    require(bool(re.fullmatch(r'[a-z0-9/-]+', ref)), 'Invalid change branch')
    for pr in api.pages('pulls?state=open&base=' + branch):
        if pr['head']['ref'] == ref and (pr['head'].get('repo') or {}).get('full_name') == api.repository:
            paths = {f['filename'] for f in api.pages(f"pulls/{pr['number']}/files")}
            tree = api.tree(pr['head']['sha'])
            require(paths == set(files) and all(api.blob(tree[p]) == data.encode('utf-8')
                    for p, data in files.items()), 'Existing workflow PR materials changed; review it explicitly')
            return {'pr': pr['number'], 'url': pr['html_url'], 'head_sha': pr['head']['sha'], 'status': 'already_open'}
    parent = api.get('git/commits/' + base)
    entries = []
    for path, content in sorted(files.items()):
        require(path == 'README.md' or path == 'docs/acceptance-publications.json' or
                re.fullmatch(r'candidates/[a-z0-9-]+\.json', path) or
                re.fullmatch(r'proofs/[a-z0-9-]+/[A-Za-z0-9_/]+\.lean', path), 'Unexpected change path')
        entries.append({'path': path, 'mode': '100644', 'type': 'blob', 'content': content})
    tree = api.request('git/trees', {'base_tree': parent['tree']['sha'], 'tree': entries})
    commit = api.request('git/commits', {'message': title, 'tree': tree['sha'], 'parents': [base]})
    api.request('git/refs', {'ref': 'refs/heads/' + ref, 'sha': commit['sha']})
    current(api, branch, base)
    pr = api.request('pulls', {'title': title, 'body': body, 'head': ref, 'base': branch})
    return {'pr': pr['number'], 'url': pr['html_url'], 'head_sha': commit['sha'], 'status': 'opened'}


def submit(api, identifier, file, bridge=None, *, dry_run=False):
    require(bool(ID.fullmatch(identifier)) and len(identifier) <= 80, 'Invalid candidate ID')
    value = read_json(safe_file(file.parent, file.name))
    schema_validate('candidate', value)
    require(value['public_source_authorized'] is True, 'Public source submission permission is required')
    from .environments import relative_path
    relative_path(value['source'].get('project_root', '.'), root=True)
    for pattern in value['source'].get('include', []):
        relative_path(pattern, pattern=True)
    files = {'candidates/' + identifier + '.json': json.dumps(value, indent=2) + '\n'}
    require(bool(value.get('bridge')) == (bridge is not None), 'Supply exactly the bridge declared by the candidate')
    if bridge:
        relative_path(value['bridge'])
        files['proofs/' + identifier + '/' + value['bridge']] = safe_file(bridge.parent, bridge.name).read_text(encoding='utf-8')
    branch, base = target(api)
    existing = api.tree(base)
    require('candidates/' + identifier + '.json' not in existing and not any(
        p.startswith('submissions/') and p.endswith('/' + identifier + '.json') for p in existing),
        'Candidate ID is already registered; use an explicit reviewed update PR')
    if dry_run:
        return {'step': 1, 'branch': branch, 'base': base, 'files': sorted(files), 'status': 'preview'}
    return open_change(api, branch, base, files, prefix='candidate/' + identifier,
                       title='feat: submit ' + identifier,
                       body='Submit the fixed candidate materials. Trusted CI prepares prerequisites and verifies the proof.\n\n'
                            'Follow the four-stage workflow in README. Registration, administrator acceptance and awards remain separate outcomes.')


def prepare(root, identifier):
    require(bool(ID.fullmatch(identifier)) and len(identifier) <= 80, 'Invalid candidate ID')
    from .intake import prepare_registry
    from .registry import validate_registry
    from .revalidate import plan
    registry = validate_registry(root)
    with tempfile.TemporaryDirectory(prefix='candidate-prepare-') as temporary:
        prepared = prepare_registry(registry, root, root, Path(temporary), [identifier])
        value = plan(prepared, identifier)
    return {'workflow': from_plan(value), 'plan': value}


def verify(api, number):
    require(number > 0, 'Invalid PR number')
    pr = api.get('pulls/' + str(number))
    branch = pr['base']['ref']
    require(pr['state'] == 'open' and not pr['draft'] and branch in ('main', 'develop')
            and pr['base']['repo']['full_name'] == api.repository, 'Expected an open candidate PR on a supported target')
    info = api.get('branches/' + branch)
    require(info.get('protected') is True, 'PR target must be protected')
    api.request('actions/workflows/lean-verification.yml/dispatches', {
        'ref': branch, 'inputs': {'pr': str(number), 'expected_head': pr['head']['sha'],
                                'expected_base': info['commit']['sha']}})
    return {'step': 3, 'status': 'dispatched', 'pr': number,
            'url': f'https://github.com/{api.repository}/pull/{number}/checks'}


def merge(api, number, expected_head=None):
    require(number > 0, 'Invalid PR number')
    pr = api.get('pulls/' + str(number))
    branch, base = target(api)
    require(expected_head is None or pr['head']['sha'] == expected_head, 'PR head changed while waiting for publication')
    require(pr['base']['ref'] == branch and pr['base']['repo']['full_name'] == api.repository,
            'Publication requires the protected default branch')
    if pr.get('merged'):
        return pr
    require(pr['state'] == 'open' and not pr['draft'], 'A closed or draft PR cannot be published')
    require(pr.get('mergeable_state') == 'clean', 'PR checks or reviews are incomplete; rerun publish when mergeable')
    current(api, branch, base)
    result = api.request('pulls/' + str(number) + '/merge',
                         {'sha': pr['head']['sha'], 'merge_method': 'squash'}, method='PUT')
    require(result.get('merged') is True, 'GitHub did not merge the requested PR')
    return api.get('pulls/' + str(number))


def complete_publication(api, result, wait_seconds):
    require(0 <= wait_seconds <= 1800, 'Publication wait must be between 0 and 1800 seconds')
    if not wait_seconds:
        return result
    deadline = time.monotonic() + wait_seconds
    while True:
        pr = api.get('pulls/' + str(result['pr']))
        require(pr['head']['sha'] == result['head_sha'], 'Publication PR head changed; review it explicitly')
        if pr.get('merged'):
            return dict(result, status='synchronized', next_action='Revalidation and catalog publication run automatically.')
        require(pr['state'] == 'open', 'Publication PR was closed without merging')
        if pr.get('mergeable_state') == 'clean':
            merge(api, result['pr'], expected_head=result['head_sha'])
            return dict(result, status='synchronized', next_action='Revalidation and catalog publication run automatically.')
        if time.monotonic() >= deadline:
            return dict(result, status='waiting_checks_or_review')
        time.sleep(min(10, max(0, deadline - time.monotonic())))


def publish(api, identifier, *, pr=None, approval=None, release_tag=None, wait_seconds=0):
    require(bool(ID.fullmatch(identifier)) and len(identifier) <= 80, 'Invalid candidate ID')
    require(not (approval and release_tag), 'Select either a new approval or an existing acceptance release')
    require(pr is None or pr > 0, 'Invalid PR number')
    require(0 <= wait_seconds <= 1800, 'Publication wait must be between 0 and 1800 seconds')
    if pr:
        # Do not merge an unrelated maintenance/candidate PR via this entrypoint.
        paths = [x['filename'] for x in api.pages(f'pulls/{pr}/files')]
        require('candidates/' + identifier + '.json' in paths and all(
            p == 'candidates/' + identifier + '.json' or p.startswith('proofs/' + identifier + '/') and p.endswith('.lean')
            for p in paths), 'Publish PR must contain only this candidate and its proof bridge')
        merge(api, pr)
    branch, base = target(api)
    registry, publications, readme = snapshot(api, branch, base)
    require(identifier in registry['candidates'], 'Candidate is not registered on the default branch')
    old = next((p for p in publications['publications'] if p['candidate_id'] == identifier), None)
    if approval or release_tag:
        from .acceptance import accept, import_release
        identity = problem_identity(registry, identifier)
        entry = (accept(api, registry['candidates'][identifier], identifier, approval, branch, base, prior=old, identity=identity)
                 if approval else import_release(api, registry['candidates'][identifier], identifier, release_tag, identity=identity))
        require(old is None or old == entry, 'Existing acceptance reference is immutable; use a reviewed version change')
        if old is None:
            publications['publications'].append(entry)
    from .catalog import publication_history
    verified = publication_history(api, publications)
    generated = update(readme, render(registry, publications, api.repository, verified=verified))
    files = {}
    original_publications = decode(api.blob(api.tree(base)['docs/acceptance-publications.json']))
    if publications != original_publications:
        files['docs/acceptance-publications.json'] = json.dumps(publications, indent=2) + '\n'
    if generated != readme:
        files['README.md'] = generated
    current(api, branch, base)
    if files:
        result = open_change(api, branch, base, files, prefix='publication/' + identifier,
                             title='docs: publish ' + identifier + ' registration and acceptance',
                             body='Generate the registration summary and any validated immutable administrator acceptance reference.\n\n'
                                  'The candidate is already registered. Required checks and normal branch review still apply. '
                                  'Live machine status is separate from historical acceptance. No source, policy or verifier changes.')
        result['next_action'] = 'Required publication checks/review are pending; rerun publish to resume.'
        result = complete_publication(api, result, wait_seconds)
    else:
        result = {'status': 'synchronized'}
    result.update(step=4, registered=True,
                  catalog=f'https://{api.repository.split("/")[0]}.github.io/{api.repository.split("/")[1]}/')
    return result
