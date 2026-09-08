# Adding candidates and contributing

Use English for repository content, issues and PRs. Preserve mathematical notation and original proper names for attribution. Registration and CI results do not decide awards.

## 1. Open a candidate issue

Provide the original problem and scope, public proof/paper links, a full upstream commit, all target modules/declarations, Lean/dependency information, known assumptions and attribution. Missing materials remain in the issue until supplied.

## 2. Reuse or prepare a trusted problem

Reference an existing `problem_id` and `statement_version`, or prepare a separate problem PR using [the templates](templates/problem/). Bind all files under the problem version in `trusted_files`, fix the complete official target list and perform [statement review](docs/statement-review.md).

For the workspace path, set `workspace.solution_module`, permitted `workspace.submission_paths`, and the canonical `workspace.environment_digest`. The candidate PR cannot change this trusted interface. Pending review permits diagnostics only; merge still requires the approved review.

## 3. Identify and freeze the environment; adapt only when needed

Run the non-executing inspector against a local source checkout:

```bash
python -m verifier inspect-environment /path/to/project
```

Reuse an approved environment when the full dependency/tool configuration matches. A version difference normally adds environment configuration, not a workflow. Directory and theorem-name differences normally belong in source mapping and a bridge. Special dependencies or unsupported tools require explicit adaptation.

New environment configuration belongs in a separate maintenance PR. Freeze versions and file hashes, run real onboarding tests and record evidence before approving the environment and admitting its ID in policy. A suggested match or a `pending` environment cannot pass the candidate gate.

## 4. Submit the candidate PR

Copy [the submission template](templates/submission.json) to `submissions/<problem-id>/<submission-id>.json`. Set the full upstream commit, complete target mapping and environment ID. Add `execution.project_root`, `execution.include` and hashed `execution.proof_files` as needed. Place local Lean bridges under `proofs/<submission-id>/`.

Use [the bridge template](templates/Bridge.lean) when needed. A bridge calls the upstream theorem and proves the official statement with the required name. It is checked proof code, not trusted configuration. Selected upstream files and bridge overlays may not collide or replace trusted files. Arbitrary shell commands, upstream Lake programs and precompiled binaries are not accepted inputs. `adapter_id` remains null; use proof overlays for Lean bridges.

Link the candidate issue in the PR and run:

```bash
python -m verifier validate
python -m unittest discover -s tests -v
```

PR creation and updates automatically trigger verification. Required `registry`, `tests` and `lean-verification` checks must pass. Code merge permission for your own PR does not replace the mathematical review policy.

## 5. Understand failures and retain evidence

Read the trusted plan first. Missing statements, unsupported environments and stale hashes may prevent proof execution. Otherwise inspect per-stage evidence: a build success alone is not a proof pass. Fix the input and push again; previous results cannot authorize the new version.

Maintainers can rerun **Trusted Lean verification** from `main` using an open PR number. The `plan` CLI and **Verification preflight** remain non-executing diagnostics and cannot grant proof acceptance.

Evidence artifacts contain sources, exports, checker logs and version bindings. Verify sealed archive integrity with `python -m verifier.evidence verify <archive.zip>`. Durable archival and award acceptance remain subject to the [activation checklist](docs/implementation-status.md).
