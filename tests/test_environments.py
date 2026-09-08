"""Trust boundaries for reusable environments, source overlays, and evidence."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from verifier.environments import discover, inspect_project, load_environments, matches, relative_path
from verifier.evidence import inspect_archive, seal
from verifier.merge_gate import candidate_sources, prerequisites
from verifier.registry import ROOT, RegistryError, canonical_digest, validate_registry


class EnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_environment_reuse_is_static_and_reports_pending_approval(self):
        with patch('subprocess.run', side_effect=AssertionError('Must not execute')), patch('socket.create_connection', side_effect=AssertionError('Must not fetch')):
            result = discover(ROOT / 'environments/lean-4-28-mathlib', ROOT)
        self.assertEqual(result['machine_status'], 'not_run')
        self.assertEqual(result['matches'][0]['environment_id'], 'lean-4-28-mathlib')
        self.assertEqual(result['matches'][0]['status'], 'pending')

    def test_dynamic_configuration_never_executes(self):
        (self.root / 'lakefile.lean').write_text('malicious executable Lake configuration')
        with patch('subprocess.run', side_effect=AssertionError('Must not execute')):
            result = inspect_project(self.root)
        self.assertIn('dynamic_lakefile_requires_review', result['warnings'])

    def test_matching_ignores_project_name_and_lock_formatting(self):
        source = ROOT / 'environments/lean-4-28-mathlib'
        for name in ('lean-toolchain', 'lakefile.toml', 'lake-manifest.json'):
            shutil.copyfile(source / name, self.root / name)
        lock = json.loads((self.root / 'lake-manifest.json').read_text())
        lock['name'] = 'a-different-project'
        lock['packages'].reverse()
        (self.root / 'lake-manifest.json').write_text(json.dumps(lock))
        self.assertEqual(discover(self.root, ROOT)['matches'][0]['environment_id'], 'lean-4-28-mathlib')

    def test_stdlib_project_does_not_need_a_dependency_lock(self):
        (self.root / 'lean-toolchain').write_text('leanprover/lean4:v4.34.0-rc2\n')
        (self.root / 'lakefile.toml').write_text('name = "different-project"\n')
        result = discover(self.root, ROOT)
        self.assertEqual(result['matches'][0]['environment_id'], 'lean-4-34-rc2-stdlib')

    def test_dependency_must_be_pinned_and_public(self):
        for field, value in [('rev', 'main'), ('type', 'path'), ('url', 'https://evil.test/proof')]:
            dep = {'name': 'dep', 'type': 'git', 'rev': 'a'*40, 'url': 'https://github.com/example/dep'}
            dep[field] = value
            (self.root / 'lake-manifest.json').write_text(json.dumps({'packages': [dep]}))
            with self.subTest(field=field), self.assertRaises(RegistryError): inspect_project(self.root)

    def test_environment_hashes_and_resource_bounds(self):
        shutil.copytree(ROOT / 'environments', self.root / 'environments')
        path = self.root / 'environments/lean-4-28-mathlib/lakefile.toml'
        path.write_text(path.read_text() + '\n# changed\n')
        with self.assertRaisesRegex(RegistryError, 'hash mismatch'): load_environments(self.root)
        envpath = self.root / 'environments/lean-4-34-rc2-stdlib/environment.json'
        env = json.loads(envpath.read_text()); env['resources']['memory_mb'] = 999999
        envpath.write_text(json.dumps(env))
        with self.assertRaises(RegistryError): load_environments(self.root)

    def test_safe_patterns_and_segment_matching(self):
        self.assertTrue(matches('Proofs/Nested/Main.lean', ['Proofs/**']))
        self.assertFalse(matches('Proofs/Nested/Main.lean', ['Proofs/*.lean']))
        self.assertFalse(matches('ProofsOther/Main.lean', ['Proofs/**']))
        for value in ('../Main.lean', '/tmp/Main.lean', 'x//Main.lean', '.lake/**', 'x/../../x', 'x\\y'):
            with self.subTest(value=value), self.assertRaises(RegistryError): relative_path(value, pattern=True)

    def source_fixture(self):
        submission = {'submission_id': 'example', 'repository': 'https://github.com/example/proof', 'commit': 'a'*40,
                      'execution': {'project_root': 'src/submission', 'include': ['Proofs/**'], 'proof_files': []}}
        problem = {'trusted_files': [{'path': 'Challenge.lean', 'sha256': 'b'*64}],
                   'workspace': {'submission_paths': ['Proofs/**', 'Bridge.lean']}}
        dest = self.root / 'source'; dest.mkdir()
        return submission, problem, dest

    def test_subdirectory_mapping_excludes_other_projects(self):
        submission, problem, dest = self.source_fixture()
        tree = {'src/submission/Proofs/Main.lean': {'data': b'proof'}, 'src/original/Old.lean': {'data': b'wrong'}}
        with patch('verifier.merge_gate.GitHub') as api:
            api.return_value.tree.return_value = tree
            api.return_value.blob.side_effect = lambda item: item['data']
            hashes = candidate_sources(submission, dest, problem=problem)
        self.assertEqual(list(hashes), ['Proofs/Main.lean'])
        self.assertEqual((dest / 'Proofs/Main.lean').read_bytes(), b'proof')

    def test_candidate_cannot_overwrite_trusted_files_or_escape_slots(self):
        for name in ('Challenge.lean', 'Outside.lean'):
            submission, problem, dest = self.source_fixture()
            submission['execution']['include'] = ['**']
            with patch('verifier.merge_gate.GitHub') as api:
                api.return_value.tree.return_value = {'src/submission/' + name: {}}
                api.return_value.blob.return_value = b'malicious'
                with self.assertRaises(RegistryError): candidate_sources(submission, dest, problem=problem)
            shutil.rmtree(dest)

    def test_hashed_bridge_overlay_and_collision_rejection(self):
        submission, problem, dest = self.source_fixture()
        bridge = self.root / 'proofs/example/Bridge.lean'; bridge.parent.mkdir(parents=True)
        bridge.write_bytes(b'bridge proof')
        submission['execution']['proof_files'] = [{'path': 'Bridge.lean', 'sha256': hashlib.sha256(bridge.read_bytes()).hexdigest()}]
        with patch('verifier.merge_gate.GitHub') as api:
            api.return_value.tree.return_value = {'src/submission/Proofs/Main.lean': {}}
            api.return_value.blob.return_value = b'proof'
            hashes = candidate_sources(submission, dest, problem=problem, registry_root=self.root)
            self.assertIn('Bridge.lean', hashes)
            bridge.write_bytes(b'tampered')
            with self.assertRaisesRegex(RegistryError, 'Stale proof overlay'):
                candidate_sources(submission, dest, problem=problem, registry_root=self.root)

    def test_pending_review_can_plan_diagnostics_but_environment_cannot_self_approve(self):
        env = load_environments(ROOT)['lean-4-34-rc2-stdlib']
        problem = {'review': {'status': 'pending'}, 'required_theorems': ['target'],
                   'workspace': {'environment_digest': canonical_digest(env), 'solution_module': 'Bridge'}}
        submission = {'problem_id': 'example', 'statement_version': 'v1', 'toolchain_id': env['environment_id'], 'adapter_id': None,
                      'execution': {}, 'targets': [{'module': 'Proofs.Main', 'declaration': 'different_name', 'official_theorem': 'target'}]}
        trusted = {'problems': {('example','v1'): problem}, 'environments': {env['environment_id']: env},
                   'policy': {'backend': 'comparator-export-v1', 'toolchains': [env['environment_id']]}}
        proposed = copy.deepcopy(trusted); proposed['submissions'] = {'example': submission}
        self.assertEqual(prerequisites(trusted, proposed, 'example')[2], 'Bridge')
        proposed['environments'][env['environment_id']]['resources']['cpus'] = 4
        with self.assertRaisesRegex(RegistryError, 'cannot change'): prerequisites(trusted, proposed, 'example')
        proposed = copy.deepcopy(trusted); proposed['submissions'] = {'example': submission}
        trusted['environments'][env['environment_id']]['status'] = 'pending'
        with self.assertRaisesRegex(RegistryError, 'unsupported'): prerequisites(trusted, proposed, 'example')

    def test_evidence_roundtrip_and_tampering(self):
        source = self.root / 'evidence'; source.mkdir()
        (source / 'result.json').write_text('{"machine_status":"failed"}')
        archive = seal(source, self.root / 'sealed')
        self.assertIn('result.json', inspect_archive(archive)['files'])
        metadata = json.loads((archive.parent / 'archive.json').read_text())
        self.assertEqual(metadata['formal_status'], 'pending')
        corrupt = self.root / 'corrupt.zip'
        with zipfile.ZipFile(archive) as old, zipfile.ZipFile(corrupt, 'w') as new:
            new.writestr('MANIFEST.json', old.read('MANIFEST.json'))
            new.writestr('result.json', '{"machine_status":"passed"}')
        with self.assertRaisesRegex(RegistryError, 'checksum'): inspect_archive(corrupt)
        with self.assertRaisesRegex(RegistryError, 'already exists'): seal(source, archive.parent)

    def test_archive_rejects_traversal_and_symlinks(self):
        archive = self.root / 'evil.zip'
        with zipfile.ZipFile(archive, 'w') as stream:
            stream.writestr('../escape', 'malicious')
            stream.writestr('MANIFEST.json', '{}')
        with self.assertRaises(RegistryError): inspect_archive(archive)
        source = self.root / 'evidence'; source.mkdir()
        (source / 'link').symlink_to('/etc/passwd')
        with self.assertRaises(RegistryError): seal(source, self.root / 'sealed')


if __name__ == '__main__':
    unittest.main()
