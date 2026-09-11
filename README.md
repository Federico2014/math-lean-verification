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

The workflow has four steps. New candidate PRs currently target protected
`develop`, which is also the default branch.

| Step | Responsible party | Completion condition |
| --- | --- | --- |
| 1. Prepare materials and open a PR | Contributor | Submit one complete candidate JSON and any required bridge in a PR against `develop`. |
| 2. Clear prerequisites | Maintainer and authorized reviewers | Approve the exact official statement, correspondence, environment and any adaptation. |
| 3. Verify the proof | Trusted CI | Complete actual isolated proof checks, preserve evidence and pass all required PR checks. |
| 4. Merge, publish and accept | Maintainer, CI and authorized decision maker | Merge the candidate, publish its registration and current verification status, then publish formal acceptance when separately authorized and durably archived. |

### 1. Prepare materials and open a PR

Copy [templates/candidate.json](templates/candidate.json) to
`candidates/<candidate-id>.json`; IDs use lowercase words separated by hyphens.
Provide:

- The registered `problem_id`, or a `problem` object containing `title`,
  `source_url` and `scope` for maintainer correspondence review.
- A public GitHub proof repository and full 40-character immutable commit.
- Every target Lean module and theorem declaration.
- Proof/formalization authors, proof route, AI contribution and known assumptions.
- `public_source_authorized: true` only when you have permission to submit the source.

Open one PR per candidate against `develop`, containing only the candidate file
and any required proof bridge. Use `source.project_root` for a project in a
subdirectory. An Issue, local Lean installation, generated hashes and README edits
are not submission requirements. Never execute candidate Lean, Lake or plugins on
the host.

Opening, updating or retargeting the PR triggers **Trusted Lean verification**.
CI reads the fixed source as data and prepares the environment selection,
registration and bridge. Preparation alone does not verify a proof.

### 2. Clear prerequisites

| Result | Next action |
| --- | --- |
| `needs_information` | Contributor completes the missing materials. |
| `waiting_problem` / `waiting_review` | Maintainers prepare the official workspace and approve statement correspondence. |
| `waiting_environment` | Maintainers run real backend tests and approve the pinned environment. |
| `needs_adaptation` | Resolve the source layout, mapping or bridge requirements. |
| `infrastructure_error` | Repair the infrastructure or source/service issue and retry. |
| `failed` | Inspect proof evidence and correct the proof or integration failure before retrying. |
| `verified` | Check the evidence and merge requirements below. |

Keep the candidate PR open while maintainers prepare trusted problem, environment,
policy and approval changes in separate PRs against the same target branch. Once
those changes merge, the scheduler replans and resumes ready candidates against
the new base. No empty candidate commit is needed; resolve actual merge conflicts
normally.

Normal statement review requires two accredited independent reviewers. An
explicitly authorized administrator exception must bind the exact problem,
statement version and digest through protected policy and approval changes.
It is separate from formal acceptance and must not be labeled independent review.
See [statement review](docs/statement-review.md).

### 3. Verify the proof

Trusted CI performs isolated source builds, checks all required targets and
bridges, compares official statements, audits transitive axioms, and runs Lean and
Nanoda replay. It seals and uploads the evidence.

Inspect `lean-plan-*` and `lean-evidence-*`, including `report.md`,
`verification-result.json` and stage logs. Require `registry`, `tests` and
`lean-verification` to pass and confirm actual candidate proof execution. A green
registry check, unit test, environment build or Markdown-only maintenance check
alone is not proof verification. Changed inputs or protected base revisions
require fresh verification; previous runs remain historical evidence.

### 4. Merge, publish and accept

**Merge.** After required checks and applicable review pass, a maintainer merges
the PR. Confirm it is **Merged**: closing an unmerged PR does not register its files.

**Publish.** Every protected default-branch push starts **Revalidate registered
Lean proofs**, including documentation pushes. **Publish registered candidates**
updates the [live catalog](https://Federico2014.github.io/math-lean-verification/).
Publication also runs on a 15-minute schedule, which GitHub may delay. Check the
published revision, candidate ID, source commit and evidence; only a successful
run for the current default-branch revision can show current `verified`.
Maintainers add a [README entry](#registered-candidates) linking the registration,
fixed source and recorded verification. The live catalog supplies current status.

**Accept.** Formal acceptance requires a separate authorized decision and durable
evidence; merging or passing CI does not grant it. Automatic formal acceptance
remains disabled (`formal_acceptance_enabled: false`). For an explicitly authorized
administrator acceptance, record the administrator, decision, date, review basis
and limitations; bind it to the exact statement, source, verifier,
environment/policy and successful run/attempt. Preserve the evidence and licenses
in an immutable archive, verify file checksums by reading uploaded files back,
and publish the acceptance record. Temporary Actions artifacts alone are insufficient.
Add its pinned reference to `docs/acceptance-publications.json` through a protected
maintenance PR, update the README acceptance link and verify catalog publication.

Registration may be published while formal acceptance is pending. A scoped
administrator decision is labeled administrator acceptance, never two-person
independent review. The catalog shows it as `accepted_historical` for the accepted
revisions; it does not grant current machine success. Award decisions remain separate.

See the [detailed candidate lifecycle](docs/candidate-lifecycle.md) for the DGG
example and archive requirements, [the contributor guide](CONTRIBUTING.md) for
submission details, and [intake operations](docs/simplified-intake.md) for recovery
and deployment.

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
