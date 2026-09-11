"""Explicit administrator acceptance publication, isolated from proof execution.

Only a current protected revalidation artifact can be the basis of a new decision.
Historical immutable releases remain importable without reissuing their decisions.
"""
import base64
from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

from .catalog import WORKFLOW, outcome, publication_history, trusted_run
from .evidence import inspect_archive
from .registry import require, schema_validate, statement_digest

MAX_ARCHIVE = 64 * 1024**2
REQUIRED_STAGES = {'sandbox_probes', 'challenge_clean_build_export', 'solution_clean_build_export',
                   'candidate_target_coverage', 'statement_comparison', 'transitive_axiom_audit',
                   'official_kernel_replay', 'independent_nanoda_replay'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_assets(api, release, files, directory):
    assets = {asset['name']: asset for asset in release['assets']}
    require(len(assets) == len(release['assets']) and set(assets) == set(files), 'Publication asset set differs')
    for name, data in files.items():
        asset = assets[name]
        require(asset.get('state') == 'uploaded' and asset.get('digest') == 'sha256:' + sha(data),
                'Publication asset checksum differs')
        destination = directory / name
        api.download('releases/assets/' + str(asset['id']), destination)
        require(destination.read_bytes() == data, 'Publication asset readback differs')


def archive_tree(api, files):
    entries = []
    for name, data in files.items():
        blob = api.request('git/blobs', {'content': base64.b64encode(data).decode(), 'encoding': 'base64'})
        expected = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        require(blob['sha'] == expected, 'Archive Git blob identity differs')
        entries.append({'path': name, 'mode': '100644', 'type': 'blob', 'sha': expected})
    tree = api.request('git/trees', {'tree': entries})
    return api.request('git/commits', {'message': 'Archive administrator acceptance',
                                      'tree': tree['sha'], 'parents': []})['sha']


def verify_tree(api, commit, files):
    tree = api.tree(commit)
    require(set(tree) == set(files), 'Archive Git file set differs')
    for name, data in files.items():
        item = tree[name]
        require(item['type'] == 'blob' and item['mode'] == '100644' and item['size'] == len(data),
                'Archive Git entry differs')
        blob = api.get('git/blobs/' + item['sha'])
        require(blob.get('encoding') == 'base64', 'Unsupported archive blob encoding')
        require(base64.b64decode(blob['content']) == data, 'Archive Git readback differs')


def import_release(api, candidate, identifier, tag):
    from .candidate import decode
    from .registry import ID
    require(bool(ID.fullmatch(tag)) and len(tag) <= 100, 'Invalid acceptance release tag')
    release = api.get('releases/tags/' + tag)
    require(release.get('draft') is False and release.get('immutable') is True, 'Acceptance release must be immutable and published')
    assets = [x for x in release['assets'] if x['name'] == 'acceptance.json']
    require(len(assets) == 1, 'Expected one acceptance record')
    with tempfile.TemporaryDirectory(prefix='acceptance-readback-') as temporary:
        path = Path(temporary) / 'acceptance.json'
        api.download('releases/assets/' + str(assets[0]['id']), path)
        raw = path.read_bytes()
        record = decode(raw)
    require(record.get('record_kind') == 'administrator_formal_acceptance' and record.get('formal_status') == 'accepted',
            'Not an administrator acceptance record')
    require(record['candidate_id'] == identifier and record['problem_id'] == candidate.get('problem_id', record['problem_id'])
            and record['statement_version'] == candidate.get('statement_version', record['statement_version']), 'Acceptance statement mismatch')
    require(record['review']['authority'] == release['author']['login'], 'Acceptance administrator mismatch')
    require(assets[0].get('digest') == 'sha256:' + sha(raw), 'Acceptance readback checksum mismatch')
    entry = {'candidate_id': identifier, 'problem_id': record['problem_id'],
             'statement_version': record['statement_version'], 'accepted_on': record['accepted_on'],
             'administrator': record['review']['authority'], 'source_commit': record['source']['commit'],
             'verifier_sha': record['bindings']['base_sha'], 'release_id': release['id'],
             'release_tag': tag, 'archive_commit': release['target_commitish'], 'record_sha256': sha(raw)}
    publication_history(api, {'schema_version': 1, 'publications': [entry]})
    return entry


def checked_evidence(api, candidate, identifier, approval, branch, base, directory):
    from .candidate import decode
    run_id, attempt = approval['run_id'], approval['run_attempt']
    run = api.get(f'actions/runs/{run_id}/attempts/{attempt}')
    workflow = api.get('actions/workflows/' + WORKFLOW)
    require(trusted_run(run, workflow, api.repository, branch) and run['head_sha'] == base
            and run['id'] == run_id and run['run_attempt'] == attempt and run['status'] == 'completed'
            and run.get('display_title') in (f'Revalidate {base} all', f'Revalidate {base} selected-{identifier}'),
            'Acceptance needs a completed protected revalidation for the approved revision')
    jobs = list(api.pages(f'actions/runs/{run_id}/attempts/{attempt}/jobs', 'jobs'))
    require(all(j['run_id'] == run_id and j['run_attempt'] == attempt and j['head_sha'] == base for j in jobs),
            'Verification job identity mismatch')
    require(sum(j['name'] == 'Verify candidate ' + identifier for j in jobs) == 1
            and outcome(run, jobs, identifier) == 'verified', 'Candidate proof was not verified')
    artifact = api.get('actions/artifacts/' + str(approval['artifact_id']))
    require(artifact.get('expired') is False and artifact['workflow_run']['id'] == run_id
            and artifact['workflow_run']['head_sha'] == base
            and artifact['name'] == f'revalidation-{identifier}-{base}-{attempt}', 'Evidence artifact identity mismatch')
    downloaded = directory / 'artifact.zip'
    api.download('actions/artifacts/' + str(approval['artifact_id']) + '/zip', downloaded)
    require(artifact.get('digest') == 'sha256:' + sha(downloaded.read_bytes()), 'Evidence artifact checksum mismatch')
    name = approval['archive_sha256'] + '.zip'
    with zipfile.ZipFile(downloaded) as outer:
        items = outer.infolist()
        require(len(items) <= 20000 and sum(i.file_size for i in items) <= MAX_ARCHIVE, 'Evidence artifact exceeds limits')
        matches = [i for i in items if i.filename.split('/')[-1] == name]
        require(len(matches) == 1 and matches[0].file_size <= MAX_ARCHIVE, 'Expected the approved sealed evidence archive')
        data = outer.read(matches[0])
    require(sha(data) == approval['archive_sha256'], 'Approved archive checksum mismatch')
    archive = directory / name
    archive.write_bytes(data)
    inspect_archive(archive)
    with zipfile.ZipFile(archive) as sealed:
        result = decode(sealed.read(identifier + '/verification-result.json'))
        problem = decode(sealed.read(identifier + '/inputs/problem.json'))
        submitted = decode(sealed.read(identifier + '/inputs/candidate.json'))
    schema_validate('result', result)
    schema_validate('problem', problem)
    require(submitted == candidate, 'Candidate changed since the approved proof run')
    require(result['submission_id'] == identifier and result['verification_status'] == 'verified'
            and result['machine_status'] == 'passed' and result['review_status'] == 'approved'
            and result.get('failed_stage') is None and REQUIRED_STAGES <= set(result['completed_stages']),
            'Incomplete verification evidence')
    require(result['bindings']['base_sha'] == base and result['bindings']['upstream_commit'] == approval['source_commit']
            and result['bindings']['run_id'] == str(run_id) and result['bindings']['run_attempt'] == str(attempt),
            'Proof bindings differ from administrator approval')
    require(statement_digest(problem) == approval['statement_digest'] and
            problem['problem_id'] == candidate.get('problem_id', problem['problem_id']) and
            problem['statement_version'] == candidate.get('statement_version', problem['statement_version']),
            'Approved statement differs from verified statement')
    return data, result, problem


def accept(api, candidate, identifier, approval_path, branch, base):
    from .candidate import current, decode
    from .registry import read_json, safe_file
    approval = read_json(safe_file(approval_path.parent, approval_path.name))
    schema_validate('administrator-acceptance', approval)
    require(approval['candidate_id'] == identifier and approval['source_commit'] == candidate['source']['commit'],
            'Approval does not match the registered candidate')
    require(date.fromisoformat(approval['accepted_on']) <= date.today(), 'Acceptance date is in the future')
    require(api.viewer()['login'] == approval['administrator'] and api.get('')['permissions']['admin'] is True,
            'The authenticated administrator must make this acceptance decision')
    require(api.get('immutable-releases').get('enabled') is True, 'Enable immutable releases before publishing acceptance')
    tag = 'acceptance-' + identifier[:40] + '-' + hashlib.sha256(json.dumps(approval, sort_keys=True).encode()).hexdigest()[:24]
    existing = next((r for r in api.pages('releases') if r['tag_name'] == tag), None)
    if existing and existing.get('draft') is False:
        return import_release(api, candidate, identifier, tag)
    require(approval['verifier_sha'] == base, 'Approval verifier revision is stale; review current evidence')
    with tempfile.TemporaryDirectory(prefix='administrator-acceptance-') as temporary:
        directory = Path(temporary)
        data, result, problem = checked_evidence(api, candidate, identifier, approval, branch, base, directory)
        record = {'schema_version': 1, 'record_kind': 'administrator_formal_acceptance',
                  'formal_status': 'accepted', 'candidate_id': identifier, 'problem_id': problem['problem_id'],
                  'statement_version': problem['statement_version'], 'statement_digest': approval['statement_digest'],
                  'accepted_on': approval['accepted_on'], 'source': candidate['source'], 'bindings': result['bindings'],
                  'review': {'authority': approval['administrator'], 'approval_kind': 'administrator_attestation',
                             'evidence': approval['reason'], 'independent_review_records_supplied': False},
                  'administrator_approval': approval,
                  'machine_evidence': {'archive': approval['archive_sha256'] + '.zip',
                                       'archive_sha256': approval['archive_sha256'],
                                       'run_url': f'https://github.com/{api.repository}/actions/runs/{approval["run_id"]}/attempts/{approval["run_attempt"]}'},
                  'decision_scope': 'Administrator acceptance for these fixed inputs; no independent two-reviewer or award decision.',
                  'archival_policy': 'Retain immutable release assets and tagged Git backup indefinitely; verify checksums after migration and annually. Both copies use GitHub.'}
        files = {'acceptance.json': (json.dumps(record, indent=2) + '\n').encode(),
                 approval['archive_sha256'] + '.zip': data}
        files['SHA256SUMS'] = ''.join(sha(data) + '  ' + name + '\n' for name, data in sorted(files.items())).encode()
        current(api, branch, base)
        if existing:
            release = api.get('releases/' + str(existing['id']))
            require(release['author']['login'] == approval['administrator'], 'Draft administrator mismatch')
            commit = release['target_commitish']
        else:
            commit = archive_tree(api, files)
            verify_tree(api, commit, files)
            release = api.request('releases', {'tag_name': tag, 'target_commitish': commit,
                'name': 'Administrator acceptance: ' + identifier, 'draft': True,
                'body': 'Explicit administrator acceptance for the revisions in acceptance.json. '
                        'The archive and SHA256SUMS preserve the evidence. Independent two-reviewer and award decisions are not asserted.'})
        verify_tree(api, commit, files)
        assets = {a['name']: a for a in release['assets']}
        require(set(assets) <= set(files), 'Draft contains unexpected assets')
        for name, data in files.items():
            if name not in assets:
                upload = directory / 'uploads' / name
                upload.parent.mkdir(exist_ok=True)
                upload.write_bytes(data)
                api.upload(release['id'], upload)
        release = api.get('releases/' + str(release['id']))
        readback = directory / 'readback'
        readback.mkdir()
        verify_assets(api, release, files, readback)
        current(api, branch, base)
        require(api.get('immutable-releases').get('enabled') is True, 'Release immutability changed during publication')
        api.request('releases/' + str(release['id']), {'draft': False}, method='PATCH')
        published = api.get('releases/' + str(release['id']))
        require(published.get('immutable') is True and published.get('draft') is False, 'Release was not published immutably')
        final = directory / 'published-readback'
        final.mkdir()
        verify_assets(api, published, files, final)
    return import_release(api, candidate, identifier, tag)
