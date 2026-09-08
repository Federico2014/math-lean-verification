# Adding candidates and contributing

Submitting a candidate requests verification. It does not establish an award, a valid proof, or priority for a first solution.

Use English for repository documentation, comments, forms, registration descriptions, issues, and pull requests. Preserve source titles, proper names, mathematical notation, and code identifiers where needed for accurate attribution.

## 1. Register the materials

Open a "Submit a candidate result" issue with the original mathematical problem, paper, first public disclosure date, intended proof/counterexample/partial-result scope, Lean repository URL, full 40-character commit, all target theorems, versions, and attribution. Only public materials authorized for sharing belong in this repository.

If no Lean project exists, open an issue and explicitly mark the formalization materials as pending. Do not create a submission that falsely appears ready for verification.

Issues do not automatically fetch or execute source code, create official statements, or produce verification conclusions.

## 2. New or existing problem

If the exact problem and official statement version already exist, reference their `problem_id` and `statement_version`. Multiple proof projects may be registered for the same problem, each with a globally unique `submission_id`.

For a new problem, create `problems/<problem-id>/v1/`:

```text
problem.json
statement.md
correspondence.md
definitions.md
Challenge.lean
```

Use the [problem templates](templates/problem/) and write the materials from the original problem. Templates contain placeholders and cannot pass validation unchanged. Official statements require [independent review](docs/statement-review.md); copying candidate code does not constitute blind drafting.

`problem.json` records original sources, scope, direction of the claim, and all `required_theorems`. `trusted_files` must list every file in the problem directory except `problem.json`, with its SHA-256. Update hashes whenever bound files change; existing approvals also require renewed review.

Generate file hashes with `shasum -a 256 <file>` on macOS or `sha256sum <file>` on Linux. While toolchain integration is unavailable, keep `toolchain_id` as `null` and review status as `pending`.

## 3. Register a proof

Copy the [submission template](templates/submission.json) to:

```text
submissions/<problem-id>/<submission-id>.json
```

Specify a fixed public repository URL, commit, target modules, and declarations. Each official target must correspond to exactly one target record; do not register only the easy parts.

Registrations do not accept `main`, `latest`, arbitrary shell commands, or candidate-defined axiom allowlists. If adaptation is required, submit a separate reviewed change under `adapters/`. The current backend is not implemented, so registering an adapter ID does not execute it.

Record authors, formalization contributors, and proof strategy, with explicit prior results, extra assumptions, and partial progress. Public attribution must exclude payment details, identity documents, and internal background checks.

## 4. Local validation and PR

Install development dependencies as described in the README, then run:

```bash
python -m verifier validate
python -m unittest discover -s tests -v
```

Open a PR from a new branch, link the registration issue, and explain the change, sources, and verification scope. Creating or updating a PR triggers CI automatically; `registry`, `tests`, and `lean-verification` must pass before merging. PR review approval is currently optional, so authors with merge permission may merge their own PRs.

Pending statement drafts may be registered separately, but candidate proof PRs must reference an already-approved statement and toolchain on `main` and pass the [Lean merge gate](docs/lean-merge-gate.md). Unsupported profiles, missing bridges, and pending reviews block candidate merging. Metadata validation alone does not establish mathematical correctness. Code-merge permissions do not replace the two independent mathematical reviewers required for formal acceptance.

## 5. Maintainer preflight and subsequent full verification

After reviewing and merging the registration, a maintainer selects **Verification preflight** in Actions, uses the `main` branch, and enters the `submission_id`.

The current workflow validates registration and produces a `plan.json` bound to input hashes. With no backend configured, it exits with code 3 and explicit blockers. It does not download candidates, run Lean, or mark proofs successful. Its artifact is temporary preflight data, not a formal evidence archive.

The supported source-only profile performs a clean offline build, trusted statement comparison, axiom audit, and dual-checker replay before candidate merging. Mathlib integration and durable formal archiving remain outstanding. Formal acceptance still requires valid statement review; see the [activation checklist](docs/implementation-status.md).

## 6. Changes and resubmission

Changing the candidate commit or targets produces a new preflight input digest. Future formal records must be appended, never overwritten. Corrections to an official problem or its definitions require invalidating the old version, publishing a new version, and reviewing it again. Do not change the problem to accommodate the current proof.
