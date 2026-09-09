# math-lean-verification

[![Registry CI](https://github.com/Federico2014/math-lean-verification/actions/workflows/ci.yml/badge.svg)](https://github.com/Federico2014/math-lean-verification/actions/workflows/ci.yml)

Infrastructure for verifying Lean formalizations of mathematical results, initially for the Justin Sun Prize. The goal is to check both that **a proof is valid under the accepted logic and that it proves the intended mathematical problem.**

## Current status

The DGG candidate has passed real Lean proof verification in CI, with result
**`verified` under an explicit administrator exception for statement review**.
See [Registered candidates](#registered-candidates) for the fixed proof source and
exact verification run. **Formal acceptance remains pending.** Use
`python -m verifier list` to list registrations and their statement review records;
it does not retrieve CI results.

Available components include candidate intake forms, registration schemas, original-problem and statement-correspondence templates, hash and target-coverage validation, CI tests, and a maintainer preflight entry point. The CI badge reports only repository code and registration checks.

The [Lean merge gate](docs/lean-merge-gate.md) uses trusted problem workspaces, reusable environment configurations, explicit source mappings and checked proof bridges. It runs isolated builds, Comparator statement/axiom checks, and Lean plus Nanoda replay. The existing core/Std environment has onboarding evidence; the additional Lean 4.28 / Mathlib profile has [real onboarding evidence](docs/workspace-onboarding.md) for its explicitly limited module scope. Durable formal archives and reviewer accreditation remain separate activation requirements.

Inspect a project's environment without running its code:

```bash
python -m verifier inspect-environment /path/to/project
```

Reuse approved configurations whenever possible. Version differences normally add configuration, not another workflow; special requirements need explicit adaptation. See [environment onboarding](docs/environment-onboarding.md).

The [generic intake guide](docs/generic-intake.md) covers `draft-submission`,
`draft-environment`, hash-bound source adaptation without a fork, automatic
environment regression matrices and protected-main revalidation. Drafts and
environment test success never grant approval.

## Registered candidates

Candidates whose registration PRs are merged into `main` are listed here, one row
per submission. Each row links the registration, fixed proof commit and actual
verification evidence. Registration, Lean proof verification and award decisions
are separate states; environment regression success is not a candidate result.

The DGG submission uses the approved `lean-4-32-rc1-mathlib-dgg` environment and
[DGG v1 workspace](problems/dgg-cost/v1/statement.md). Its approval is an explicit
[administrator exception](docs/administrator-approvals/dgg-cost-v1.md) by
`Federico2014`; two-person independent mathematical review remains incomplete.
[Issue #12](https://github.com/Federico2014/math-lean-verification/issues/12)
tracks the review work. [PR #14](https://github.com/Federico2014/math-lean-verification/pull/14)
was merged at `4677f1f`. Its [successful candidate verification](https://github.com/Federico2014/math-lean-verification/actions/runs/34342252724)
checked PR head `806d9b0ac4cb6fcc031b42f7aadb8bc02ec90d01` against protected
base `dec0d00a2e7e2cdedff418f6f25e0aa932b37854`, after the administrator
approval and policy changes. All eight machine stages completed, including
statement comparison, transitive axiom auditing, Lean kernel replay and Nanoda
replay. The result records `machine_status: passed`, `verification_status: verified`,
`review_approval_kind: administrator_exception` and `formal_status: pending`.
[Revalidation of merged commit 4677f1f](https://github.com/Federico2014/math-lean-verification/actions/runs/34354995262)
is a separate run; inspect it for that revision's outcome.

| Candidate / submission | Statement version / registration | Fixed proof source | Lean verification / evidence |
| --- | --- | --- | --- |
| DGG / Goemans cost conjecture — `dgg-cost-jyh` | [dgg-cost/v1](problems/dgg-cost/v1/statement.md) / [registration](submissions/dgg-cost/dgg-cost-jyh.json) | [jyh/dinitz-verify @ ffba352](https://github.com/jyh/dinitz-verify/tree/ffba3523f0edd14be3460d039f22a6b98c02fd9e) | `verified` — [PR verification at 806d9b0](https://github.com/Federico2014/math-lean-verification/actions/runs/34342252724); machine `passed`, administrator exception; formal acceptance `pending` |

This table is maintained in documentation; CI publishes checks and evidence but
does not rewrite the README. Add a row in the registration PR using `not_run`
until a bound machine result exists. After successful verification and merge,
update the row in a documentation change with the exact run and checked revision.
Keep PR verification and subsequent `main` revalidation outcomes distinct. Source,
environment or verification-rule changes require fresh evidence; an earlier pass
must not describe changed inputs.

## Adding a candidate

**The normal path is: provide the proof source → reuse a reviewed problem and approved environment → open a registration PR → inspect the automatic CI result.** The same workflow handles future candidates; an ordinary submission does not need a new workflow. Actual Lean execution happens in isolated CI containers. Local commands below only prepare or validate registration data.

### 1. Provide the candidate materials

Open a [candidate submission issue](https://github.com/Federico2014/math-lean-verification/issues/new?template=candidate.yml) with the original problem and paper links, public GitHub proof repository, full 40-character commit SHA, target Lean modules/declarations, Lean version, dependencies, assumptions and author attribution. A paper without Lean proof source cannot undergo machine verification. Publish only materials you are authorized to share.

### 2. Confirm the problem and environment

With maintainers, identify the existing `problem_id`, `statement_version`, complete official theorem list and approved `toolchain_id`. Reuse these when available.

For a new problem, maintainers first prepare a separate PR under `problems/<problem-id>/<version>/` containing the trusted Lean statement and permitted proof interface. For a new environment, use the [environment onboarding process](docs/environment-onboarding.md): pin dependencies, run real compatibility tests and record approval in a separate PR. Both configurations must reach `main` before candidate execution. Pending statement review permits diagnostic execution, but the exact statement review must be approved before the candidate gate can pass.

These are reusable setup steps. A candidate PR cannot approve or alter its own problem, environment or verification policy.

### 3. Prepare the registration files

Set up this repository's [Python environment](#local-development). From this repository, inspect a local source checkout matching the candidate's fixed commit, then generate a draft. Replace the example IDs, theorem names and commit placeholder:

```bash
python -m verifier inspect-environment /path/to/candidate-project
python -m verifier draft-submission /path/to/candidate-project \
  --repository https://github.com/OWNER/REPOSITORY \
  --commit FULL_40_HEX_COMMIT \
  --submission-id example-proof --problem-id example-problem \
  --statement-version v1 \
  --target Submission upstream_theorem official_theorem \
  --output /tmp/candidate-draft.json
```

`--target` means `MODULE DECLARATION OFFICIAL_THEOREM`; repeat it for every official target. Review the draft's `blockers`, then save **only its `submission` object** as `submissions/example-problem/example-proof.json`. Alternatively, fill in [the submission template](templates/submission.json) directly.

Complete the paper links, authorship, proof route, AI role, assumptions and prior results. The generated draft deliberately leaves publication permission false; confirm it only when authorization actually exists. Check the environment ID and source selection rather than treating a suggested match as approval.

| Registration field | What to provide |
| --- | --- |
| `execution.project_root` | Project directory relative to the upstream repository; `.` for its root. |
| `execution.include` | Lean files needed by the proof, relative to that root, such as `Submission.lean` and `Submission/**`. |
| `execution.proof_files` | Optional local bridge paths and SHA-256 hashes. Store them under `proofs/<submission-id>/`. |
| `execution.source_transforms` | Optional hash-bound renames or exact replacements; see [source adaptation](docs/generic-intake.md#adapt-source-modules-without-a-fork). |

If the upstream theorem needs to expose the official name or statement, complete [the bridge template](templates/Bridge.lean) using the trusted workspace's `solution_module` and permitted paths. Keep `adapter_id` null. Bridges and adapted sources undergo the full proof checks. Custom Lake programs, native plugins and precompiled artifacts require separately supported tooling; they are not ordinary submission inputs.

### 4. Open the candidate PR

Validate the completed registration locally:

```bash
python -m verifier validate
```

This checks metadata and hashes; it does not execute Lean. Update the [registered candidate list](#registered-candidates), commit the registration and any bridge files on your branch or fork, then open a PR targeting `main`. Link the candidate issue and describe the official target mapping and any source adaptation. Opening or updating the PR automatically triggers **Trusted Lean verification**; no local Lean run is required.

### 5. Read the CI result and correct failures

The required checks are `registry`, `tests` and `lean-verification`. CI retrieves the fixed source commit, builds in isolation, checks all required statements and axioms, and performs Lean plus Nanoda replay. A successful build or green Registry CI badge alone does not establish proof verification.

Open the **Trusted Lean verification** run from the PR checks. Inspect `lean-plan-*` for prerequisite failures and `lean-evidence-<submission-id>-<head-sha>` for `report.md`, `verification-result.json` and detailed logs.

- Missing workspace, unsupported environment or stale hash: correct the registration or complete maintainer onboarding.
- Build, statement, axiom or replay failure: fix the proof or bridge, update the bound commit/hashes and push again.
- `review_pending`: machine checks passed, but mathematical review still blocks the gate.
- `verified`: machine checks and the bound approval policy passed. Inspect `review_approval_kind`: `independent_review` records normal review, while `administrator_exception` records an explicit statement-specific waiver. Formal acceptance and award decisions remain separate.

Each update needs fresh verification. Maintainers can rerun **Trusted Lean verification** from `main` with the open PR number. After relevant changes reach `main`, **Revalidate registered Lean proofs** rechecks registered candidates. See [the contribution process](CONTRIBUTING.md) for review and evidence requirements.

## Verification principles

```text
Original mathematical problem
    ↓ Independent mathematical review: quantifiers, definitions, scope, assumptions, conclusion
Official Lean statement (fixed version)
    ↓ Machine comparison + axiom audit + independent checker replay
Candidate proof (fixed commit)
    ↓ Complete evidence archive linked to review records
Formal acceptance status (separate from prize amount, priority, and recipient identity)
```

Faithfulness from natural language to Lean requires independent review; machine checking alone cannot establish that the natural-language problem was understood correctly. Candidates cannot change the problem or allowlist to make their proofs pass.

## Local development

Use Python 3.12. Install the pinned development dependencies as follows; `requirements-dev.txt` is not used for formal CI.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python -m verifier validate
python -m verifier list
```

CI uses `requirements-ci.lock` and `--require-hashes` on Linux x86_64 / Python 3.12. The two dependency lists must keep matching versions.

After registration, run `python -m verifier plan <submission-id> --output plan.json`. Exit codes: `0` means registration validation succeeded; `2` means invalid input; `3` means preflight completed but formal verification is blocked. None of these exit codes indicates that a proof has been verified.

## Documentation

- [Lean proof merge gate](docs/lean-merge-gate.md)
- [Technical design](docs/design.md)
- [Candidate contribution process](CONTRIBUTING.md)
- [Statement correspondence review](docs/statement-review.md)
- [Maintainer runbook](docs/maintainer-runbook.md)
- [Implementation status and acceptance checklist](docs/implementation-status.md)
- [Verification and acceptance policy](policy/verification.md)
- [Security boundaries](SECURITY.md)

Original repository code is licensed under MIT. Third-party materials retain their own licenses and must include applicable notices. External papers and proof sources retain their owners' licenses; integration or archiving does not change those licenses.
