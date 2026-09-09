"""Cache-check orchestration only; real Lake compatibility is tested in CI."""
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from backend.cache_guard import check_cached_modules


class CacheGuardTests(unittest.TestCase):
    def test_declared_scope_uses_no_rebuild_and_process_group_deadline(self):
        with patch('backend.cache_guard.subprocess.run') as run:
            check_cached_modules(Path('/project'), ['Mathlib', 'Mathlib.Data.Nat.Basic'])
        command = run.call_args.args[0]
        self.assertEqual(command[:4], ['timeout', '--kill-after=10s', '300s', 'lake'])
        self.assertEqual(command[4:], ['--no-build', 'build', '+Mathlib', '+Mathlib.Data.Nat.Basic'])
        self.assertEqual(run.call_args.kwargs, {'cwd': Path('/project'), 'check': True})

    def test_missing_or_stale_cache_fails_without_rebuild_fallback(self):
        with patch('backend.cache_guard.subprocess.run',
                   side_effect=subprocess.CalledProcessError(1, ['lake'])) as run:
            with self.assertRaisesRegex(RuntimeError, 'source rebuild is disabled'):
                check_cached_modules(Path('/project'), ['Mathlib'])
        self.assertEqual(run.call_count, 1)

    def test_deadline_and_forced_kill_have_explicit_budget_failure(self):
        for code in (124, 137):
            with self.subTest(code=code), patch('backend.cache_guard.subprocess.run',
                    side_effect=subprocess.CalledProcessError(code, ['timeout'])) as run:
                with self.assertRaisesRegex(RuntimeError, '300-second budget'):
                    check_cached_modules(Path('/project'), ['Mathlib'])
                self.assertEqual(run.call_count, 1)

    def test_empty_scope_still_checks_full_mathlib_without_rebuild(self):
        with patch('backend.cache_guard.subprocess.run') as run:
            check_cached_modules(Path('/project'), [])
        self.assertEqual(run.call_args.args[0][-3:], ['--no-build', 'build', '+Mathlib'])
