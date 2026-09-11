# math-lean-verification

[![Registry CI](https://github.com/Federico2014/math-lean-verification/actions/workflows/ci.yml/badge.svg)](https://github.com/Federico2014/math-lean-verification/actions/workflows/ci.yml)

Infrastructure for verifying Lean formalizations of mathematical results, initially for the Justin Sun Prize. The goal is to check both that **a proof is valid under the accepted logic and that it proves the intended mathematical problem.**

## Current status

See [Registered candidates](#registered-candidates) for current registrations and
machine verification results. Formal acceptance is a separate process. Use
`python -m verifier list` to list registered candidate IDs;
it does not retrieve CI results.

Available components include single-file candidate intake, registration schemas, original-problem and statement-correspondence templates, hash and target-coverage validation, and automatic CI verification. The Registry CI badge reports only repository code and registration checks.

The [Lean merge gate](docs/lean-merge-gate.md) uses trusted problem workspaces, reusable environment configurations, explicit source mappings and checked proof bridges. It runs isolated builds, Comparator statement/axiom checks, and Lean plus Nanoda replay. The existing core/Std environment has onboarding evidence; the additional Lean 4.28 / Mathlib profile has [real onboarding evidence](docs/workspace-onboarding.md) for its explicitly limited module scope. Durable formal archives and reviewer accreditation remain separate activation requirements.

Inspect a project's environment without running its code:

```bash
python -m verifier inspect-environment /path/to/project
```

Reuse approved configurations whenever possible. Version differences normally add configuration, not another workflow; special requirements need explicit adaptation. See [environment onboarding](docs/environment-onboarding.md).

The [environment and adaptation guide](docs/generic-intake.md) covers
`draft-environment`, hash-bound source adaptation without a fork, automatic
environment regression matrices and protected-default-branch revalidation. Drafts and
environment test success never grant approval.

## Registered candidates

| Candidate | Fixed proof source | Machine verification | Formal acceptance |
| --- | --- | --- | --- |
| [DGG / Goemans cost conjecture: rational counterexample](candidates/dgg-cost-jyh.json) (`dgg-cost-jyh`, statement `v1`) | [jyh/dinitz-verify @ ffba3523f0ed](https://github.com/jyh/dinitz-verify/tree/ffba3523f0edd14be3460d039f22a6b98c02fd9e) | [Verified — 2026-09-11](https://github.com/Federico2014/math-lean-verification/actions/runs/34560237399/attempts/1), verifier `ab95172eade9` | [Accepted by administrator Federico2014 — 2026-09-11](https://github.com/Federico2014/math-lean-verification/releases/tag/acceptance-dgg-cost-v1-20260911) |

This summary records the linked verification run and immutable acceptance decision.
The administrator acceptance applies to the revisions in its record; it does not
assert two independent reviewers or an award decision.

[Open the live candidate catalog](https://Federico2014.github.io/math-lean-verification/)
for the current protected default-branch status, full proof and verifier revisions,
and evidence links. After a candidate PR merges, CI revalidates it and publishes
updated status. Publication also runs on a 15-minute schedule; GitHub may delay
scheduled jobs. Maintainers update this README summary from recorded evidence.
Deployment needs the one-time [Pages setup](docs/simplified-intake.md#deployment).

## Adding a candidate

The complete workflow runs from submission through registration and a separate
formal acceptance decision. New candidate PRs currently target protected `develop`,
which is also the default branch.

| Step | Responsible party | Work and completion condition |
| --- | --- | --- |
| 1. Prepare materials | Contributor | Complete one candidate JSON with the original problem, fixed proof commit, targets, attribution, assumptions and publication permission. |
| 2. Open a PR | Contributor; CI prepares the plan | Open one candidate PR against `develop`; trusted CI identifies required configuration and any blockers. |
| 3. Clear prerequisites | Maintainer and authorized reviewers | Approve the exact official statement, correspondence, environment and any adaptation in separate maintenance PRs. |
| 4. Verify the proof | Trusted CI | Run isolated proof checks and archive evidence; inspect the actual candidate result and all required checks. |
| 5. Merge and register | Maintainer | Merge after required checks and applicable review pass. Closing an unmerged PR does not register the candidate. |
| 6. Publish registration | CI and maintainer | Revalidate on the protected default branch, publish the live catalog and add the README summary with evidence links. |
| 7. Publish formal acceptance | Authorized decision maker and archive maintainer | Record a separate decision for fixed revisions, preserve and verify a durable archive, and publish its acceptance links. |

### 1. Prepare one candidate file

Copy [templates/candidate.json](templates/candidate.json) to
`candidates/<candidate-id>.json`; IDs use lowercase words separated by hyphens.
Use the GitHub web editor or your usual Git client. Provide:

- The registered `problem_id`, or a `problem` object containing `title`,
  `source_url` and `scope` for maintainer correspondence review.
- A public GitHub proof repository and full 40-character immutable commit.
- Every target Lean module and theorem declaration.
- Proof/formalization authors, proof route, AI contribution and known assumptions.
- `public_source_authorized: true` only when you have permission to submit the source.

Replace template placeholders. An Issue is optional. Submission does not require a
local Lean installation, environment ID, source hashes, generated registration or
README edit. Use `source.project_root` for a project in a subdirectory.
Never execute candidate Lean, Lake or plugins on the host.

### 2. Open one PR per candidate against develop

Opening, updating or retargeting the PR automatically triggers **Trusted Lean verification**.
Both `develop` and `main` are supported protected targets; new work goes to `develop`.
CI reads the fixed source as data, matches approved environments, selects local
imports, prepares internal registration and generates a proof bridge when the
mapping is unambiguous. Preparation alone does not verify a proof.
Only changed candidate files and optional bridge files belong in this PR.

### 3. Clear prerequisite and preparation blockers

| Result | Next action |
| --- | --- |
| `needs_information` | Complete the missing candidate materials and update the PR. |
| `waiting_problem` / `waiting_review` | Maintainers prepare the official workspace and approved correspondence. |
| `waiting_environment` | Maintainers run real backend tests and approve a compatible pinned environment. |
| `needs_adaptation` | Maintainers review the reported mapping/build requirements; provide an optional checked bridge if needed. |
| `infrastructure_error` | Retry the trusted workflow after resolving the source/service failure. |
| `failed` | Inspect proof evidence and correct the proof or integration failure before retrying. |
| `verified` | Actual machine checks and exact statement approval passed; proceed to the merge requirements below. |

Keep the candidate PR open while prerequisites are prepared. Maintainers merge
trusted problem, environment, policy and approval changes in separate PRs against
the same target branch. Each target-branch push automatically replans waiting
candidate PRs against its new revision while preserving their submitted head.
No empty commit or rebase is needed merely to pick up approved configuration;
resolve actual merge conflicts normally. Manual recovery is available on either
supported branch; the periodic schedule runs on the default branch.

Normal statement review requires two accredited independent reviewers. An explicitly
authorized administrator exception must bind the exact problem, statement version
and digest through protected policy and approval changes. It does not constitute
independent review or formal acceptance. See [statement review](docs/statement-review.md).

### 4. Inspect the machine verification evidence

For a ready candidate, trusted CI runs isolated source builds, checks all required
targets and bridges, compares the official statements, audits transitive axioms,
and performs Lean and Nanoda replay. It seals and uploads the evidence.

Read `lean-plan-*` / scheduler diagnostics for prerequisites, and
`lean-evidence-*` for `report.md`, `verification-result.json` and stage logs.
Require `registry`, `tests` and `lean-verification` to pass and confirm the candidate
itself has successful proof execution. A green registry check, unit test,
environment build or Markdown-only maintenance check alone is not proof verification.
Changed source, statement, environment, policy, PR head or protected base bindings
require fresh checks; evidence from a different revision remains historical.

### 5. Merge and register the candidate

A maintainer merges after all required checks and applicable review are satisfied.
Confirm the PR is **Merged**, not merely **Closed**: only merging registers its
candidate files on the protected target branch.

### 6. Publish the catalog and README entry

Every protected default-branch push starts **Revalidate registered Lean proofs**,
including documentation commits because the verifier revision changes.
**Publish registered candidates** updates the
[live catalog](https://Federico2014.github.io/math-lean-verification/); publication
also runs on a 15-minute schedule, which GitHub may delay.

Check the catalog's revision, generation time, candidate ID, fixed source and
evidence link. Only proof success for the current default-branch revision can
show current `verified`.

Maintainers separately add the candidate to [Registered candidates](#registered-candidates)
in this README, linking its registration, fixed source and recorded verification.
Add a formal acceptance link only after the decision has been published.
README evidence links describe their cited revisions; use the live catalog for
current status.

### 7. Publish formal acceptance separately

Machine verification does not automatically grant formal acceptance. Automatic
formal acceptance remains disabled (`formal_acceptance_enabled: false`).
For an explicitly authorized, scoped administrator acceptance:

1. Record the administrator, decision, date, review basis and limitations. Label
   it as administrator acceptance without claiming two-person independent review.
2. Bind the decision to the exact problem/statement, source, verifier,
   environment/policy and successful run/attempt with its evidence.
3. Preserve the complete evidence and licenses in a durable archive with file
   checksums; verify uploaded files by reading them back. Temporary Actions
   artifacts alone are insufficient. Never overwrite immutable records.
4. Publish and verify the immutable acceptance record. Add its pinned reference
   to `docs/acceptance-publications.json` through a protected maintenance PR,
   update the README acceptance link and check the deployed catalog.

The catalog displays the scoped published decision as `accepted_historical`.
It remains a record for its accepted revisions when current inputs change and
never grants current machine success. Award eligibility, priority, recipients
and amounts remain separate decisions.

See the [complete candidate lifecycle](docs/candidate-lifecycle.md) for the DGG
example and archive details, [the contributor guide](CONTRIBUTING.md) for submission
requirements, and [intake operations](docs/simplified-intake.md) for recovery and deployment.

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
