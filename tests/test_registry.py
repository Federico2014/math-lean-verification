"""Synthetic temporary registries only; no real award candidates or Lean runs."""

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch

from verifier.__main__ import main
from verifier.registry import (
    ROOT, RegistryError, file_digest, plan_verification, read_json,
    schema_validate, statement_digest, validate_registry,
)


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        for folder in ("problems", "submissions", "records", "policy"):
            (self.root / folder).mkdir()
        self.policy = read_json(ROOT / "policy/verification.json")
        self.write("policy/verification.json", self.policy)
        self.base = self.root / "problems/test-problem/v1"
        self.base.mkdir(parents=True)
        for name, text in {
            "statement.md": "Synthetic original problem: True.",
            "correspondence.md": "Synthetic review material; never a candidate.",
            "definitions.md": "No nonstandard definitions.",
            "Challenge.lean": "-- Test data only; never compiled.\ntheorem target : True := by trivial\n",
        }.items():
            (self.base / name).write_text(text)
        self.problem = {
            "schema_version": 1, "problem_id": "test-problem", "statement_version": "v1",
            "title": "Synthetic test", "claim_kind": "proof",
            "original_sources": [{"url": "https://example.org/problem", "citation": "Test only", "snapshot_sha256": None}],
            "scope": "Synthetic True statement", "required_theorems": ["target"], "toolchain_id": None,
            "trusted_files": [{"path": p.name, "sha256": file_digest(p)} for p in sorted(self.base.iterdir())],
            "review": {"status": "pending", "statement_digest": None, "reviewers": [], "evidence_url": None},
        }
        self.submission = {
            "schema_version": 1, "submission_id": "test-submission", "problem_id": "test-problem",
            "statement_version": "v1", "repository": "https://github.com/example/proof", "commit": "a" * 40,
            "targets": [{"module": "Synthetic", "declaration": "synthetic", "official_theorem": "target"}],
            "toolchain_id": None, "adapter_id": None, "paper_urls": ["https://example.org/paper"],
            "contribution": {"proof_authors": ["Test"], "formalization_authors": ["Test"],
                             "proof_route": "Synthetic", "ai_role": "None", "known_assumptions": [],
                             "prior_results": "Test data only", "public_source_authorized": True},
        }
        self.save()

    def write(self, relative, data):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))

    def save(self):
        self.write("problems/test-problem/v1/problem.json", self.problem)
        self.write("submissions/test-problem/test-submission.json", self.submission)

    def reject(self):
        self.save()
        with self.assertRaises(RegistryError):
            validate_registry(self.root)

    def approve_for_test(self):
        self.policy["approved_reviewers"] = ["reviewer-one", "reviewer-two"]
        self.write("policy/verification.json", self.policy)
        self.problem["toolchain_id"] = "test-environment"
        self.submission["toolchain_id"] = "test-environment"
        self.problem["original_sources"][0]["snapshot_sha256"] = "b" * 64
        self.problem["review"] = {
            "status": "approved", "statement_digest": statement_digest(self.problem),
            "reviewers": ["reviewer-one", "reviewer-two"], "evidence_url": "https://example.org/review",
        }
        self.save()

    def test_valid_pending_registration(self):
        result = validate_registry(self.root)
        self.assertEqual(list(result["submissions"]), ["test-submission"])

    def test_empty_registry_is_valid(self):
        import shutil
        shutil.rmtree(self.root / "problems/test-problem")
        shutil.rmtree(self.root / "submissions/test-problem")
        self.assertEqual(validate_registry(self.root)["submissions"], {})

    def test_mutable_or_injected_commits_rejected(self):
        for value in ("main", "latest", "abc123", "$(touch /tmp/x)", "a" * 40 + "\n"):
            with self.subTest(value=value):
                self.submission["commit"] = value
                self.reject()

    def test_unknown_executable_fields_rejected(self):
        self.submission["build_command"] = "exit 0"
        self.reject()

    def test_unsafe_repository_urls_rejected(self):
        for value in ("file:///tmp/repo", "http://github.com/a/b", "https://github.com.evil/a/b",
                      "https://github.com/a/b?cmd=x", "https://token@github.com/a/b", "https://github.com/a/../b"):
            with self.subTest(value=value):
                self.submission["repository"] = value
                self.reject()

    def test_all_official_targets_required(self):
        self.problem["required_theorems"].append("secondTarget")
        self.reject()

    def test_duplicate_target_mapping_rejected(self):
        self.submission["targets"].append({"module": "Another", "declaration": "another", "official_theorem": "target"})
        self.reject()

    def test_unknown_problem_version_rejected(self):
        self.submission["statement_version"] = "v2"
        self.reject()

    def test_submission_filename_identity_bound(self):
        self.submission["submission_id"] = "different-id"
        self.reject()

    def test_source_file_modification_requires_hash_update(self):
        (self.base / "Challenge.lean").write_text("theorem target : False := by sorry")
        self.reject()

    def test_missing_target_statement_rejected(self):
        (self.base / "Challenge.lean").unlink()
        self.reject()

    def test_unbound_file_rejected(self):
        (self.base / "Extra.lean").write_text("-- unexpected dependency")
        self.reject()

    def test_bound_json_dependency_supported(self):
        file = self.base / "lock.json"
        file.write_text('{"dependency": "test"}')
        self.problem["trusted_files"].append({"path": "lock.json", "sha256": file_digest(file)})
        self.save()
        validate_registry(self.root)

    def test_orphan_json_rejected(self):
        self.write("problems/orphan.json", {})
        self.reject()

    def test_duplicate_file_path_rejected(self):
        duplicate = copy.deepcopy(self.problem["trusted_files"][0])
        duplicate["sha256"] = "f" * 64
        self.problem["trusted_files"].append(duplicate)
        self.reject()

    def test_traversal_rejected(self):
        for path in ("../outside", "/tmp/outside", "dir/../../outside", "dir\\outside", "dir//file"):
            with self.subTest(path=path):
                self.problem["trusted_files"][0]["path"] = path
                self.reject()

    def test_symlink_rejected_even_within_root(self):
        target = self.base / "Challenge.lean"
        original = target.read_text()
        target.unlink()
        (self.root / "outside.lean").write_text(original)
        target.symlink_to(self.root / "outside.lean")
        self.reject()

    def test_directory_symlink_rejected(self):
        (self.root / "submissions/linked").symlink_to(self.base, target_is_directory=True)
        self.reject()

    def test_duplicate_json_fields_rejected(self):
        file = self.root / "duplicate.json"
        file.write_text('{"status":"pending","status":"approved"}')
        with self.assertRaises(RegistryError):
            read_json(file)

    def test_nonfinite_json_rejected(self):
        for value in ("NaN", "Infinity", "-Infinity"):
            file = self.root / "value.json"
            file.write_text('{"x":' + value + '}')
            with self.assertRaises(RegistryError):
                read_json(file)

    def test_oversize_json_rejected(self):
        file = self.root / "large.json"
        file.write_text(" " * (2 * 1024 * 1024 + 1))
        with self.assertRaises(RegistryError):
            read_json(file)

    def test_approved_review_is_bound_to_statement(self):
        self.approve_for_test()
        validate_registry(self.root)
        self.problem["scope"] = "Changed scope"
        self.reject()

    def test_content_change_invalidates_approval_even_after_rehash(self):
        self.approve_for_test()
        file = self.base / "definitions.md"
        file.write_text("Changed definitions")
        for item in self.problem["trusted_files"]:
            if item["path"] == file.name:
                item["sha256"] = file_digest(file)
        self.reject()

    def test_reviewers_must_be_distinct_and_allowlisted(self):
        self.approve_for_test()
        for reviewers in (["reviewer-one", "REVIEWER-ONE"], ["reviewer-one", "outsider"]):
            with self.subTest(reviewers=reviewers):
                self.problem["review"]["reviewers"] = reviewers
                self.reject()

    def test_formal_enable_flag_rejected(self):
        self.policy["formal_acceptance_enabled"] = True
        self.write("policy/verification.json", self.policy)
        self.reject()

    def test_extra_standard_axiom_rejected(self):
        self.policy["standard_axioms"].append("sorryAx")
        self.write("policy/verification.json", self.policy)
        self.reject()

    def test_no_fabricated_records(self):
        self.write("records/fake.json", {"formal_status": "formal_verified"})
        self.reject()

    def test_plan_never_executes_or_fetches(self):
        with patch("subprocess.run", side_effect=AssertionError("No execution allowed")), \
             patch("socket.create_connection", side_effect=AssertionError("No networking allowed")):
            result = plan_verification(self.root, "test-submission")
        self.assertEqual(result["machine_status"], "not_run")
        self.assertEqual(result["formal_status"], "pending")
        self.assertIn("backend_unconfigured", result["blockers"])
        self.assertIn("statement_review_pending", result["blockers"])

    def test_approved_review_does_not_fake_backend_success(self):
        self.approve_for_test()
        result = plan_verification(self.root, "test-submission")
        self.assertNotIn("statement_review_pending", result["blockers"])
        self.assertEqual(result["machine_status"], "not_run")

    def test_plan_digest_changes_for_new_candidate_commit(self):
        first = plan_verification(self.root, "test-submission")
        self.submission["commit"] = "c" * 40
        self.save()
        second = plan_verification(self.root, "test-submission")
        self.assertNotEqual(first["input_digest"], second["input_digest"])

    def test_plan_schema_rejects_fake_pass(self):
        result = plan_verification(self.root, "test-submission")
        result["machine_status"] = "passed"
        with self.assertRaises(RegistryError):
            schema_validate("plan", result)

    def test_unknown_and_unsafe_ids_rejected(self):
        for value in ("unknown", "../escape", "$(touch-file)", "--root", "x\n"):
            with self.subTest(value=value), self.assertRaises(RegistryError):
                plan_verification(self.root, value)

    def test_cli_exit_codes_and_no_overwrite(self):
        output = self.root / "plan.json"
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(main(["--root", str(self.root), "validate"]), 0)
            self.assertEqual(main(["--root", str(self.root), "plan", "test-submission", "--output", str(output)]), 3)
            before = output.read_bytes()
            self.assertEqual(main(["--root", str(self.root), "plan", "test-submission", "--output", str(output)]), 2)
            self.assertEqual(output.read_bytes(), before)
            self.assertEqual(main(["--root", str(self.root), "plan", "missing"]), 2)


if __name__ == "__main__":
    unittest.main()
