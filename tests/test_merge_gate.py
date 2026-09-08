"""Reject attempts to bypass the trusted statement and fixed-source gate."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from verifier.merge_gate import prerequisites, select_submissions, GitHub
from verifier.lean_backend import copy_sources, sandbox
from verifier.registry import RegistryError


class MergeGateTests(unittest.TestCase):
    def fixture(self):
        problem = {'review': {'status': 'approved'}, 'required_theorems': ['target']}
        submission = {'problem_id': 'example', 'statement_version': 'v1',
            'toolchain_id': 'lean-4-34-rc2-stdlib', 'adapter_id': None,
            'targets': [{'module': 'Solution', 'declaration': 'target', 'official_theorem': 'target'}]}
        trusted = {'problems': {('example','v1'): problem}, 'submissions': {},
            'policy': {'backend': 'comparator-export-v1', 'toolchains': ['lean-4-34-rc2-stdlib']}}
        proposed = copy.deepcopy(trusted)
        proposed['submissions']['example'] = submission
        return trusted, proposed

    def test_candidate_cannot_supply_its_own_trusted_statement(self):
        trusted, proposed = self.fixture()
        trusted['problems'] = {}
        with self.assertRaisesRegex(RegistryError, 'merged before'):
            prerequisites(trusted, proposed, 'example')

    def test_candidate_cannot_change_approved_statement(self):
        trusted, proposed = self.fixture()
        proposed['problems'][('example','v1')]['required_theorems'] = ['True']
        with self.assertRaisesRegex(RegistryError, 'cannot change'):
            prerequisites(trusted, proposed, 'example')

    def test_pending_review_and_unknown_toolchain_block(self):
        for kind in ['review','toolchain','adapter','target']:
            trusted, proposed = self.fixture()
            if kind == 'review':
                for r in [trusted,proposed]: r['problems'][('example','v1')]['review']['status'] = 'pending'
            elif kind == 'toolchain': trusted['policy']['toolchains'] = []
            elif kind == 'adapter': proposed['submissions']['example']['adapter_id'] = 'unreviewed'
            else: proposed['submissions']['example']['targets'][0]['declaration'] = 'easier'
            with self.subTest(kind=kind), self.assertRaises(RegistryError):
                prerequisites(trusted, proposed, 'example')

    def test_no_affected_candidate_is_distinct_from_proof_pass(self):
        trusted, proposed = self.fixture()
        self.assertEqual(select_submissions(trusted, proposed), ['example'])
        self.assertEqual(select_submissions(proposed, proposed), [])
        with self.assertRaises(RegistryError): select_submissions(proposed, trusted)

    def test_source_rejects_precompiled_files_and_symlinks(self):
        for kind in ['binary','symlink']:
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp); src = root/'src'; src.mkdir()
                if kind == 'binary': (src/'Solution.olean').write_bytes(b'untrusted')
                else: (src/'Solution.lean').symlink_to('/etc/passwd')
                with self.assertRaises(RegistryError): copy_sources(src, root/'out')

    def test_only_immutable_local_image_ids_are_executable(self):
        with patch('subprocess.Popen') as execute, self.assertRaises(RegistryError):
            sandbox('attacker/image:latest', Path('/tmp'), ['true'])
        execute.assert_not_called()

    def test_source_url_cannot_escape_github(self):
        for value in ['https://evil.test/x','owner/repo/../../x','owner/repo?x=1']:
            with self.subTest(value=value), self.assertRaises(RegistryError): GitHub(value)
