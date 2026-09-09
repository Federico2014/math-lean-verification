"""Failure classification and evidence retention without simulating a proof pass."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from verifier.lean_backend import verify
from verifier.registry import VerificationError


class BackendFailureTests(unittest.TestCase):
    def exercise(self, *, error=None, exit_code=None):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch('verifier.lean_backend.sandbox') as execute:
                if error is not None:
                    execute.side_effect = error
                else:
                    execute.return_value = (exit_code, b'', b'untrusted diagnostic')
                result = verify('sha256:' + 'a'*64, root/'challenge', root/'solution',
                                'Solution', ['target'], root/'evidence')
            self.assertEqual(result['machine_status'], 'failed')
            self.assertEqual(result['stages'], [])
            log = json.loads((root/'evidence/execution-0.json').read_text())
            self.assertEqual(log['exit_code'], exit_code)
            self.assertGreaterEqual(log['duration_seconds'], 0)
            self.assertEqual(json.loads((root/'evidence/result.json').read_text()), result)
            return result

    def test_runtime_errors_keep_failed_stage_evidence(self):
        for error in [VerificationError('Sandbox execution timed out', 'infrastructure_error'),
                      FileNotFoundError('Docker unavailable'),
                      subprocess.TimeoutExpired('docker', 60)]:
            with self.subTest(error=error):
                self.assertEqual(self.exercise(error=error)['failure_status'], 'infrastructure_error')

    def test_docker_failures_are_separate_from_rejected_proofs(self):
        for code in [125, 126, 127, 137, -9]:
            with self.subTest(code=code):
                self.assertEqual(self.exercise(exit_code=code)['failure_status'], 'infrastructure_error')
        self.assertEqual(self.exercise(exit_code=1)['failure_status'], 'failed')


if __name__ == '__main__':
    unittest.main()
