"""Generic intake must preserve fixed source identities and non-passing states."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import yaml

from verifier.environment_matrix import matrix
from verifier.environments import load_environments
from verifier.merge_gate import candidate_sources
from verifier.onboarding import environment_draft
from verifier.registry import ROOT, RegistryError, canonical_digest
from verifier.results import write_result
from verifier.revalidate import plan, revision
from verifier.source_adaptation import adapt


class GenericIntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def source_fixture(self):
        original = {'Challenge.lean': b'def predicate : Prop := True\n',
                    'Submission.lean': b'import Challenge\ntheorem upstream : predicate := by trivial\n'}
        transforms = [{'path': path, 'destination': 'CandidateChallenge.lean' if path == 'Challenge.lean' else path,
                       'sha256': hashlib.sha256(data).hexdigest(), 'replacements': []}
                      for path, data in original.items()]
        transforms[1]['replacements'] = [{'old': 'import Challenge\n', 'new': 'import CandidateChallenge\n', 'count': 1}]
        submission = {'submission_id': 'test', 'repository': 'https://github.com/example/proof', 'commit': 'a'*40,
            'targets': [{'module': 'Submission'}],
            'execution': {'project_root': '.', 'include': ['*.lean'], 'proof_files': [], 'source_transforms': transforms}}
        problem = {'trusted_files': [{'path': 'Challenge.lean'}],
                   'workspace': {'submission_paths': ['CandidateChallenge.lean', 'Submission.lean']}}
        return original, submission, problem

    def fetch(self, original, submission, problem):
        dest = self.root / 'prepared'; dest.mkdir(exist_ok=True)
        evidence = []
        with patch('verifier.merge_gate.GitHub') as api:
            api.return_value.tree.return_value = {path: {'data': data} for path, data in original.items()}
            api.return_value.blob.side_effect = lambda entry: entry['data']
            hashes = candidate_sources(submission, dest, problem=problem,
                original_sources=self.root / 'original', adaptations=evidence)
        return dest, hashes, evidence

    def test_challenge_rename_preserves_original_and_binds_both_versions(self):
        original, submission, problem = self.source_fixture()
        dest, hashes, evidence = self.fetch(original, submission, problem)
        self.assertFalse((dest / 'Challenge.lean').exists())
        self.assertIn('CandidateChallenge.lean', hashes)
        self.assertEqual((self.root / 'original/Submission.lean').read_bytes(), original['Submission.lean'])
        self.assertTrue((dest / 'Submission.lean').read_text().startswith('import CandidateChallenge'))
        changed = next(item for item in evidence if item['path'] == 'Submission.lean')
        self.assertNotEqual(changed['original_sha256'], changed['adapted_sha256'])

    def test_stale_hash_missing_source_and_replacement_count_are_rejected(self):
        for kind in ('hash', 'count', 'missing'):
            original, submission, problem = self.source_fixture()
            transform = submission['execution']['source_transforms'][1]
            if kind == 'hash': transform['sha256'] = 'b'*64
            elif kind == 'count': transform['replacements'][0]['count'] = 2
            else: transform['path'] = 'Missing.lean'
            with self.subTest(kind=kind), self.assertRaises(RegistryError):
                self.fetch(original, submission, problem)

    def test_adaptation_cannot_escape_or_overwrite_trusted_files(self):
        for destination in ('../Escape.lean', 'lakefile.lean', 'Challenge.lean', 'Outside.lean', 'Submission.lean'):
            original, submission, problem = self.source_fixture()
            submission['execution']['source_transforms'][0]['destination'] = destination
            with self.subTest(destination=destination), self.assertRaises(RegistryError):
                self.fetch(original, submission, problem)

    def test_replacement_expansion_is_bounded(self):
        change = {'destination': 'Main.lean', 'sha256': hashlib.sha256(b'x').hexdigest(),
                  'replacements': [{'old': 'x', 'new': 'a'*100, 'count': 1}]}
        with self.assertRaisesRegex(RegistryError, 'exceeds limit'):
            adapt('Main.lean', b'x', change, max_bytes=10)

    def stdlib_project(self):
        project = self.root / 'project'; project.mkdir()
        (project / 'lean-toolchain').write_text('leanprover/lean4:v4.34.0-rc2\n')
        (project / 'lakefile.toml').write_text('name = "example"\n')
        (project / 'Solution.lean').write_text('theorem proof : True := by trivial\n')
        return project

    def test_environment_draft_is_pending_and_matrix_discovers_it(self):
        project = self.stdlib_project()
        with patch('subprocess.run', side_effect=AssertionError('No execution')):
            draft = environment_draft(project, self.root / 'environments/test-env', identifier='test-env',
                archive_sha256='b'*64, exporter_commit='c'*40, cache_modules=[])
        self.assertEqual(draft['status'], 'pending')
        self.assertIsNone(draft['evidence_url'])
        self.assertEqual(load_environments(self.root)['test-env'], draft)
        self.assertEqual(matrix(self.root), {'include': [{'environment': 'test-env'}]})
        self.assertNotIn('test-env', json.loads((ROOT/'policy/verification.json').read_text())['toolchains'])

    def test_dynamic_lake_is_not_copied_into_environment(self):
        project = self.stdlib_project()
        (project / 'lakefile.lean').write_text('unreviewed executable configuration')
        with self.assertRaisesRegex(RegistryError, 'warnings'):
            environment_draft(project, self.root/'env', identifier='test-env', archive_sha256='b'*64,
                              exporter_commit='c'*40, cache_modules=[])
        self.assertFalse((self.root / 'env').exists())

    def test_custom_static_lake_options_cannot_silently_match_stdlib(self):
        from verifier.environments import discover
        project = self.stdlib_project()
        (project / 'lakefile.toml').write_text('name = "example"\nmoreLeanArgs = ["--plugin=unreviewed.so"]\n')
        inspection = discover(project, ROOT)
        self.assertEqual(inspection['matches'], [])
        self.assertIn('custom_lake_configuration_requires_review', inspection['warnings'])

    def test_mathlib_draft_canonicalizes_lock_and_remains_unapproved(self):
        import shutil
        project = self.root / 'mathlib-project'
        shutil.copytree(ROOT/'environments/lean-4-28-mathlib', project)
        lock = json.loads((project/'lake-manifest.json').read_text())
        lock['packagesDir'] = '../../outside'
        (project/'lake-manifest.json').write_text(json.dumps(lock))
        output = self.root/'environments/new-mathlib'
        env = environment_draft(project, output, identifier='new-mathlib', archive_sha256='b'*64,
                                exporter_commit='c'*40, cache_modules=['Mathlib.Data.Nat.Basic'])
        created = json.loads((output/'lake-manifest.json').read_text())
        self.assertEqual(created['packagesDir'], '.lake/packages')
        self.assertTrue(all(d['rev'] == d['inputRev'] for d in created['packages']))
        self.assertEqual(load_environments(self.root)['new-mathlib'], env)

    def test_empty_environment_matrix_is_not_a_pass(self):
        with self.assertRaises(RegistryError): matrix(self.root)

    def test_revalidation_plans_unchanged_candidates_and_keeps_blockers(self):
        env = load_environments(ROOT)['lean-4-34-rc2-stdlib']
        problem = {'review': {'status': 'pending'}, 'workspace': {'solution_module': 'Bridge',
                    'environment_digest': canonical_digest(env)}}
        valid = {'problem_id': 'test', 'statement_version': 'v1', 'toolchain_id': env['environment_id'],
                 'adapter_id': None, 'execution': {}}
        registry = {'submissions': {'ready': valid, 'blocked': {**valid, 'toolchain_id': 'unknown'}},
                    'problems': {('test', 'v1'): problem}, 'environments': {env['environment_id']: env},
                    'policy': {'backend': 'comparator-export-v1', 'toolchains': [env['environment_id']]}}
        value = plan(registry)
        self.assertEqual(value['matrix']['include'], [{'submission': 'ready', 'environment': env['environment_id']}])
        self.assertEqual(value['blocked']['blocked']['status'], 'unsupported')
        self.assertEqual(plan(registry, 'ready')['blocked'], {})
        with self.assertRaises(RegistryError): plan(registry, 'unknown')

    def test_revalidation_refuses_non_main_and_wrong_revision(self):
        with patch('verifier.revalidate.subprocess.check_output', return_value='a'*40+'\n'):
            with self.assertRaises(RegistryError): revision('b'*40)
            with patch.dict(os.environ, {'GITHUB_ACTIONS': 'true', 'GITHUB_REF': 'refs/heads/feature', 'GITHUB_SHA': 'a'*40}):
                with self.assertRaisesRegex(RegistryError, 'protected main'): revision('a'*40)

    def test_summary_cannot_hide_skipped_or_blocked_candidates(self):
        workflow = yaml.load((ROOT/'.github/workflows/revalidate.yml').read_text(), Loader=yaml.BaseLoader)
        script = workflow['jobs']['summary']['steps'][0]['run']
        for work, unblocked, result, okay in [
            ('true','true','success',True), ('true','true','skipped',False),
            ('true','true','cancelled',False), ('true','false','success',False),
            ('false','false','skipped',False), ('false','true','skipped',True),
            ('','true','skipped',False),
        ]:
            env = {**os.environ, 'PLAN_RESULT':'success','HAS_WORK':work,'UNBLOCKED':unblocked,
                   'VERIFY_RESULT':result,'GITHUB_STEP_SUMMARY':str(self.root/'summary')}
            status = subprocess.run(['bash','-e','-c',script], env=env, capture_output=True).returncode
            with self.subTest(work=work, unblocked=unblocked, result=result):
                self.assertEqual(status == 0, okay)

    def test_result_cannot_turn_failed_machine_into_verified(self):
        proof = {'verification_status': 'verified', 'machine_status': 'failed', 'review_status': 'approved',
                 'targets': ['official'], 'candidate_targets': ['proof'], 'bindings': {
                     'pr_head': None,'base_sha':'a'*40,'upstream_commit':'b'*40,'workspace_digest':'c'*64,
                     'environment_digest':'d'*64,'policy_digest':'e'*64,'run_id':None,'run_attempt':None}}
        with self.assertRaisesRegex(RegistryError, 'machine success'):
            write_result(self.root/'result.json', 'example', proof)

    def test_administrator_result_discloses_authority_and_still_requires_machine_success(self):
        proof = {'verification_status': 'verified', 'machine_status': 'passed',
                 'review_status': 'approved', 'review_approval_kind': 'administrator_exception',
                 'review_administrator': 'test-admin', 'targets': ['official'],
                 'candidate_targets': ['proof'], 'bindings': {
                     'pr_head': None, 'base_sha': 'a'*40, 'upstream_commit': 'b'*40,
                     'workspace_digest': 'c'*64, 'environment_digest': 'd'*64,
                     'policy_digest': 'e'*64, 'run_id': None, 'run_attempt': None}}
        result = write_result(self.root/'admin-result.json', 'example', proof)
        self.assertEqual(result['review_approval_kind'], 'administrator_exception')
        self.assertEqual(result['review_administrator'], 'test-admin')
        self.assertEqual(result['formal_status'], 'pending')
        proof['machine_status'] = 'failed'
        with self.assertRaisesRegex(RegistryError, 'machine success'):
            write_result(self.root/'failed-admin.json', 'example', proof)
        proof['machine_status'] = 'passed'
        proof['review_administrator'] = None
        with self.assertRaisesRegex(RegistryError, 'identify its authority'):
            write_result(self.root/'anonymous-admin.json', 'example', proof)


if __name__ == '__main__':
    unittest.main()
