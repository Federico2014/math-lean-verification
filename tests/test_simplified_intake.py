"""Synthetic intake and protected-main resumption; never compile candidate code."""
import copy
import os
from pathlib import Path
import shutil
import unittest
from unittest.mock import Mock, patch

from verifier.environments import load_environments
from verifier.intake import imports, prepare_one
from verifier.registry import ROOT, RegistryError, canonical_digest, statement_digest, validate_registry
from verifier.resume import marker, resume


class IntakeTests(unittest.TestCase):
    def setUp(self):
        from test_registry import RegistryTests
        self.fixture = f = RegistryTests()
        f.setUp()
        self.addCleanup(f.temp.cleanup)
        self.root = f.root
        shutil.copytree(ROOT / 'environments', f.root / 'environments')
        self.env = load_environments(f.root)['lean-4-34-rc2-stdlib']
        f.problem['toolchain_id'] = self.env['environment_id']
        f.problem['workspace'] = {'environment_digest': canonical_digest(self.env),
            'solution_module': 'Bridge', 'submission_paths': ['Proofs/**', 'Bridge.lean', 'CandidateChallenge.lean']}
        f.policy['approved_reviewers'] = ['reviewer-one', 'reviewer-two']
        f.problem['original_sources'][0]['snapshot_sha256'] = 'b'*64
        f.problem['review'] = {'status': 'approved', 'statement_digest': statement_digest(f.problem),
            'reviewers': ['reviewer-one', 'reviewer-two'], 'evidence_url': 'https://example.org/review'}
        f.write('policy/verification.json', f.policy)
        f.write('problems/test-problem/v1/problem.json', f.problem)
        (f.root / 'submissions/test-problem/test-submission.json').unlink()
        self.candidate = {'schema_version': 1, 'title': 'Synthetic only', 'problem_id': 'test-problem',
            'source': {'repository': 'https://github.com/example/proof', 'commit': 'a'*40},
            'targets': [{'module': 'Proofs.Main', 'declaration': 'upstream'}],
            'attribution': {k: v for k, v in f.submission['contribution'].items() if k != 'public_source_authorized'},
            'public_source_authorized': True}
        f.write('candidates/example-proof.json', self.candidate)
        self.registry = validate_registry(f.root)
        self.sources = {'lean-toolchain': ('leanprover/lean4:' + self.env['lean_release']).encode(),
                        'lakefile.toml': b'name = "example"\n[[lean_lib]]\nname = "Proofs"\n',
                        'Proofs/Main.lean': b'import Proofs.Helper\ntheorem upstream : True := helper\n',
                        'Proofs/Helper.lean': b'theorem helper : True := by trivial\n',
                        'Unused.lean': b'theorem unused : False := by sorry\n'}
        self.api = Mock()
        self.api.tree.side_effect = lambda sha: {k: {'data': v} for k, v in self.sources.items()}
        self.api.blob.side_effect = lambda item: item['data']

    def prepare(self, registry=None):
        return prepare_one('example-proof', self.candidate, registry or self.registry,
                           self.root, self.root, self.root / 'generated', lambda _: self.api)

    def test_preparation_closes_local_imports_and_generates_bound_bridge(self):
        value = self.prepare()
        self.assertEqual(value['intake_status'], 'ready', value)
        self.assertEqual(value['machine_status'], 'not_run')
        self.assertEqual(value['submission']['execution']['include'], ['Proofs/Helper.lean', 'Proofs/Main.lean'])
        self.assertEqual(value['submission']['targets'][0]['official_theorem'], 'target')
        bridge = self.root / 'generated/proofs/example-proof/Bridge.lean'
        self.assertIn('Lean.getConstInfo `upstream', bridge.read_text())
        self.assertIn('name := `target', bridge.read_text())
        self.assertIn('levelParams := info.levelParams', bridge.read_text())
        self.assertEqual(value['candidate_digest'], canonical_digest(self.candidate))
        self.assertEqual(value['environment_digest'], canonical_digest(self.env))
        self.assertNotIn('Unused.lean', value['source_hashes'])

    def test_missing_approvals_accumulate_without_fetching_without_permission(self):
        registry = copy.deepcopy(self.registry)
        registry['problems']['test-problem', 'v1']['review']['status'] = 'pending'
        registry['policy']['toolchains'] = []
        value = self.prepare(registry)
        self.assertEqual({b['status'] for b in value['blockers']}, {'waiting_review', 'waiting_environment'})
        self.api.reset_mock()
        self.candidate['public_source_authorized'] = False
        self.assertEqual(self.prepare()['intake_status'], 'needs_information')
        self.api.tree.assert_not_called()

    def test_static_metadata_review_requires_exact_candidate_and_metadata_binding(self):
        self.sources['lakefile.lean'] = b'-- never execute dynamic Lake\n'
        blocked = self.prepare()
        self.assertEqual(blocked['intake_status'], 'needs_adaptation')
        mapping = {'schema_version': 1, 'candidate_digest': canonical_digest(self.candidate),
                   'problem_id': 'test-problem', 'statement_version': 'v1',
                   'reviewed_metadata_sha256': blocked['metadata_digest']}
        self.fixture.write('intake-mappings/example-proof.json', mapping)
        self.assertEqual(self.prepare()['intake_status'], 'ready')
        self.sources['lakefile.lean'] += b'-- changed\n'
        self.assertEqual(self.prepare()['intake_status'], 'needs_adaptation')
        self.candidate['title'] = 'changed materials'
        self.assertIn('stale', self.prepare()['blockers'][0]['reason'])

    def test_protected_collision_is_renamed_with_exact_import_replacement(self):
        self.sources['Proofs/Main.lean'] = b'import Challenge\ntheorem upstream : True := helper\n'
        self.sources['Challenge.lean'] = b'theorem helper : True := by trivial\n'
        value = self.prepare()
        self.assertEqual(value['intake_status'], 'ready', value)
        transforms = {t['path']: t for t in value['submission']['execution']['source_transforms']}
        self.assertEqual(transforms['Challenge.lean']['destination'], 'CandidateChallenge.lean')
        self.assertEqual(transforms['Proofs/Main.lean']['replacements'][0]['new'], 'import CandidateChallenge\n')

    def test_missing_import_selection_and_path_conflicts_stay_nonpassing(self):
        self.candidate['source']['include'] = ['Proofs/Main.lean']
        self.assertEqual(self.prepare()['intake_status'], 'needs_adaptation')
        self.candidate['source'].pop('include')
        self.sources['Proofs/Main.lean'] = b'import Bridge\ntheorem upstream : True := by trivial\n'
        self.sources['Bridge.lean'] = b'-- conflicting bridge\n'
        self.assertEqual(self.prepare()['intake_status'], 'needs_adaptation')

    def test_import_comments_and_strings_are_not_dependencies(self):
        self.assertEqual(imports(b'/-- import Bad -/\nimport Good -- comment\n#check "import Fake"\n'), ['Good'])
        with self.assertRaises(RegistryError):
            imports(b'/- unterminated')


    def test_open_pr_uses_new_main_approval_without_changing_candidate_head(self):
        from verifier.merge_gate import run
        candidate_path = self.root / 'candidates/example-proof.json'
        candidate_bytes = candidate_path.read_bytes()
        candidate_path.unlink()
        pending = copy.deepcopy(self.fixture.problem)
        pending['review'] = {'status': 'pending', 'statement_digest': None, 'reviewers': [], 'evidence_url': None}
        self.fixture.write('problems/test-problem/v1/problem.json', pending)
        pr = {'state': 'open', 'head': {'sha': 'c'*40},
              'base': {'sha': 'd'*40, 'ref': 'main', 'repo': {'full_name': 'example/registry'}}}
        registry_api = Mock()
        registry_api.get.side_effect = lambda path: ([{'filename': 'candidates/example-proof.json'}]
                                                    if '/files?' in path else pr)
        # The old PR tree deliberately has no current workspace or approvals.
        registry_api.tree.return_value = {'candidates/example-proof.json': {'data': candidate_bytes}}
        registry_api.blob.side_effect = lambda item: item['data']
        with patch('verifier.merge_gate.ROOT', self.root), \
             patch('verifier.merge_gate.subprocess.check_output', side_effect=lambda *args, **kwargs: pr['base']['sha']), \
             patch('verifier.merge_gate.GitHub', side_effect=lambda repo: registry_api if repo == 'example/registry' else self.api):
            result = run('example/registry', 1, 'c'*40, None, self.root/'plan', check_only=True)
            self.assertEqual(result['status'], 'blocked')
            self.assertEqual(result['blocked']['example-proof']['intake_status'], 'waiting_review')
            self.fixture.write('problems/test-problem/v1/problem.json', self.fixture.problem)
            pr['base']['sha'] = 'e'*40
            result = run('example/registry', 1, 'c'*40, None, self.root/'plan', check_only=True)
            self.assertEqual(result['status'], 'ready', result)
            self.assertEqual(result['head_sha'], 'c'*40)
            self.assertEqual(result['verifier_sha'], 'e'*40)
            self.assertEqual(result['matrix']['include'][0]['submission'], 'example-proof')

    def test_description_only_requires_protected_problem_mapping(self):
        self.candidate.pop('problem_id')
        self.candidate['problem'] = {'title': 'Synthetic test', 'source_url': 'https://example.org/unrelated', 'scope': 'different'}
        self.assertEqual(self.prepare()['intake_status'], 'waiting_problem')


