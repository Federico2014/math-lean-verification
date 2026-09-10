"""Regression guards for repository workflows and published schemas."""

import re
from fnmatch import fnmatchcase
import unittest

import yaml
from jsonschema import Draft202012Validator

from verifier.registry import ROOT, read_json, validate_registry


class RepositoryTests(unittest.TestCase):
    def test_backend_manifest_matches_build_pins(self):
        manifest = read_json(ROOT / "backend/toolchain.json")
        dockerfile = (ROOT / "backend/Dockerfile").read_text()
        builder = (ROOT / "backend/build-comparator.py").read_text()
        for key in ("comparator_commit", "exporter_commit", "nanoda_commit", "lean_archive_sha256", "lean_release"):
            self.assertIn(manifest[key], dockerfile, key)
        self.assertIn(manifest["exporter_commit"], builder)
        profile = read_json(ROOT / "backend/seccomp.json")
        allowed = {name for rule in profile["syscalls"] if rule["action"] == "SCMP_ACT_ALLOW" for name in rule["names"]}
        self.assertFalse(allowed & {"ptrace", "process_vm_readv", "process_vm_writev"})

    def test_schemas_well_formed(self):
        for path in (ROOT / "schemas").glob("*.json"):
            with self.subTest(path=path.name):
                schema = read_json(path)
                Draft202012Validator.check_schema(schema)
                self.assertFalse(schema["additionalProperties"])

    def test_actual_registry_is_valid(self):
        validate_registry(ROOT)

    def workflows(self):
        for path in (ROOT / ".github/workflows").glob("*.yml"):
            yield path, yaml.load(path.read_text(), Loader=yaml.BaseLoader)

    def test_ci_has_read_only_permissions_and_no_privileged_events(self):
        for path, workflow in self.workflows():
            with self.subTest(path=path.name):
                self.assertEqual(workflow["permissions"], {"contents": "read"})
                if path.name != "lean-verification.yml":
                    self.assertNotIn("pull_request_target", workflow["on"])
                self.assertNotIn("workflow_run", workflow["on"])
                for name, job in workflow["jobs"].items():
                    self.assertEqual(job["runs-on"], "ubuntu-24.04")
                    allowed = {
                        ('resume-candidates.yml', 'resume'): {'contents': 'read', 'pull-requests': 'read', 'actions': 'write'},
                        ('candidate-catalog.yml', 'build'): {'contents': 'read', 'actions': 'read'},
                        ('candidate-catalog.yml', 'deploy'): {'pages': 'write', 'id-token': 'write'},
                    }
                    if (path.name, name) in allowed:
                        self.assertEqual(job['permissions'], allowed[path.name, name])
                        self.assertEqual(job['if'], "github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop'" if path.name == 'resume-candidates.yml' else "github.ref == 'refs/heads/main'")
                    elif path.name != "lean-verification.yml":
                        self.assertNotIn("permissions", job)
                    self.assertNotIn("secrets", job)
                    self.assertIn("timeout-minutes", job)

    def test_trusted_gate_never_checks_out_pr_code_or_grants_execution_write_access(self):
        workflow = yaml.load((ROOT / ".github/workflows/lean-verification.yml").read_text(), Loader=yaml.BaseLoader)
        self.assertEqual(set(workflow["on"]), {"pull_request_target", "workflow_dispatch"})
        self.assertEqual(workflow['on']['pull_request_target']['branches'], ['main', 'develop'])
        self.assertIn('edited', workflow['on']['pull_request_target']['types'])
        self.assertIn('github.event.pull_request.base.ref', workflow['run-name'])
        jobs = workflow["jobs"]
        self.assertNotIn("permissions", jobs["verify"])
        self.assertEqual(jobs["verify"]["needs"], ["resolve", "plan"])
        self.assertEqual(jobs['resolve']['concurrency'], jobs['publish']['concurrency'])
        self.assertEqual(jobs['resolve']['concurrency']['cancel-in-progress'], 'false')
        for name in ["resolve", "publish"]:
            self.assertEqual(jobs[name]["permissions"], {"contents": "read", "statuses": "write"})
        for name, job in jobs.items():
            checkouts = [s for s in job["steps"] if s.get("uses", "").startswith("actions/checkout@")]
            self.assertEqual(len(checkouts), 1)
            ref = checkouts[0]["with"]["ref"]
            expected = "${{ github.event.pull_request.base.sha || github.sha }}" if name == "resolve" else "${{ needs.resolve.outputs.base }}"
            self.assertEqual(ref, expected)
            self.assertNotIn("head", ref)
        self.assertEqual(jobs["publish"]["needs"], ["resolve", "plan", "verify"])
        self.assertNotIn("download-artifact", str(jobs["publish"]))
        self.assertIn("needs.verify.result", str(jobs["publish"]))
        self.assertNotIn("continue-on-error", str(workflow))

    def test_actions_pinned_and_checkout_credentials_disabled(self):
        for path, workflow in self.workflows():
            for job in workflow["jobs"].values():
                for step in job["steps"]:
                    if "uses" in step:
                        self.assertRegex(step["uses"], r"^[\w-]+/[\w-]+@[a-f0-9]{40}$")
                        if step["uses"].startswith("actions/checkout@"):
                            self.assertEqual(step["with"]["persist-credentials"], "false")
                    if "run" in step:
                        self.assertNotIn("${{", step["run"])
                        self.assertNotIn("lake build", step["run"])
                        self.assertNotIn("continue-on-error", step)

    def test_backend_filters_keep_execution_changes_and_skip_static_entrypoints(self):
        workflow = yaml.load((ROOT / '.github/workflows/backend-ci.yml').read_text(), Loader=yaml.BaseLoader)
        patterns = workflow['on']['pull_request']['paths']
        def triggers(paths):
            # These workflow filters use only literal filenames and directory/**.
            for path in paths:
                selected = False
                for pattern in patterns:
                    if fnmatchcase(path, pattern.removeprefix('!')):
                        selected = not pattern.startswith('!')
                if selected:
                    return True
            return False
        for path in ('backend/export.py', 'backend/GateReplay.lean', 'verifier/lean_backend.py',
                     'verifier/intake.py', 'verifier/merge_gate.py', 'verifier/revalidate.py',
                     'verifier/registry.py', 'verifier/build_environment.py', 'verifier/environment_matrix.py',
                     'verifier/environments.py', 'verifier/source_adaptation.py', 'verifier/future_executor.py',
                     'environments/new/environment.json', 'schemas/environment.schema.json',
                     'scripts/backend_smoke.py', 'requirements-ci.lock', '.github/workflows/backend-ci.yml'):
            with self.subTest(path=path):
                self.assertTrue(triggers([path]))
        for path in ('README.md', 'docs/design.md', 'verifier/__main__.py', 'verifier/catalog.py',
                     'verifier/onboarding.py', 'verifier/resume.py', 'candidates/example.json'):
            with self.subTest(path=path):
                self.assertFalse(triggers([path]))
                self.assertTrue(triggers([path, 'verifier/lean_backend.py']))
        self.assertIn('workflow_dispatch', workflow['on'])
        # Filtering a required workflow can leave its required status pending.
        for filename, event in [('ci.yml', 'pull_request'), ('lean-verification.yml', 'pull_request_target')]:
            required = yaml.load((ROOT / '.github/workflows' / filename).read_text(), Loader=yaml.BaseLoader)
            self.assertNotIn('paths', required['on'][event] or {})
            self.assertNotIn('paths-ignore', required['on'][event] or {})

    def test_main_revalidation_coalesces_revisions_but_separates_manual_selections(self):
        workflow = yaml.load((ROOT / '.github/workflows/revalidate.yml').read_text(), Loader=yaml.BaseLoader)
        concurrency = workflow['concurrency']
        self.assertEqual(concurrency['cancel-in-progress'], 'true')
        self.assertNotIn('github.sha', concurrency['group'])
        self.assertIn('github.ref', concurrency['group'])
        selection = "inputs.submission && format('selected-{0}', inputs.submission) || 'all'"
        self.assertIn(selection, concurrency['group'])
        self.assertIn(selection, workflow['run-name'])
        # Current-SHA catalog provenance requires evidence even after docs commits.
        self.assertEqual(workflow['on']['push'], {'branches': ['main']})

    def test_ci_locks_have_exact_versions_hashes_and_match_dev_versions(self):
        pinned = []
        for line in (ROOT / "requirements-ci.lock").read_text().splitlines():
            if not line or line.startswith("#"):
                continue
            self.assertRegex(line, r"^[A-Za-z0-9-]+==[0-9.]+ --hash=sha256:[a-f0-9]{64}$")
            pinned.append(line.split(" ")[0])
        dev = [x for x in (ROOT / "requirements-dev.txt").read_text().splitlines() if x and not x.startswith("#")]
        self.assertEqual(pinned, dev)

    def test_markdown_local_links_exist(self):
        for doc in ROOT.rglob("*.md"):
            if ".git" in doc.parts or ".venv" in doc.parts:
                continue
            for target in re.findall(r"\]\(([^)]+)\)", doc.read_text()):
                if "://" in target or target.startswith("#"):
                    continue
                with self.subTest(doc=doc.relative_to(ROOT), target=target):
                    self.assertTrue((doc.parent / target.split("#")[0]).exists())

    def test_templates_have_expected_fields_without_registering_candidates(self):
        problem = read_json(ROOT / "templates/problem/problem.json")
        submission = read_json(ROOT / "templates/submission.json")
        self.assertEqual(set(problem), set(read_json(ROOT / "schemas/problem.schema.json")["required"]) | {"workspace"})
        self.assertEqual(set(submission), set(read_json(ROOT / "schemas/submission.schema.json")["required"]) | {"execution"})
        self.assertEqual(problem["review"]["status"], "pending")


if __name__ == "__main__":
    unittest.main()
