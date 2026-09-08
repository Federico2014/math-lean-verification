"""End-to-end controller tests with stubbed network and proof engine.

These test orchestration and review binding, not Lean proof correctness.
"""
import json
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from verifier.merge_gate import run
from verifier.registry import ROOT, canonical_digest, statement_digest
from verifier.environments import load_environments


class WorkspaceGateTests(unittest.TestCase):
    def exercise(self, review):
        from test_registry import RegistryTests
        fixture = RegistryTests(); fixture.setUp()
        self.addCleanup(fixture.temp.cleanup)
        root = fixture.root
        shutil.copytree(ROOT / 'environments', root / 'environments')
        env = load_environments(root)['lean-4-34-rc2-stdlib']
        fixture.problem['toolchain_id'] = env['environment_id']
        fixture.problem['workspace'] = {'environment_digest': canonical_digest(env),
            'solution_module': 'Proofs.Main', 'submission_paths': ['Proofs/**']}
        fixture.submission['toolchain_id'] = env['environment_id']
        fixture.submission['execution'] = {'project_root': '.', 'include': ['Proofs/**'], 'proof_files': []}
        fixture.submission['targets'] = [{'module': 'Proofs.Main', 'declaration': 'target', 'official_theorem': 'target'}]
        if review == 'approved':
            fixture.policy['approved_reviewers'] = ['reviewer-one', 'reviewer-two']
            fixture.problem['original_sources'][0]['snapshot_sha256'] = 'b'*64
            fixture.problem['review'] = {'status': 'approved', 'statement_digest': statement_digest(fixture.problem),
                'reviewers': ['reviewer-one','reviewer-two'], 'evidence_url': 'https://example.org/review'}
        fixture.write('policy/verification.json', fixture.policy)
        fixture.save()
        # The trusted base contains the workspace, but no candidate registration.
        source_file = root / 'submissions/test-problem/test-submission.json'
        candidate = source_file.read_bytes(); source_file.unlink()
        tree = {p.relative_to(root).as_posix(): {'size': p.stat().st_size, 'data': p.read_bytes()}
                for p in root.rglob('*') if p.is_file()}
        tree['submissions/test-problem/test-submission.json'] = {'size': len(candidate), 'data': candidate}
        def proof_engine(image, challenge, solution, module, targets, evidence, **kwargs):
            evidence.mkdir(parents=True)
            self.assertEqual(module, 'Proofs.Main')
            self.assertEqual(targets, ['target'])
            self.assertEqual((solution/'Proofs/Main.lean').read_text(), 'theorem target : True := by trivial\n')
            return {'machine_status': 'passed', 'stages': ['unit_test_stub_only']}
        with patch('verifier.merge_gate.ROOT', root), patch('verifier.merge_gate.subprocess.check_output', return_value='d'*40), \
             patch('verifier.merge_gate.GitHub') as api, patch('verifier.merge_gate.verify', side_effect=proof_engine):
            api.return_value.get.return_value = {'state': 'open', 'head': {'sha': 'c'*40},
                'base': {'sha': 'd'*40, 'ref': 'main', 'repo': {'full_name': 'example/registry'}}}
            api.return_value.tree.side_effect = lambda sha: tree if sha == 'c'*40 else {'Proofs/Main.lean': {'data': b'theorem target : True := by trivial\n'}}
            api.return_value.blob.side_effect = lambda item: item['data']
            plan = run('example/registry', 1, 'c'*40, None, root/'plan', check_only=True)
            self.assertEqual(plan['matrix']['include'], [{'submission': 'test-submission', 'environment': env['environment_id']}])
            self.assertEqual(plan['status'], 'ready')
            return run('example/registry', 1, 'c'*40, 'sha256:'+'e'*64, root/'evidence')

    def test_successful_machine_diagnostics_cannot_bypass_pending_review(self):
        result = self.exercise('pending')
        proof = result['submissions']['test-submission']
        self.assertEqual(proof['machine_status'], 'passed')
        self.assertEqual(proof['verification_status'], 'review_pending')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(proof['formal_status'], 'pending')

    def test_approved_review_and_execution_bind_all_inputs(self):
        result = self.exercise('approved')
        proof = result['submissions']['test-submission']
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(proof['verification_status'], 'verified')
        self.assertEqual(proof['bindings']['pr_head'], 'c'*40)
        self.assertEqual(proof['bindings']['base_sha'], 'd'*40)
        self.assertEqual(proof['bindings']['upstream_commit'], 'a'*40)
        self.assertIn('Proofs/Main.lean', proof['source_hashes'])
        self.assertEqual(proof['formal_status'], 'pending')


if __name__ == '__main__':
    unittest.main()