class ResumeTests(unittest.TestCase):
    def setup_api(self, runs=()):
        api = Mock(repository='example/registry')
        pr = {'number': 1, 'state': 'open', 'head': {'sha': 'a'*40},
              'base': {'sha': 'b'*40, 'ref': 'main', 'repo': {'full_name': api.repository}}}
        api.get.side_effect = lambda path: {'commit': {'sha': 'b'*40}} if path == 'branches/main' else pr
        api.pages.side_effect = lambda path, *args, **kwargs: iter(
            runs if path.startswith('actions/') else [pr] if path.startswith('pulls?') else [{'filename': 'candidates/example.json'}])
        return api, pr

    @patch.dict(os.environ, {'GITHUB_RUN_ID': '456'})
    def test_blocked_pr_resumes_same_head_when_main_preparation_becomes_ready(self):
        api, pr = self.setup_api()
        planner = Mock(return_value={'status': 'blocked', 'blocked': {'example': 'waiting_environment'}})
        self.assertEqual(resume(api, 'b'*40, planner)[0]['status'], 'waiting')
        self.assertIn('statuses/', api.request.call_args.args[0])
        api.request.reset_mock()
        planner.return_value = {'status': 'ready'}
        self.assertEqual(resume(api, 'b'*40, planner)[0]['status'], 'dispatched')
        request = api.request.call_args.args[1]
        self.assertEqual(request, {'ref': 'main', 'inputs': {'pr': '1', 'expected_head': 'a'*40, 'expected_base': 'b'*40}})

    def test_repeat_dispatch_and_closed_pr_are_suppressed(self):
        previous = {'event': 'workflow_dispatch', 'display_title': marker(1, 'a'*40, 'b'*40), 'head_sha': 'b'*40,
                    'head_repository': {'full_name': 'example/registry'}}
        api, pr = self.setup_api([previous])
        planner = Mock()
        self.assertEqual(resume(api, 'b'*40, planner)[0]['status'], 'already_dispatched')
        planner.assert_not_called()
        pr['state'] = 'closed'
        self.assertEqual(resume(api, 'b'*40, planner), [])
        api.request.assert_not_called()

    def test_head_change_during_preparation_cannot_dispatch(self):
        api, pr = self.setup_api()
        def plan(*args, **kwargs):
            pr['head']['sha'] = 'c'*40
            return {'status': 'ready'}
        self.assertEqual(resume(api, 'b'*40, plan), [])
        api.request.assert_not_called()

    def test_only_one_retry_before_execution_and_never_retry_proof_failure(self):
        previous = {'event': 'workflow_dispatch', 'display_title': marker(1, 'a'*40, 'b'*40),
                    'head_sha': 'b'*40, 'head_repository': {'full_name': 'example/registry'},
                    'status': 'completed', 'conclusion': 'failure', 'run_attempt': 1, 'id': 77}
        api, pr = self.setup_api([previous])
        original = api.pages.side_effect
        jobs = [{'steps': []}]
        api.pages.side_effect = lambda path, *args, **kwargs: iter(jobs) if '/attempts/' in path else original(path, *args, **kwargs)
        self.assertEqual(resume(api, 'b'*40, Mock(return_value={'status': 'ready'}))[0]['status'], 'dispatched')
        api.request.reset_mock()
        jobs[0]['steps'] = [{'name': 'Verify every required target and its trusted statement',
                             'status': 'completed', 'conclusion': 'failure'}]
        self.assertEqual(resume(api, 'b'*40, Mock())[0]['status'], 'already_dispatched')
        api.request.assert_not_called()
        # Two attempts at dispatch exhaust the automatic retry budget.
        api, pr = self.setup_api([previous, dict(previous, id=78)])
        self.assertEqual(resume(api, 'b'*40, Mock())[0]['status'], 'already_dispatched')

    def test_initial_pr_run_uses_pr_head_for_deduplication(self):
        previous = {'event': 'pull_request_target', 'display_title': marker(1, 'a'*40, 'b'*40),
                    'head_sha': 'a'*40, 'head_repository': {'full_name': 'example/registry'},
                    'status': 'in_progress'}
        api, pr = self.setup_api()
        pr['head']['repo'] = {'full_name': 'contributor/fork'}
        previous['head_repository'] = {'full_name': 'contributor/fork'}
        original = api.pages.side_effect
        api.pages.side_effect = lambda path, *args, **kwargs: iter([previous]) if 'head_sha=' + 'a'*40 in path else original(path, *args, **kwargs)
        planner = Mock()
        self.assertEqual(resume(api, 'b'*40, planner)[0]['status'], 'already_dispatched')
        planner.assert_not_called()
        api.request.assert_not_called()
