"""Environment selection must avoid unrelated work without hiding missing inputs."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from verifier.environment_matrix import changed_files, main, matrix, selection
from verifier.onboarding import environment_draft
from verifier.registry import RegistryError


class EnvironmentMatrixTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        project = self.root / 'project'
        project.mkdir()
        (project / 'lean-toolchain').write_text('leanprover/lean4:v4.34.0-rc2\n')
        (project / 'lakefile.toml').write_text('name = "synthetic"\n')
        for identifier in ('alpha', 'beta', 'all'):
            environment_draft(project, self.root / 'environments' / identifier,
                              identifier=identifier, archive_sha256='b'*64,
                              exporter_commit='c'*40, cache_modules=[])

    def ids(self, **kwargs):
        return [item['environment'] for item in matrix(self.root, **kwargs)['include']]

    def git(self, *args):
        return subprocess.check_output(['git', '-c', 'user.name=CI Test',
            '-c', 'user.email=ci@example.invalid', '-c', 'commit.gpgsign=false',
            *args], cwd=self.root, text=True).strip()

    def commit(self):
        self.git('add', '-A')
        self.git('commit', '-qm', 'Synthetic fixture')
        return self.git('rev-parse', 'HEAD')

    def test_manual_selection_is_exact_and_all_is_a_valid_environment_id(self):
        self.assertEqual(self.ids(), ['all', 'alpha', 'beta'])
        self.assertEqual(self.ids(environment='alpha'), ['alpha'])
        self.assertEqual(self.ids(environment='all'), ['all'])
        for name in ('missing', ' alpha ', '../alpha', 'alpha\nbeta'):
            with self.subTest(name=name), self.assertRaisesRegex(RegistryError, 'Unknown environment'):
                self.ids(environment=name)
        with self.assertRaisesRegex(RegistryError, 'cannot override'):
            self.ids(environment='alpha', changed_paths=['backend/export.py'])

    def test_environment_changes_select_only_affected_existing_profiles(self):
        self.assertEqual(self.ids(changed_paths=['environments/alpha/environment.json']), ['alpha'])
        self.assertEqual(self.ids(changed_paths=['environments/alpha/lean-toolchain',
            'environments/beta/lake-manifest.json', 'environments/alpha/environment.json', 'README.md']),
            ['alpha', 'beta'])

    def test_shared_changes_override_environment_only_selection(self):
        for path in ('backend/GateReplay.lean', 'backend/seccomp.json', 'verifier/environment_matrix.py',
                     'verifier/lean_backend.py', 'verifier/future_checker.py', 'schemas/environment.schema.json',
                     'policy/verification.json', 'scripts/backend_smoke.py', 'requirements-ci.lock',
                     '.github/workflows/backend-ci.yml', 'environments/shared.json'):
            with self.subTest(path=path):
                self.assertEqual(self.ids(changed_paths=['environments/alpha/environment.json', path]),
                                 ['all', 'alpha', 'beta'])

    def test_documentation_and_static_entrypoints_need_no_backend_execution(self):
        for path in ('README.md', 'docs/design.md', 'backend/README.md', 'environments/README.md',
                     'verifier/__main__.py', 'verifier/catalog.py', 'verifier/onboarding.py',
                     'verifier/resume.py', 'candidates/example.json'):
            with self.subTest(path=path):
                self.assertEqual(self.ids(changed_paths=[path]), [])
        self.assertEqual(self.ids(changed_paths=[]), [])

    def test_incomplete_and_invalid_unselected_profiles_fail_closed(self):
        (self.root / 'environments/incomplete').mkdir()
        for shared in ([], ['backend/export.py'], ['environments/shared.json']):
            with self.subTest(shared=shared), self.assertRaisesRegex(RegistryError, 'missing its descriptor'):
                self.ids(changed_paths=shared + ['environments/incomplete/lean-toolchain'])
        (self.root / 'environments/beta/lean-toolchain').write_text('tampered')
        with self.assertRaisesRegex(RegistryError, 'hash mismatch'):
            self.ids(environment='alpha')

    def test_real_git_rename_and_deletion_choose_new_id_and_skip_deleted_id(self):
        self.git('init', '-q')
        base = self.commit()
        before = self.root / 'environments/alpha'
        after = self.root / 'environments/renamed'
        before.rename(after)
        descriptor = after / 'environment.json'
        value = json.loads(descriptor.read_text())
        value['environment_id'] = 'renamed'
        descriptor.write_text(json.dumps(value))
        head = self.commit()
        paths = changed_files(self.root, base, head)
        self.assertIn('environments/alpha/lean-toolchain', paths)
        self.assertIn('environments/renamed/lean-toolchain', paths)
        self.assertEqual(self.ids(changed_paths=paths), ['renamed'])
        shutil.rmtree(after)
        deleted_head = self.commit()
        self.assertEqual(self.ids(changed_paths=changed_files(self.root, head, deleted_head)), [])

    def test_full_pr_diff_includes_earlier_commits_but_not_unrelated_base_changes(self):
        self.git('init', '-q')
        base = self.commit()
        self.git('checkout', '-qb', 'proposal')
        descriptor = self.root / 'environments/alpha/environment.json'
        data = json.loads(descriptor.read_text())
        data['description'] = 'Changed synthetic environment'
        descriptor.write_text(json.dumps(data))
        self.commit()
        (self.root / 'README.md').write_text('Later documentation change\n')
        head = self.commit()
        self.git('checkout', '--detach', base)
        (self.root / 'backend').mkdir()
        (self.root / 'backend/shared.py').write_text('# unrelated base change\n')
        advanced_base = self.commit()
        self.git('checkout', 'proposal')
        paths = changed_files(self.root, advanced_base, head)
        self.assertIn('environments/alpha/environment.json', paths)
        self.assertNotIn('backend/shared.py', paths)
        self.assertEqual(self.ids(changed_paths=paths), ['alpha'])

    def test_diff_failures_and_invalid_revisions_cannot_become_empty_success(self):
        for sha in ('main', '--help', 'a'*39, None):
            with self.subTest(sha=sha), self.assertRaisesRegex(RegistryError, 'fixed PR'):
                changed_files(self.root, sha, 'b'*40)
        with patch('verifier.environment_matrix.subprocess.check_output',
                   side_effect=subprocess.CalledProcessError(128, 'git')):
            with self.assertRaises(subprocess.CalledProcessError):
                changed_files(self.root, 'a'*40, 'b'*40)

    def test_event_routing_and_empty_outputs(self):
        event = {'pull_request': {'base': {'sha': 'a'*40}, 'head': {'sha': 'b'*40}},
                 'inputs': {'environment': 'beta'}}
        with patch('verifier.environment_matrix.changed_files', return_value=['environments/alpha/environment.json']):
            value, mode = selection(self.root, 'pull_request', event)
            self.assertEqual(value, {'include': [{'environment': 'alpha'}]})
            self.assertEqual(mode, 'pull_request')
            with self.assertRaisesRegex(RegistryError, 'automatic'):
                selection(self.root, 'pull_request', event, 'beta')
        self.assertEqual(selection(self.root, 'workflow_dispatch', event)[0],
                         {'include': [{'environment': 'beta'}]})
        self.assertEqual(len(selection(self.root, 'workflow_dispatch', {'inputs': {'environment': ''}})[0]['include']), 3)
        with self.assertRaisesRegex(RegistryError, 'Unsupported'):
            selection(self.root, 'pull_request_target', event)
        event_path, output, summary = [self.root / name for name in ('event.json', 'output', 'summary')]
        event_path.write_text(json.dumps(event))
        env = {'GITHUB_EVENT_NAME': 'pull_request', 'GITHUB_EVENT_PATH': str(event_path),
               'GITHUB_OUTPUT': str(output), 'GITHUB_STEP_SUMMARY': str(summary)}
        with patch.dict(os.environ, env, clear=True), patch('sys.argv', ['environment_matrix']), \
             patch('verifier.environment_matrix.ROOT', self.root), \
             patch('verifier.environment_matrix.changed_files', return_value=['README.md']):
            main()
        self.assertIn('has_work=false', output.read_text())
        self.assertIn('matrix={"include": []}', output.read_text())
        self.assertIn('no environment was verified', summary.read_text())


if __name__ == '__main__':
    unittest.main()
