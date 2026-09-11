"""Catalog provenance tests use API metadata fixtures, never proof acceptance mocks."""
import copy
import io
import os
import unittest
from unittest.mock import Mock, patch

from verifier.catalog import build, render, PATH, EXECUTION_STEP
from verifier.registry import RegistryError
from verifier.merge_gate import GitHub


class CatalogTests(unittest.TestCase):
    def setUp(self):
        # API fixtures model their own branch; the CI runner's PR ref is unrelated.
        environment = patch.dict(os.environ, {'GITHUB_ACTIONS': 'false'})
        environment.start()
        self.addCleanup(environment.stop)
        self.base = 'b'*40
        self.run = {'id': 12, 'run_number': 2, 'run_attempt': 1, 'workflow_id': 7,
            'path': PATH, 'event': 'push', 'head_branch': 'main', 'head_sha': self.base,
            'repository': {'full_name': 'example/registry'}, 'head_repository': {'full_name': 'example/registry'},
            'display_title': f'Revalidate {self.base} all', 'status': 'completed'}
        self.job = {'run_id': 12, 'run_attempt': 1, 'head_sha': self.base,
            'name': 'Verify candidate example', 'status': 'completed', 'conclusion': 'success',
            'steps': [{'name': EXECUTION_STEP, 'status': 'completed', 'conclusion': 'success'}]}
        self.registry = {'submissions': {}, 'candidates': {'example': {
            'title': '<img src=x onerror=alert(1)>',
            'source': {'repository': 'https://github.com/example/proof', 'commit': 'a'*40}}}}
        self.api = Mock(repository='example/registry')
        self.branch = 'main'
        self.protected = True
        self.api.get.side_effect = self.get
        self.runs = [self.run]
        self.api.pages.side_effect = lambda path, *args, **kwargs: iter(self.runs if '/workflows/' in path else [self.job])

    def get(self, path):
        if path == '':
            return {'default_branch': self.branch}
        if path == 'branches/' + self.branch:
            return {'protected': self.protected, 'commit': {'sha': self.base}}
        return {'id': 7, 'path': PATH}

    def catalog(self):
        return build(self.api, self.registry, self.base)

    def test_repository_metadata_request_has_no_trailing_slash(self):
        with patch('verifier.merge_gate.urllib.request.urlopen', return_value=io.BytesIO(b'{}')) as request:
            GitHub('example/registry').get('')
        self.assertEqual(request.call_args.args[0].full_url, 'https://api.github.com/repos/example/registry')

    def test_develop_default_lists_candidates_and_uses_only_develop_evidence(self):
        self.branch = 'develop'
        self.assertEqual(self.catalog()['candidates'][0]['status'], 'not_run')
        self.run['head_branch'] = 'develop'
        value = self.catalog()
        self.assertEqual(value['branch'], 'develop')
        self.assertEqual(value['candidates'][0]['status'], 'verified')
        self.assertIn('Protected develop:', render(value))
        self.assertIn('branch%3Adevelop', value['candidates'][0]['history_url'])

    def test_unprotected_or_unsupported_default_branch_is_rejected(self):
        self.protected = False
        with self.assertRaisesRegex(RegistryError, 'must be protected'):
            self.catalog()
        self.branch = 'feature'
        with self.assertRaisesRegex(RegistryError, 'Unsupported default branch'):
            self.catalog()

    def test_default_branch_switch_during_publication_is_rejected_even_at_same_sha(self):
        reads = 0
        def get(path):
            nonlocal reads
            if path == '':
                reads += 1
                return {'default_branch': 'main' if reads == 1 else 'develop'}
            if path.startswith('branches/'):
                return {'protected': True, 'commit': {'sha': self.base}}
            return self.get(path)
        self.api.get.side_effect = get
        with self.assertRaisesRegex(RegistryError, 'Default branch changed'):
            self.catalog()

    def acceptance(self):
        entry = {'candidate_id': 'example', 'problem_id': 'example-problem', 'statement_version': 'v1',
                 'accepted_on': '2026-09-11', 'administrator': 'maintainer', 'source_commit': 'a'*40,
                 'verifier_sha': 'd'*40, 'release_id': 5, 'release_tag': 'acceptance-example-v1',
                 'archive_commit': 'e'*40, 'record_sha256': 'f'*64}
        self.registry['candidates']['example'].update(problem_id='example-problem', statement_version='v1')
        release = {'draft': False, 'immutable': True, 'published_at': '2026-09-11T00:00:00Z',
                   'tag_name': entry['release_tag'], 'target_commitish': entry['archive_commit'],
                   'author': {'login': 'maintainer'}, 'assets': [{'name': 'acceptance.json',
                   'state': 'uploaded', 'digest': 'sha256:' + entry['record_sha256']}]}
        tag = {'object': {'sha': entry['archive_commit'], 'type': 'commit',
                         'url': 'https://api.github.com/repos/example/registry/git/commits/' + entry['archive_commit']}}
        self.api.get.side_effect = lambda path: release if path == 'releases/5' else tag if path.startswith('git/ref/tags/') else self.get(path)
        return {'schema_version': 1, 'publications': [entry]}, release, tag

    def test_historical_acceptance_does_not_grant_a_current_machine_pass(self):
        publications, _, _ = self.acceptance()
        self.job['conclusion'] = 'failure'
        self.registry['candidates']['example']['source']['commit'] = 'c'*40
        value = build(self.api, self.registry, self.base, publications)
        row = value['candidates'][0]
        self.assertEqual(row['status'], 'failed')
        self.assertEqual(row['formal_status'], 'accepted_historical')
        self.assertEqual(row['acceptance_history']['source_commit'], 'a'*40)
        self.assertIn('Historical acceptance: source', render(value))
        self.assertIn('Accepted by administrator maintainer', render(value))

    def test_mutable_draft_substituted_or_reattributed_release_is_rejected(self):
        for field, invalid in [('draft', True), ('immutable', False), ('published_at', None),
                               ('target_commitish', '0'*40), ('author', {'login': 'attacker'}),
                               ('tag_name', 'another-tag'), ('assets', [])]:
            with self.subTest(field=field):
                publications, release, _ = self.acceptance()
                release[field] = invalid
                with self.assertRaises(RegistryError):
                    build(self.api, self.registry, self.base, publications)
        publications, release, tag = self.acceptance()
        release['assets'][0]['digest'] = 'sha256:' + '0'*64
        with self.assertRaisesRegex(RegistryError, 'checksum mismatch'):
            build(self.api, self.registry, self.base, publications)
        publications, _, tag = self.acceptance()
        tag['object']['sha'] = '0'*40
        with self.assertRaisesRegex(RegistryError, 'tag mismatch'):
            build(self.api, self.registry, self.base, publications)

    def test_exact_success_is_published_with_escaped_text_and_formal_pending(self):
        value = self.catalog()
        row = value['candidates'][0]
        self.assertEqual(row['status'], 'verified')
        self.assertEqual(row['formal_status'], 'pending')
        self.assertTrue(row['evidence_url'].endswith('/12/attempts/1'))
        page = render(value)
        self.assertNotIn('<img src=', page)
        self.assertIn('&lt;img', page)

    def test_foreign_pr_workflow_base_and_repository_cannot_grant_a_pass(self):
        original = copy.deepcopy(self.run)
        for field, invalid in [('path', '.github/workflows/ci.yml'), ('event', 'pull_request'),
                               ('head_branch', 'feature'), ('head_sha', 'c'*40), ('workflow_id', 8),
                               ('head_repository', {'full_name': 'attacker/registry'}),
                               ('head_repository', None), ('repository', None),
                               ('repository', {'full_name': 'attacker/registry'})]:
            with self.subTest(field=field):
                self.run.update(original)
                self.run[field] = invalid
                self.assertEqual(self.catalog()['candidates'][0]['status'], 'not_run')

    def test_candidate_named_all_is_distinct_from_an_all_candidate_run(self):
        self.registry['candidates']['all'] = copy.deepcopy(self.registry['candidates']['example'])
        self.job['name'] = 'Verify candidate all'
        self.run['display_title'] = f'Revalidate {self.base} selected-all'
        rows = {r['id']: r for r in self.catalog()['candidates']}
        self.assertEqual(rows['all']['status'], 'verified')
        self.assertEqual(rows['example']['status'], 'not_run')
        self.assertIsNone(rows['example']['evidence_url'])
        self.run['display_title'] = f'Revalidate {self.base} all'
        rows = {r['id']: r for r in self.catalog()['candidates']}
        self.assertIsNotNone(rows['example']['evidence_url'])

    def test_retry_failure_and_running_never_fall_back_to_older_green(self):
        old = copy.deepcopy(self.run)
        old['id'] = 11
        old['run_number'] = 1
        self.runs.append(old)
        self.job['conclusion'] = 'failure'
        self.assertEqual(self.catalog()['candidates'][0]['status'], 'failed')
        self.job['status'] = 'queued'
        self.assertEqual(self.catalog()['candidates'][0]['status'], 'queued')

    def test_attempt_mismatch_or_missing_execution_step_rejects_publication(self):
        self.job['run_attempt'] = 2
        with self.assertRaises(RegistryError):
            self.catalog()
        self.job['run_attempt'] = 1
        self.job['steps'] = []
        with self.assertRaises(RegistryError):
            self.catalog()

    def test_candidate_failure_is_independent_and_api_failure_not_not_run(self):
        self.api.pages.side_effect = OSError('unavailable')
        with self.assertRaises(OSError):
            self.catalog()

    def test_new_attempt_during_generation_invalidates_the_snapshot(self):
        reads = 0
        def pages(path, *args, **kwargs):
            nonlocal reads
            if '/workflows/' in path:
                reads += 1
                newer = dict(self.run, run_attempt=2, status='queued')
                return iter([self.run] if reads == 1 else [newer])
            return iter([self.job])
        self.api.pages.side_effect = pages
        with self.assertRaisesRegex(RegistryError, 'attempts changed'):
            self.catalog()

    def test_job_changes_within_running_attempt_invalidate_publication(self):
        self.run['status'] = 'in_progress'
        for change in ('completed', 'conclusion', 'step', 'missing', 'identity'):
            reads = 0
            initial = copy.deepcopy(self.job)
            if change == 'completed':
                initial['status'] = 'queued'
                initial['conclusion'] = None
            def pages(path, *args, **kwargs):
                nonlocal reads
                if '/workflows/' in path:
                    return iter(self.runs)
                reads += 1
                job = copy.deepcopy(initial)
                if reads > 1:
                    if change == 'completed':
                        job = copy.deepcopy(self.job)
                    elif change == 'conclusion':
                        job['conclusion'] = 'failure'
                    elif change == 'step':
                        job['steps'][0]['conclusion'] = 'failure'
                    elif change == 'missing':
                        return iter([])
                    else:
                        job['head_sha'] = 'c'*40
                return iter([job])
            self.api.pages.side_effect = pages
            with self.subTest(change=change), self.assertRaisesRegex(RegistryError, 'jobs changed|identity mismatch'):
                self.catalog()

    def test_in_workflow_publication_reports_completed_blocked_plan_as_not_run(self):
        self.run['status'] = 'in_progress'
        self.job['name'] = 'summary'
        self.job['conclusion'] = 'failure'
        value = self.catalog()
        self.assertEqual(value['candidates'][0]['status'], 'not_run')
        self.assertEqual(value['candidates'][0]['workflow']['current_step'], 2)

    def test_running_plan_does_not_claim_prerequisites_are_complete(self):
        self.run['status'] = 'in_progress'
        self.job.update(name='plan', status='in_progress', conclusion=None)
        row = self.catalog()['candidates'][0]
        self.assertEqual(row['status'], 'running')
        self.assertEqual(row['workflow']['current_step'], 2)

    def test_summary_job_transition_invalidates_in_workflow_publication(self):
        self.run['status'] = 'in_progress'
        reads = 0
        def pages(path, *args, **kwargs):
            nonlocal reads
            if '/workflows/' in path:
                return iter(self.runs)
            reads += 1
            return iter([dict(self.job, name='summary', status='queued' if reads == 1 else 'completed')])
        self.api.pages.side_effect = pages
        with self.assertRaisesRegex(RegistryError, 'jobs changed'):
            self.catalog()
