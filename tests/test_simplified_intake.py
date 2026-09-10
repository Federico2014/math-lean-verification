"""Synthetic intake and protected-main resumption; never compile candidate code."""
import copy
import os
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

    def test_orphan_candidate_paths_cannot_receive_not_applicable(self):
        from verifier.merge_gate import run
        pr = {'state': 'open', 'head': {'sha': 'c'*40},
              'base': {'sha': 'd'*40, 'ref': 'main', 'repo': {'full_name': 'example/registry'}}}
        api = Mock()
        api.get.return_value = pr
        with patch('verifier.merge_gate.ROOT', self.root), \
             patch('verifier.merge_gate.subprocess.check_output', return_value='d'*40), \
             patch('verifier.merge_gate.GitHub', return_value=api), \
             patch('verifier.merge_gate.proposal_snapshot') as snapshot, \
             patch('verifier.merge_gate.validate_registry', return_value=self.registry):
            for path in ('proofs/orphan/Bridge.lean', 'proofs/example-proof/Unused.lean',
                         'candidates/missing.json', 'submissions/missing.json', 'candidates/proof.txt'):
                snapshot.return_value = {path}
                with self.subTest(path=path), self.assertRaisesRegex(RegistryError, 'not bound'):
                    run('example/registry', 1, 'c'*40, None, self.root/'plan', check_only=True)
            snapshot.return_value = {'candidates/README.md'}
            self.assertEqual(run('example/registry', 1, 'c'*40, None, self.root/'plan', check_only=True)['status'],
                             'not_applicable')

    def test_candidate_metadata_only_edit_still_selects_verification(self):
        from verifier.merge_gate import candidate_changes
        self.assertEqual(candidate_changes(self.registry, {'candidates/example-proof.json'}), {'example-proof'})
        registry = copy.deepcopy(self.registry)
        registry['candidates']['example-proof']['bridge'] = 'Bridge.lean'
        self.assertEqual(candidate_changes(registry, {'proofs/example-proof/Bridge.lean'}), {'example-proof'})
        renamed = copy.deepcopy(registry)
        renamed['candidates']['example-proof']['bridge'] = 'Renamed.lean'
        self.assertEqual(candidate_changes(renamed, {'proofs/example-proof/Bridge.lean',
            'proofs/example-proof/Renamed.lean', 'candidates/example-proof.json'}, previous=registry), {'example-proof'})
        registry['submissions']['legacy'] = {'problem_id': 'test-problem',
            'execution': {'proof_files': [{'path': 'Bridge.lean'}]}}
        self.assertEqual(candidate_changes(registry, {'submissions/test-problem/legacy.json',
                                                     'proofs/legacy/Bridge.lean'}), {'legacy'})

    def test_candidate_plan_uses_its_explicit_checked_schema(self):
        from verifier.registry import plan_verification, schema_validate
        value = plan_verification(self.root, 'example-proof')
        self.assertEqual(value['plan_kind'], 'candidate_intake')
        schema_validate('candidate-plan', value)
        self.assertEqual(value['machine_status'], 'not_run')

    def test_candidate_delta_rejects_other_registrations_and_code(self):
        from verifier.merge_gate import candidate_delta
        candidate_delta(['example-proof'], {'candidates/example-proof.json', 'proofs/example-proof/Bridge.lean'})
        for path in ('submissions/other/proof.json', 'proofs/other/Bridge.lean', 'policy/verification.json',
                     '.github/workflows/lean-verification.yml', 'verifier/intake.py', 'README.md'):
            with self.subTest(path=path), self.assertRaises(RegistryError):
                candidate_delta(['example-proof'], {'candidates/example-proof.json', path})
        with self.assertRaises(RegistryError):
            candidate_delta(['first', 'second'], set())

    def test_mapping_rejects_different_transforms_for_same_source_path(self):
        from verifier.intake import mappings
        first = {'path': 'Proofs/Main.lean', 'destination': 'Proofs/Main.lean', 'sha256': 'a'*64, 'replacements': []}
        self.fixture.write('intake-mappings/example-proof.json', {'schema_version': 1,
            'candidate_digest': canonical_digest(self.candidate), 'problem_id': 'test-problem', 'statement_version': 'v1',
            'source_transforms': [first, dict(first, destination='Proofs/Other.lean')]})
        with self.assertRaisesRegex(RegistryError, 'Duplicate source transform'):
            mappings(self.root)


