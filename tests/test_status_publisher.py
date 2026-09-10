"""Exercise the actual publisher against a fake GitHub API, never a real status."""
import io
import json
import os
import runpy
import unittest
from unittest.mock import patch

from verifier.registry import ROOT


class PublisherTests(unittest.TestCase):
    def publish(self, plan, execution, *, plan_result='success', moved=False, closed=False, superseded=False, unrelated_pages=0):
        sent = []
        def response(request, timeout):
            if request.data:
                sent.append(json.loads(request.data))
                return io.BytesIO(b'{}')
            if '/statuses?' in request.full_url:
                page = int(request.full_url.rsplit('page=', 1)[1])
                if page <= unrelated_pages:
                    return io.BytesIO(json.dumps([{'context': 'unrelated'}] * 100).encode())
                return io.BytesIO(json.dumps([{'context': 'lean-verification', 'state': 'pending',
                    'target_url': 'https://github.com/example/registry/actions/runs/' + ('124' if superseded else '123')}]).encode())
            return io.BytesIO(json.dumps({'state': 'closed' if closed else 'open', 'head': {'sha': 'a'*40},
                'base': {'sha': ('c' if moved else 'b')*40}}).encode())
        env = {'GITHUB_REPOSITORY': 'example/registry', 'GH_TOKEN': 'test-token', 'GITHUB_RUN_ID': '123',
               'PR_HEAD': 'a'*40, 'EXPECTED_BASE': 'b'*40, 'PR_NUMBER': '1',
               'EXECUTION_RESULT': execution, 'PLAN_RESULT': plan_result, 'PLAN_STATUS': plan}
        with patch.dict(os.environ, env, clear=True), patch('sys.argv', ['gate_status.py', 'finish']), patch('urllib.request.urlopen', side_effect=response):
            runpy.run_path(str(ROOT / 'scripts/gate_status.py'), run_name='__main__')
        self.assertEqual(len(sent), 0 if moved or closed or superseded else 1)
        return sent[0] if sent else None

    def test_status_ownership_is_found_beyond_first_page(self):
        self.assertEqual(self.publish('ready', 'success', unrelated_pages=1)['state'], 'success')

    def test_all_matrix_jobs_required(self):
        self.assertEqual(self.publish('ready', 'success')['state'], 'success')
        for state in ('failure', 'cancelled', 'skipped', '', 'unknown'):
            with self.subTest(state=state):
                self.assertEqual(self.publish('ready', state)['state'], 'failure')

    def test_no_candidate_is_not_a_proof_verdict(self):
        verdict = self.publish('not_applicable', 'skipped')
        self.assertEqual(verdict['state'], 'success')
        self.assertIn('No candidate proof changes', verdict['description'])
        self.assertEqual(self.publish('not_applicable', 'success')['state'], 'failure')

    def test_failed_plan_and_stale_base_cannot_publish_success(self):
        self.assertEqual(self.publish('ready', 'success', plan_result='failure')['state'], 'failure')
        self.assertIsNone(self.publish('ready', 'success', moved=True))
        self.assertIsNone(self.publish('ready', 'success', closed=True))
        self.assertIsNone(self.publish('ready', 'failure', superseded=True))
        self.assertEqual(self.publish('unknown', 'success')['state'], 'failure')


if __name__ == '__main__':
    unittest.main()
