"""Synthetic operator workflow tests; none establish Lean proof validity."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from verifier.candidate import Session, complete_publication, merge, open_change, prepare, publish, submit, verify
from verifier.registration import END, START, problem_identity, render, update
from verifier.registry import RegistryError, canonical_digest
from verifier.workflow import from_plan, progress


def candidate():
    return {'schema_version': 1, 'title': 'Synthetic candidate', 'problem_id': 'test-problem',
            'statement_version': 'v1',
            'source': {'repository': 'https://github.com/example/proof', 'commit': 'a'*40},
            'targets': [{'module': 'Submission', 'declaration': 'Submission.target'}],
            'attribution': {'proof_authors': ['Test'], 'formalization_authors': ['Test'],
                            'ai_role': 'None', 'proof_route': 'Synthetic', 'known_assumptions': []},
            'public_source_authorized': True}


class WorkflowTests(unittest.TestCase):
    def test_prerequisites_proof_and_acceptance_do_not_substitute_for_one_another(self):
        for status in ('pending', 'waiting_review', 'unsupported', 'invented'):
            value = progress(preparation=status, verification='verified', registered=True, acceptance={'url': 'historical'})
            self.assertEqual(value['current_step'], 2)
            self.assertNotEqual(value['steps'][2]['status'], 'complete')
        for status in ('not_run', 'failed', 'cancelled', 'running', 'queued'):
            value = progress(preparation='ready', verification=status, acceptance={'url': 'historical'})
            self.assertEqual(value['current_step'], 3)
            self.assertEqual(value['formal_status'], 'accepted_historical')
        value = progress(preparation='ready', verification='verified')
        self.assertEqual(value['current_step'], 4)
        self.assertEqual(value['steps'][3]['status'], 'pending')
        self.assertEqual(value['formal_status'], 'pending')

    def test_blocker_classifications_and_mixed_plans_remain_visible(self):
        for code in ('needs_information', 'waiting_problem', 'waiting_review', 'waiting_environment', 'needs_adaptation'):
            self.assertEqual(progress(preparation=code)['steps'][1]['status'], code)
        value = from_plan({'status': 'ready', 'blocked': {'waiting': {'intake_status': 'waiting_environment'}}})
        self.assertEqual(value['current_step'], 2)
        self.assertEqual(value['steps'][1]['status'], 'waiting_environment')
        self.assertEqual(value['blocked_candidates'], ['waiting'])

    def test_executed_failure_is_verification_failure_and_pass_reaches_publication(self):
        proof = {'machine_status': 'failed', 'verification_status': 'failed', 'review_status': 'approved'}
        value = from_plan({'status': 'failed', 'submissions': {'example': proof}})
        self.assertEqual(value['current_step'], 3)
        self.assertEqual(value['steps'][2]['status'], 'failed')
        self.assertEqual(from_plan({'status': 'passed'}, registered=True)['current_step'], 4)
        proof.update(machine_status='passed', verification_status='review_pending', review_status='pending')
        self.assertEqual(from_plan({'status': 'failed', 'submissions': {'example': proof}})['current_step'], 2)

    def test_ready_plan_is_not_a_proof_pass(self):
        value = from_plan({'status': 'ready'})
        self.assertEqual(value['current_step'], 3)
        self.assertEqual(value['steps'][2]['status'], 'not_run')


class OperatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.file = self.root / 'candidate.json'
        self.value = candidate()
        self.file.write_text(json.dumps(self.value))
        self.base = 'b'*40
        self.api = Mock(repository='example/registry')
        self.pr = {'number': 12, 'state': 'open', 'draft': False, 'merged': False,
                   'mergeable_state': 'clean', 'head': {'sha': 'c'*40},
                   'base': {'ref': 'develop', 'repo': {'full_name': 'example/registry'}}}
        def get(path):
            if path == '': return {'default_branch': 'develop'}
            if path == 'branches/develop': return {'protected': True, 'commit': {'sha': self.base}}
            if path == 'pulls/12': return self.pr
            if path == 'git/commits/' + self.base: return {'tree': {'sha': 'd'*40}}
            self.fail('Unexpected read: ' + path)
        self.api.get.side_effect = get
        self.api.pages.return_value = []
        self.api.tree.return_value = {}
        def request(path, data=None, method=None):
            if path == 'git/trees': return {'sha': 'e'*40}
            if path == 'git/commits': return {'sha': 'f'*40}
            if path == 'git/refs': return {}
            if path == 'pulls': return {'number': 12, 'html_url': 'https://github.com/example/registry/pull/12'}
            if path == 'pulls/12/merge':
                self.pr['merged'] = True
                return {'merged': True}
            if path.endswith('/dispatches'): return None
            self.fail('Unexpected write: ' + path)
        self.api.request.side_effect = request

    def test_binary_endpoints_use_their_required_accept_headers(self):
        session = Session('example/registry')
        with patch.object(session, 'call') as call:
            session.download('actions/artifacts/20/zip', self.root / 'artifact.zip')
            self.assertEqual(call.call_args.args[0], ['repos/example/registry/actions/artifacts/20/zip'])
            session.download('releases/assets/30', self.root / 'asset.zip')
            self.assertEqual(call.call_args.args[0][-2:], ['-H', 'Accept: application/octet-stream'])
            with self.assertRaises(RegistryError): session.download('https://attacker.invalid', self.root / 'bad')

    def test_submit_opens_one_pr_containing_only_candidate_materials(self):
        result = submit(self.api, 'test-candidate', self.file)
        self.assertEqual(result['pr'], 12)
        tree = next(c.args[1] for c in self.api.request.call_args_list if c.args[0] == 'git/trees')
        self.assertEqual([e['path'] for e in tree['tree']], ['candidates/test-candidate.json'])
        self.assertEqual(tree['tree'][0]['mode'], '100644')
        pr = self.api.request.call_args_list[-1].args[1]
        self.assertEqual(pr['base'], 'develop')
        self.assertTrue(pr['head'].startswith('candidate/test-candidate-'))

    def test_submit_rejects_existing_candidate_and_legacy_ids_before_writes(self):
        for path in ('candidates/test-candidate.json', 'submissions/test-problem/test-candidate.json'):
            self.api.tree.return_value = {path: {}}
            with self.assertRaisesRegex(RegistryError, 'already registered'):
                submit(self.api, 'test-candidate', self.file)
            self.api.request.assert_not_called()
        self.api.tree.return_value = {}
        preview = submit(self.api, 'test-candidate', self.file, dry_run=True)
        self.assertEqual(preview['base'], self.base)
        self.assertEqual(preview['branch'], 'develop')

    def test_invalid_publication_pr_and_wait_values_fail_before_api_access(self):
        for options in ({'pr': 0}, {'pr': -1}, {'wait_seconds': -1}, {'wait_seconds': 1801}):
            with self.assertRaises(RegistryError): publish(self.api, 'test-candidate', **options)
        self.api.get.assert_not_called()
        self.api.request.assert_not_called()

    def test_submit_preview_and_invalid_inputs_never_write(self):
        self.assertEqual(submit(self.api, 'test-candidate', self.file, dry_run=True)['status'], 'preview')
        self.api.request.assert_not_called()
        for key, value in [('public_source_authorized', False), ('bridge', '../Policy.lean')]:
            invalid = dict(self.value, **{key: value})
            self.file.write_text(json.dumps(invalid))
            with self.assertRaises(RegistryError): submit(self.api, 'test-candidate', self.file)
            self.api.request.assert_not_called()
        for identifier in ('../evil', 'evil\n', 'evil;command'):
            with self.assertRaises(RegistryError): submit(self.api, identifier, self.file)
        self.file.write_text('{"schema_version":1,"schema_version":1}')
        with self.assertRaises(RegistryError): submit(self.api, 'test-candidate', self.file)

    def test_source_and_bridge_paths_are_validated_without_execution(self):
        self.value['bridge'] = 'Bridge.lean'
        self.file.write_text(json.dumps(self.value))
        bridge = self.root / 'Bridge.lean'
        bridge.write_text('-- synthetic text only; never run')
        submit(self.api, 'test-candidate', self.file, bridge)
        tree = next(c.args[1] for c in self.api.request.call_args_list if c.args[0] == 'git/trees')
        self.assertEqual(len(tree['tree']), 2)
        self.api.request.reset_mock()
        bridge.unlink()
        bridge.symlink_to(self.file)
        with self.assertRaises(RegistryError): submit(self.api, 'test-candidate', self.file, bridge)
        self.api.request.assert_not_called()

    def test_open_change_rejects_moved_base_before_writing(self):
        with self.assertRaisesRegex(RegistryError, 'moved'):
            open_change(self.api, 'develop', '0'*40, {'README.md': 'x'}, prefix='publication/test', title='test', body='test')
        self.api.request.assert_not_called()

    def test_verify_dispatch_pins_pr_head_and_current_protected_base(self):
        value = verify(self.api, 12)
        self.assertEqual(value['status'], 'dispatched')
        data = self.api.request.call_args.args[1]
        self.assertEqual(data, {'ref': 'develop', 'inputs': {'pr': '12', 'expected_head': 'c'*40, 'expected_base': self.base}})
        self.pr['state'] = 'closed'
        self.api.request.reset_mock()
        with self.assertRaises(RegistryError): verify(self.api, 12)
        self.api.request.assert_not_called()

    def test_merge_uses_exact_head_and_never_admin_bypass(self):
        merge(self.api, 12)
        self.assertEqual(self.api.request.call_args.args[1], {'sha': 'c'*40, 'merge_method': 'squash'})
        self.assertEqual(self.api.request.call_args.kwargs['method'], 'PUT')
        self.api.request.reset_mock()
        merge(self.api, 12)
        self.api.request.assert_not_called()

    def test_publication_completion_merges_only_the_generated_head_after_checks(self):
        value = {'pr': 12, 'head_sha': 'c'*40, 'status': 'opened'}
        self.assertEqual(complete_publication(self.api, value, 1)['status'], 'synchronized')
        self.assertTrue(self.pr['merged'])
        self.pr.update(merged=False, head={'sha': 'd'*40})
        self.api.request.reset_mock()
        with self.assertRaisesRegex(RegistryError, 'head changed'):
            complete_publication(self.api, value, 1)
        self.api.request.assert_not_called()

    def test_publication_wait_never_bypasses_pending_checks(self):
        self.pr['mergeable_state'] = 'blocked'
        with patch('verifier.candidate.time.monotonic', side_effect=[0, 2]):
            value = complete_publication(self.api, {'pr': 12, 'head_sha': 'c'*40}, 1)
        self.assertEqual(value['status'], 'waiting_checks_or_review')
        self.api.request.assert_not_called()

    def test_closed_or_blocked_pr_cannot_merge(self):
        for state, mergeable in [('closed', 'clean'), ('open', 'blocked'), ('open', 'behind')]:
            self.pr.update(state=state, mergeable_state=mergeable)
            with self.assertRaises(RegistryError): merge(self.api, 12)
            self.api.request.assert_not_called()

    def test_publish_wont_merge_an_unrelated_pr(self):
        self.api.pages.return_value = [{'filename': 'README.md'}]
        with self.assertRaisesRegex(RegistryError, 'only this candidate'):
            publish(self.api, 'test-candidate', pr=12)
        self.api.request.assert_not_called()

    def test_publish_generates_registration_without_acceptance_or_record_changes(self):
        registry = {'candidates': {'test-candidate': candidate()}, 'submissions': {}}
        publications = {'schema_version': 1, 'publications': []}
        readme = 'Intro\n' + START + '\nold\n' + END + '\nUser notes\n'
        self.api.tree.return_value = {'docs/acceptance-publications.json': {}}
        self.api.blob.return_value = json.dumps(publications).encode()
        with patch('verifier.candidate.snapshot', return_value=(registry, publications, readme)), \
             patch('verifier.catalog.publication_history', return_value={}):
            value = publish(self.api, 'test-candidate')
        self.assertEqual(value['step'], 4)
        self.assertTrue(value['registered'])
        entries = next(c.args[1]['tree'] for c in self.api.request.call_args_list if c.args[0] == 'git/trees')
        self.assertEqual([e['path'] for e in entries], ['README.md'])
        self.assertIn('Live status and evidence', entries[0]['content'])
        self.assertIn('User notes', entries[0]['content'])
        self.assertNotIn('Accepted', entries[0]['content'])


class RegistrationTests(unittest.TestCase):
    def test_generated_table_is_deterministic_and_preserves_surrounding_text(self):
        registry = {'candidates': {'example': candidate()}, 'submissions': {}}
        table = render(registry, {'schema_version': 1, 'publications': []}, 'example/registry')
        readme = 'Custom intro\n' + START + '\nold table\n' + END + '\nCustom notes'
        changed = update(readme, table)
        self.assertEqual(update(changed, table), changed)
        self.assertTrue(changed.startswith('Custom intro\n'))
        self.assertTrue(changed.endswith('\nCustom notes'))
        self.assertIn('Live status and evidence', changed)
        self.assertNotIn('Verified —', changed)

    def test_markdown_and_html_in_candidate_titles_cannot_inject_links_or_rows(self):
        value = candidate()
        value['title'] = '[click](javascript:evil) | <img onerror=x>\n# Heading'
        table = render({'candidates': {'example': value}, 'submissions': {}},
                       {'schema_version': 1, 'publications': []}, 'example/registry')
        self.assertIn('\\[click\\]', table)
        self.assertNotIn('<img', table)
        self.assertEqual(len(table.splitlines()), 3)
        self.assertEqual(table.splitlines()[2].count('|'), 5)

    def test_missing_repeated_or_reversed_markers_fail_closed(self):
        for readme in ('No marker', START + START + END, END + START):
            with self.assertRaises(RegistryError): update(readme, 'table')

    def test_inline_problem_requires_exact_nonstale_protected_mapping(self):
        value = candidate()
        del value['problem_id']
        del value['statement_version']
        value['problem'] = {'title': 'Synthetic', 'source_url': 'https://example.org/problem', 'scope': 'Synthetic only'}
        registry = {'candidates': {'example': value}}
        with self.assertRaises(RegistryError): problem_identity(registry, 'example')
        mapping = {'schema_version': 1, 'candidate_digest': canonical_digest(value),
                   'problem_id': 'test-problem', 'statement_version': 'v1'}
        registry['intake_mappings'] = {'example': mapping}
        self.assertEqual(problem_identity(registry, 'example'), ('test-problem', 'v1'))
        value['title'] = 'Changed candidate'
        with self.assertRaisesRegex(RegistryError, 'Stale'): problem_identity(registry, 'example')

    def test_unverified_publication_references_cannot_render_accepted(self):
        entry = {'candidate_id': 'example', 'problem_id': 'test-problem', 'statement_version': 'v1',
                 'accepted_on': '2026-09-11', 'administrator': 'maintainer', 'source_commit': 'a'*40,
                 'verifier_sha': 'b'*40, 'release_id': 5, 'release_tag': 'acceptance-example',
                 'archive_commit': 'c'*40, 'record_sha256': 'd'*64}
        publications = {'schema_version': 1, 'publications': [entry]}
        registry = {'candidates': {'example': candidate()}, 'submissions': {}}
        with self.assertRaisesRegex(RegistryError, 'Verify immutable'):
            render(registry, publications, 'example/registry')
        with self.assertRaises(RegistryError):
            render(registry, publications, 'example/registry', verified={'example': dict(entry, record_sha256='0'*64)})
        self.assertIn('Administrator accepted', render(registry, publications, 'example/registry', verified={'example': entry}))
