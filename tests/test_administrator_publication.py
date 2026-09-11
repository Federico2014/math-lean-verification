"""Synthetic archive and API provenance tests; never evidence of a real proof pass."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from verifier.acceptance import REQUIRED_STAGES, accept, checked_evidence, import_release, sha
from verifier.catalog import EXECUTION_STEP, PATH
from verifier.evidence import seal
from verifier.registry import RegistryError, statement_digest
from test_candidate_workflow import candidate


class MemoryAPI:
    repository = 'example/registry'

    def __init__(self, fixture):
        self.f = fixture
        self.admin = True
        self.user = 'maintainer'
        self.immutable = True
        self.bad_readback = False
        self.releases = []
        self.blobs = {}
        self.trees = {}
        self.commits = {}
        self.asset_data = {}
        self.writes = []

    def viewer(self): return {'login': self.user}

    def get(self, path):
        if path == '': return {'default_branch': 'develop', 'permissions': {'admin': self.admin}}
        if path == 'branches/develop': return {'protected': True, 'commit': {'sha': self.f.base}}
        if path == 'immutable-releases': return {'enabled': self.immutable}
        if path == 'actions/runs/10/attempts/1': return self.f.run
        if path == 'actions/workflows/revalidate.yml': return {'id': 7, 'path': PATH}
        if path == 'actions/artifacts/20': return self.f.artifact
        if path.startswith('git/blobs/'):
            return {'encoding': 'base64', 'content': base64.b64encode(self.blobs[path.split('/')[-1]]).decode()}
        if path.startswith('releases/tags/'):
            return next(r for r in self.releases if r['tag_name'] == path.removeprefix('releases/tags/'))
        if path.startswith('releases/'):
            return next(r for r in self.releases if r['id'] == int(path.split('/')[-1]))
        if path.startswith('git/ref/tags/'):
            tag = path.removeprefix('git/ref/tags/')
            r = next(r for r in self.releases if r['tag_name'] == tag and not r['draft'])
            commit = r['target_commitish']
            return {'object': {'sha': commit, 'type': 'commit',
                               'url': f'https://api.github.com/repos/{self.repository}/git/commits/{commit}'}}
        raise AssertionError('Unexpected get: ' + path)

    def pages(self, path, key=None, **kwargs):
        if path == 'actions/runs/10/attempts/1/jobs': return iter([self.f.job])
        if path == 'releases': return iter(self.releases)
        raise AssertionError('Unexpected pages: ' + path)

    def request(self, path, data=None, method=None):
        self.writes.append((path, copy.deepcopy(data), method))
        if path == 'git/blobs':
            raw = base64.b64decode(data['content'])
            identity = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
            self.blobs[identity] = raw
            return {'sha': identity}
        if path == 'git/trees':
            identity = hashlib.sha1(json.dumps(data).encode()).hexdigest()
            self.trees[identity] = data['tree']
            return {'sha': identity}
        if path == 'git/commits':
            identity = hashlib.sha1(json.dumps(data).encode()).hexdigest()
            self.commits[identity] = data['tree']
            return {'sha': identity}
        if path == 'releases':
            value = dict(data, id=len(self.releases)+1, assets=[], immutable=False,
                         published_at=None, author={'login': self.user})
            self.releases.append(value)
            return value
        if path.startswith('releases/') and method == 'PATCH':
            value = self.get(path)
            value.update(data, immutable=self.immutable, published_at='2026-09-11T00:00:00Z')
            return value
        raise AssertionError('Unexpected request: ' + path)

    def tree(self, commit):
        return {e['path']: dict(e, size=len(self.blobs[e['sha']])) for e in self.trees[self.commits[commit]]}

    def upload(self, release_id, path):
        data = path.read_bytes()
        asset = {'id': len(self.asset_data)+1, 'name': path.name, 'state': 'uploaded',
                 'digest': 'sha256:' + sha(data)}
        self.asset_data[asset['id']] = data
        self.get('releases/' + str(release_id))['assets'].append(asset)
        self.writes.append(('upload', path.name, None))
        return asset

    def download(self, path, output):
        if path == 'actions/artifacts/20/zip': data = self.f.outer.read_bytes()
        elif path.startswith('releases/assets/'):
            data = self.asset_data[int(path.split('/')[-1])]
            if self.bad_readback: data += b'tampered'
        else: raise AssertionError('Unexpected download: ' + path)
        with output.open('xb') as stream: stream.write(data)


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        from test_registry import RegistryTests
        self.fixture = RegistryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.temp.cleanup)
        self.fixture.approve_for_test()
        self.root = self.fixture.root
        self.base = 'b'*40
        self.identifier = 'test-candidate'
        self.candidate = candidate()
        self.result = {'schema_version': 1, 'submission_id': self.identifier,
            'verification_status': 'verified', 'machine_status': 'passed', 'review_status': 'approved',
            'formal_status': 'pending', 'bindings': {'pr_head': None, 'base_sha': self.base,
            'upstream_commit': 'a'*40, 'workspace_digest': 'c'*64, 'environment_digest': 'd'*64,
            'policy_digest': 'e'*64, 'run_id': '10', 'run_attempt': '1'},
            'official_targets': ['target'], 'candidate_targets': ['Submission.target'],
            'completed_stages': sorted(REQUIRED_STAGES), 'failed_stage': None,
            'input_digest': 'f'*64, 'image_id': 'sha256:'+'0'*64, 'error': None,
            'review_approval_kind': 'independent_review', 'review_administrator': None}
        self.approval = {'schema_version': 1, 'decision': 'accepted', 'candidate_id': self.identifier,
            'administrator': 'maintainer', 'accepted_on': '2026-09-11', 'reason': 'Synthetic explicit decision only.',
            'run_id': 10, 'run_attempt': 1, 'artifact_id': 20, 'verifier_sha': self.base,
            'source_commit': 'a'*40, 'statement_digest': statement_digest(self.fixture.problem),
            'archive_sha256': '0'*64}
        self.run = {'id': 10, 'run_attempt': 1, 'workflow_id': 7, 'path': PATH,
            'event': 'push', 'head_branch': 'develop', 'head_sha': self.base,
            'repository': {'full_name': 'example/registry'}, 'head_repository': {'full_name': 'example/registry'},
            'status': 'completed', 'display_title': f'Revalidate {self.base} all'}
        self.job = {'run_id': 10, 'run_attempt': 1, 'head_sha': self.base,
            'name': 'Verify candidate ' + self.identifier, 'status': 'completed', 'conclusion': 'success',
            'steps': [{'name': EXECUTION_STEP, 'status': 'completed', 'conclusion': 'success'}]}
        self.api = MemoryAPI(self)
        self.approval_path = self.root / 'approval.json'
        self.rebuild()

    def rebuild(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = root / 'evidence'
            inputs = evidence / self.identifier / 'inputs'
            inputs.mkdir(parents=True)
            (inputs / 'candidate.json').write_text(json.dumps(self.candidate))
            (inputs / 'problem.json').write_text(json.dumps(self.fixture.problem))
            (inputs.parent / 'verification-result.json').write_text(json.dumps(self.result))
            sealed = seal(evidence, root / 'sealed')
            self.approval['archive_sha256'] = sealed.stem
            self.outer = self.root / 'artifact.zip'
            with zipfile.ZipFile(self.outer, 'w') as archive:
                archive.write(sealed, 'sealed/' + sealed.name)
        self.artifact = {'expired': False, 'workflow_run': {'id': 10, 'head_sha': self.base},
            'name': f'revalidation-{self.identifier}-{self.base}-1', 'digest': 'sha256:' + sha(self.outer.read_bytes())}
        self.approval_path.write_text(json.dumps(self.approval))

    def check(self):
        with tempfile.TemporaryDirectory() as temporary:
            return checked_evidence(self.api, self.candidate, self.identifier, self.approval,
                                    'develop', self.base, Path(temporary))

    def accept(self):
        self.approval_path.write_text(json.dumps(self.approval))
        return accept(self.api, self.candidate, self.identifier, self.approval_path, 'develop', self.base)

    def test_archive_provenance_and_readback_produce_one_explicit_historical_decision(self):
        entry = self.accept()
        self.assertEqual(entry['administrator'], 'maintainer')
        self.assertEqual(entry['verifier_sha'], self.base)
        self.assertTrue(self.api.releases[0]['immutable'])
        self.assertFalse(self.api.releases[0]['draft'])
        self.assertEqual(len(self.api.releases[0]['assets']), 3)
        record = json.loads(next(self.api.asset_data[a['id']] for a in self.api.releases[0]['assets'] if a['name'] == 'acceptance.json'))
        self.assertFalse(record['review']['independent_review_records_supplied'])
        self.assertEqual(record['administrator_approval'], self.approval)
        self.assertEqual(record['bindings'], self.result['bindings'])
        writes = len(self.api.writes)
        self.assertEqual(self.accept(), entry)
        self.assertEqual(len(self.api.writes), writes)

    def test_missing_approval_wrong_administrator_or_disabled_immutability_never_write(self):
        for change in ('decision', 'administrator', 'permission', 'immutability', 'revision', 'date'):
            with self.subTest(change=change):
                approval = copy.deepcopy(self.approval)
                if change == 'decision': self.approval['decision'] = 'pending'
                if change == 'administrator': self.api.user = 'someone-else'
                if change == 'permission': self.api.admin = False
                if change == 'immutability': self.api.immutable = False
                if change == 'revision': self.approval['verifier_sha'] = '0'*40
                if change == 'date': self.approval['accepted_on'] = '2999-01-01'
                with self.assertRaises(RegistryError): self.accept()
                self.assertEqual(self.api.writes, [])
                self.approval = approval
                self.api.user, self.api.admin, self.api.immutable = 'maintainer', True, True

    def test_foreign_run_wrong_attempt_failed_job_and_missing_execution_are_rejected(self):
        run, job = copy.deepcopy(self.run), copy.deepcopy(self.job)
        for change in ('fork', 'workflow', 'revision', 'attempt', 'title', 'failed', 'skipped'):
            with self.subTest(change=change):
                self.run, self.job = copy.deepcopy(run), copy.deepcopy(job)
                if change == 'fork': self.run['event'] = 'pull_request'
                if change == 'workflow': self.run['workflow_id'] = 99
                if change == 'revision': self.run['head_sha'] = '0'*40
                if change == 'attempt': self.job['run_attempt'] = 2
                if change == 'title': self.run['display_title'] = 'forged success'
                if change == 'failed': self.job['conclusion'] = 'failure'
                if change == 'skipped': self.job['steps'] = []
                with self.assertRaises(RegistryError): self.check()

    def test_expired_substituted_or_corrupted_artifacts_are_rejected(self):
        original = copy.deepcopy(self.artifact)
        for key, value in [('expired', True), ('name', 'untrusted-artifact'), ('digest', 'sha256:'+'0'*64),
                           ('workflow_run', {'id': 11, 'head_sha': self.base})]:
            self.artifact = dict(original, **{key: value})
            with self.subTest(key=key), self.assertRaises(RegistryError): self.check()

    def test_failed_result_missing_stage_wrong_statement_or_changed_source_is_rejected(self):
        result = copy.deepcopy(self.result)
        for change in ('failed', 'stage', 'run', 'source', 'statement'):
            self.result = copy.deepcopy(result)
            approval = copy.deepcopy(self.approval)
            if change == 'failed': self.result['machine_status'] = 'failed'
            if change == 'stage': self.result['completed_stages'].remove('independent_nanoda_replay')
            if change == 'run': self.result['bindings']['run_id'] = '11'
            if change == 'source': self.result['bindings']['upstream_commit'] = '0'*40
            if change == 'statement': self.approval['statement_digest'] = '0'*64
            self.rebuild()
            with self.subTest(change=change), self.assertRaises(RegistryError): self.check()
            self.approval = approval

    def test_failed_readback_leaves_draft_unpublished_and_retry_resumes(self):
        self.api.bad_readback = True
        with self.assertRaisesRegex(RegistryError, 'readback'): self.accept()
        self.assertTrue(self.api.releases[0]['draft'])
        self.api.bad_readback = False
        entry = self.accept()
        self.assertEqual(len(self.api.releases), 1)
        self.assertEqual(len(self.api.releases[0]['assets']), 3)
        self.assertEqual(entry['candidate_id'], self.identifier)

    def test_import_rejects_mutable_release_and_tampered_record(self):
        entry = self.accept()
        release = self.api.releases[0]
        release['immutable'] = False
        with self.assertRaises(RegistryError): import_release(self.api, self.candidate, self.identifier, entry['release_tag'])
        release['immutable'] = True
        self.api.bad_readback = True
        with self.assertRaises(RegistryError): import_release(self.api, self.candidate, self.identifier, entry['release_tag'])
