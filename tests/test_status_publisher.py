"""Exercise the actual publisher against a fake GitHub API, never a real status."""
import io
import json
import os
import runpy
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from verifier.registry import ROOT


class PublisherTests(unittest.TestCase):
    def publish(self, plan, execution, *, plan_result='success', moved=False, closed=False, superseded=False, unrelated_pages=0, branch='main', retargeted=False, branch_moved=False, protected=True, cached_base=False, legacy_event=False):
        sent = []
        def response(request, timeout):
            if request.data:
                sent.append(json.loads(request.data))
                return io.BytesIO(b'{}')
            if '/branches/' in request.full_url:
                return io.BytesIO(json.dumps({'protected': protected, 'commit': {'sha': ('d' if branch_moved or moved else 'b')*40}}).encode())
            if '/statuses?' in request.full_url:
                page = int(request.full_url.rsplit('page=', 1)[1])
                if page <= unrelated_pages:
                    return io.BytesIO(json.dumps([{'context': 'unrelated'}] * 100).encode())
                return io.BytesIO(json.dumps([{'context': 'lean-verification', 'state': 'pending',
                    'target_url': 'https://github.com/example/registry/actions/runs/' + ('124' if superseded else '123')}]).encode())
            return io.BytesIO(json.dumps({'state': 'closed' if closed else 'open', 'head': {'sha': 'a'*40},
                'base': {'sha': ('c' if cached_base else 'b')*40, 'ref': 'other' if retargeted else branch, 'repo': {'full_name': 'example/registry'}}}).encode())
        env = {'GITHUB_REPOSITORY': 'example/registry', 'GH_TOKEN': 'test-token', 'GITHUB_RUN_ID': '123',
               'PR_HEAD': 'a'*40, 'EXPECTED_BASE_REF': branch, 'EXPECTED_BASE': 'b'*40, 'PR_NUMBER': '1',
               'EXECUTION_RESULT': execution, 'PLAN_RESULT': plan_result, 'PLAN_STATUS': plan}
        with tempfile.TemporaryDirectory() as folder:
            if legacy_event:
                event = Path(folder) / 'event.json'
                event.write_text(json.dumps({'pull_request': {'number': 1,
                    'head': {'sha': 'a'*40}, 'base': {'ref': branch,
                    'repo': {'full_name': 'example/registry'}}}}))
                env.pop('EXPECTED_BASE_REF')
                env.update(GITHUB_EVENT_NAME='pull_request_target', GITHUB_EVENT_PATH=str(event))
            with patch.dict(os.environ, env, clear=True), patch('sys.argv', ['gate_status.py', 'finish']), patch('urllib.request.urlopen', side_effect=response), patch('subprocess.check_output', return_value='b'*40):
                runpy.run_path(str(ROOT / 'scripts/gate_status.py'), run_name='__main__')
        self.assertEqual(len(sent), 0 if moved or closed or superseded or retargeted or branch_moved or not protected else 1)
        return sent[0] if sent else None

    def test_develop_publication_is_bound_to_protected_branch_identity(self):
        self.assertEqual(self.publish('ready', 'success', branch='develop', cached_base=True)['state'], 'success')
        for kwargs in ({'retargeted': True}, {'branch_moved': True}, {'protected': False}):
            with self.subTest(**kwargs):
                self.assertIsNone(self.publish('ready', 'success', branch='develop', **kwargs))

    def test_resolver_requires_current_protected_target_checkout(self):
        for branch, ref, sha, protected, accepted in (
                ('main', 'main', 'b', True, True),
                ('develop', 'develop', 'b', True, True),
                ('develop', 'main', 'b', True, False),
                ('develop', 'develop', 'c', True, False),
                ('develop', 'develop', 'b', False, False),
                ('untrusted', 'untrusted', 'b', True, False)):
            with self.subTest(branch=branch, ref=ref, sha=sha, protected=protected), tempfile.TemporaryDirectory() as folder:
                event, output = Path(folder)/'event.json', Path(folder)/'output'
                event.write_text(json.dumps({'inputs': {'pr': '1'}}))
                sent = []
                def response(request, timeout):
                    if request.data:
                        sent.append(json.loads(request.data))
                        value = {}
                    elif '/branches/' in request.full_url:
                        value = {'protected': protected, 'commit': {'sha': 'b'*40}}
                    else:
                        value = {'state': 'open', 'head': {'sha': 'a'*40},
                                 'base': {'sha': 'e'*40, 'ref': branch, 'repo': {'full_name': 'example/registry'}}}
                    return io.BytesIO(json.dumps(value).encode())
                env = {'GITHUB_REPOSITORY': 'example/registry', 'GH_TOKEN': 'test-token', 'GITHUB_RUN_ID': '123',
                       'GITHUB_EVENT_PATH': str(event), 'GITHUB_OUTPUT': str(output),
                       'GITHUB_REF': 'refs/heads/' + ref, 'GITHUB_SHA': sha*40,
                       'GITHUB_EVENT_NAME': 'workflow_dispatch'}
                with patch.dict(os.environ, env, clear=True), patch('sys.argv', ['gate_status.py', 'resolve']), patch('urllib.request.urlopen', side_effect=response), patch('subprocess.check_output', return_value=sha*40):
                    if accepted:
                        runpy.run_path(str(ROOT / 'scripts/gate_status.py'), run_name='__main__')
                        self.assertEqual(sent[0]['state'], 'pending')
                        self.assertIn('base_ref=' + branch, output.read_text())
                    else:
                        with self.assertRaises(AssertionError):
                            runpy.run_path(str(ROOT / 'scripts/gate_status.py'), run_name='__main__')
                        self.assertEqual(sent, [])

    def test_automatic_event_uses_protected_checkout_not_default_branch_sha(self):
        cases = [
            {}, {'branch': 'main'}, {'default': 'develop'},
            {'branch': 'main', 'default': 'develop'},
            {'checkout': 'a', 'accepted': False},  # Candidate code is forbidden.
            {'checkout': 'c', 'accepted': False},  # Stale base is forbidden.
            {'protected': False, 'accepted': False},
            {'branch': 'feature', 'accepted': False},
            {'event_branch': 'main', 'accepted': False},  # Retarget at same SHA.
            {'event_head': 'd', 'accepted': False},
            {'event_repository': 'attacker/fork', 'accepted': False},
            {'default': 'feature', 'accepted': False},
            {'context_ref': 'refs/pull/1/merge', 'accepted': False},
        ]
        for case in cases:
            with self.subTest(**case), tempfile.TemporaryDirectory() as folder:
                branch = case.get('branch', 'develop')
                default = case.get('default', 'main')
                event, output = Path(folder)/'event.json', Path(folder)/'output'
                event.write_text(json.dumps({'repository': {'default_branch': default,
                    'full_name': 'example/registry'}, 'pull_request': {
                    'number': case.get('event_number', 1),
                    'head': {'sha': case.get('event_head', 'a')*40},
                    'base': {'ref': case.get('event_branch', branch), 'sha': 'c'*40,
                             'repo': {'full_name': case.get('event_repository', 'example/registry')}}}}))
                sent = []
                def response(request, timeout):
                    if request.data:
                        sent.append(json.loads(request.data))
                        value = {}
                    elif '/branches/' in request.full_url:
                        value = {'protected': case.get('protected', True), 'commit': {'sha': 'b'*40}}
                    else:
                        value = {'state': 'open', 'head': {'sha': 'a'*40},
                                 'base': {'sha': 'c'*40, 'ref': branch,
                                          'repo': {'full_name': 'example/registry'}}}
                    return io.BytesIO(json.dumps(value).encode())
                env = {'GITHUB_REPOSITORY': 'example/registry', 'GH_TOKEN': 'test-token',
                       'GITHUB_RUN_ID': '123', 'GITHUB_EVENT_NAME': 'pull_request_target',
                       'GITHUB_EVENT_PATH': str(event), 'GITHUB_OUTPUT': str(output),
                       'GITHUB_REF': case.get('context_ref', 'refs/heads/' + default),
                       'GITHUB_SHA': 'f'*40}
                with patch.dict(os.environ, env, clear=True), patch('sys.argv', ['gate_status.py', 'resolve']), patch('urllib.request.urlopen', side_effect=response), patch('subprocess.check_output', return_value=case.get('checkout', 'b')*40):
                    if case.get('accepted', True):
                        runpy.run_path(str(ROOT / 'scripts/gate_status.py'), run_name='__main__')
                        self.assertEqual(sent[0]['state'], 'pending')
                        self.assertIn('base=' + 'b'*40, output.read_text())
                        self.assertIn('base_ref=' + branch, output.read_text())
                    else:
                        with self.assertRaises(AssertionError):
                            runpy.run_path(str(ROOT / 'scripts/gate_status.py'), run_name='__main__')
                        self.assertEqual(sent, [])
                        self.assertFalse(output.exists())

    def test_legacy_default_branch_publisher_binds_original_event_target(self):
        self.assertEqual(self.publish('ready', 'success', branch='develop',
                                      legacy_event=True)['state'], 'success')
        self.assertIsNone(self.publish('ready', 'success', branch='develop',
                                      legacy_event=True, retargeted=True))
        self.assertIsNone(self.publish('ready', 'success', branch='develop',
                                      legacy_event=True, branch_moved=True))

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
