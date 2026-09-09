"""Catalog provenance tests use API metadata fixtures, never proof acceptance mocks."""
import copy
import unittest
from unittest.mock import Mock

from verifier.catalog import build, render, PATH, EXECUTION_STEP
from verifier.registry import RegistryError


class CatalogTests(unittest.TestCase):
    def setUp(self):
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
        self.api.get.side_effect = lambda path: ({'commit': {'sha': self.base}} if path == 'branches/main'
                                                else {'id': 7, 'path': PATH})
        self.runs = [self.run]
        self.api.pages.side_effect = lambda path, *args, **kwargs: iter(self.runs if '/workflows/' in path else [self.job])

    def catalog(self):
        return build(self.api, self.registry, self.base)

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
                               ('repository', {'full_name': 'attacker/registry'})]:
            with self.subTest(field=field):
                self.run.update(original)
                self.run[field] = invalid
                self.assertEqual(self.catalog()['candidates'][0]['status'], 'not_run')

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