class ResumeTests(unittest.TestCase):
    def setup_api(self, runs=(), branch='main'):
        api = Mock(repository='example/registry')
        pr = {'number': 1, 'state': 'open', 'head': {'sha': 'a'*40, 'repo': {'full_name': api.repository}},
              'base': {'sha': 'b'*40, 'ref': branch, 'repo': {'full_name': api.repository}}}
        api.get.side_effect = lambda path: {'protected': True, 'commit': {'sha': 'b'*40}} if path == 'branches/' + branch else pr
        api.pages.side_effect = lambda path, *args, **kwargs: iter(
            runs if path.startswith('actions/') else [pr] if path.startswith('pulls?') else [{'filename': 'candidates/example.json'}])
        return api, pr

    def test_scheduler_entrypoint_uses_develop_checkout_without_main_revalidation(self):
        from verifier.resume import main
        env = {'GITHUB_ACTIONS': 'true', 'GITHUB_REF_NAME': 'develop',
               'GITHUB_REF': 'refs/heads/develop', 'GITHUB_SHA': 'b'*40,
               'GITHUB_REPOSITORY': 'example/registry'}
        with patch.dict(os.environ, env, clear=True), \
             patch('verifier.resume.subprocess.check_output', return_value='b'*40) as git, \
             patch('verifier.resume.GitHub') as api, \
             patch('verifier.resume.resume', return_value=[]) as scheduler, \
             patch('verifier.resume.Path.write_text'):
            main()
            scheduler.assert_called_once_with(api.return_value, 'b'*40, branch='develop')
            scheduler.reset_mock()
            git.return_value = 'c'*40
            with self.assertRaisesRegex(RegistryError, 'checkout differs'):
                main()
            scheduler.assert_not_called()

    def test_develop_resume_uses_its_own_branch_and_identity(self):
        previous = {'event': 'workflow_dispatch', 'display_title': marker(1, 'a'*40, 'b'*40, 'main'),
                    'head_sha': 'b'*40, 'head_repository': {'full_name': 'example/registry'}}
        api, pr = self.setup_api([previous], branch='develop')
        pr['base']['sha'] = 'e'*40  # Cached PR metadata must not prevent live-base recovery.
        self.assertEqual(resume(api, 'b'*40, Mock(return_value={'status': 'ready'}), branch='develop')[0]['status'], 'dispatched')
        self.assertEqual(api.request.call_args.args[1]['ref'], 'develop')
        api.pages.assert_any_call('pulls?state=open&base=develop')
        self.assertNotEqual(marker(1, 'a'*40, 'b'*40, 'main'), marker(1, 'a'*40, 'b'*40, 'develop'))

    def test_unprotected_scheduler_and_retargeted_pr_cannot_dispatch(self):
        api, pr = self.setup_api(branch='develop')
        api.get.side_effect = lambda path: {'protected': False, 'commit': {'sha': 'b'*40}} if path.startswith('branches/') else pr
        with self.assertRaisesRegex(RegistryError, 'must be protected'):
            resume(api, 'b'*40, Mock(), branch='develop')
        api.request.assert_not_called()
        api, pr = self.setup_api(branch='develop')
        def plan(*args, **kwargs):
            pr['base']['ref'] = 'main'
            return {'status': 'ready'}
        self.assertEqual(resume(api, 'b'*40, plan, branch='develop'), [])
        api.request.assert_not_called()

    @patch.dict(os.environ, {'GITHUB_RUN_ID': '456'})
    def test_blocked_pr_resumes_same_head_when_main_preparation_becomes_ready(self):
        api, pr = self.setup_api()
        planner = Mock(return_value={'status': 'blocked', 'blocked': {'example': 'waiting_environment'}})
        self.assertEqual(resume(api, 'b'*40, planner)[0]['status'], 'waiting')
        self.assertIn('/dispatches', api.request.call_args.args[0])
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

    def test_non_candidate_and_failed_plans_never_dispatch(self):
        for status in ('not_applicable', 'failed', 'passed', 'unknown'):
            api, _ = self.setup_api()
            with self.subTest(status=status):
                result = resume(api, 'b'*40, Mock(return_value={'status': status}))
                self.assertIn(result[0]['status'], ('not_applicable', 'blocked'))
                api.request.assert_not_called()

    def test_deleted_head_repository_does_not_starve_later_prs(self):
        api, first = self.setup_api()
        second = copy.deepcopy(first)
        second['number'] = 2
        second['head']['sha'] = 'c'*40
        first['head']['repo'] = None
        original = api.pages.side_effect
        api.pages.side_effect = lambda path, *args, **kwargs: iter([first, second]) if path.startswith('pulls?') else original(path, *args, **kwargs)
        api.get.side_effect = lambda path: {'protected': True, 'commit': {'sha': 'b'*40}} if path == 'branches/main' else second
        planner = Mock(return_value={'status': 'ready'})
        result = resume(api, 'b'*40, planner)
        self.assertEqual([r['status'] for r in result], ['blocked', 'dispatched'])
        planner.assert_called_once()
        self.assertEqual(api.request.call_args.args[1]['inputs']['pr'], '2')

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

    def test_oversized_pr_does_not_starve_later_candidate_prs(self):
        api, first = self.setup_api()
        second = copy.deepcopy(first)
        second['number'] = 2
        second['head']['sha'] = 'c'*40
        api.get.side_effect = lambda path: {'protected': True, 'commit': {'sha': 'b'*40}} if path == 'branches/main' else second
        def pages(path, *args, **kwargs):
            if path.startswith('actions/'):
                return iter([])
            if path.startswith('pulls?'):
                return iter([first, second])
            return iter([{'filename': 'candidates/example.json'}] * (3000 if path.startswith('pulls/1/') else 1))
        api.pages.side_effect = pages
        planner = Mock(return_value={'status': 'ready'})
        result = resume(api, 'b'*40, planner)
        self.assertEqual([r['status'] for r in result], ['blocked', 'dispatched'])
        self.assertEqual(api.request.call_args.args[1]['inputs']['pr'], '2')
        planner.assert_called_once()
