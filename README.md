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

[Open the automatically generated candidate list](https://Federico2014.github.io/math-lean-verification/).
After a candidate PR merges, protected-default-branch CI revalidates it and publishes the
current status, fixed proof commit and evidence link. The page displays its default-branch
revision and generation time. Publication runs after default-branch pushes and on a
15-minute schedule; GitHub may delay scheduled jobs. Contributors do not edit a
README table. Deployment needs the one-time [Pages setup](docs/simplified-intake.md#deployment).

## Adding a candidate

### 1. Fill in one candidate file

Copy [templates/candidate.json](templates/candidate.json) to
`candidates/<candidate-id>.json`; IDs use lowercase words separated by hyphens.
Use the GitHub web editor or your usual Git client. Provide:

- The registered `problem_id`, or a `problem` object containing `title`,
  `source_url` and `scope` for maintainer correspondence review.
- A public GitHub proof repository and full 40-character immutable commit.
- Every target Lean module and theorem declaration.
- Proof/formalization authors, proof route, AI contribution and known assumptions.
- `public_source_authorized: true` only when you have permission to submit the source.

Replace template placeholders. An Issue is optional. You do not need a local
Lean installation, environment ID, source hashes, generated registration or
README edit. Use `source.project_root` for a project in a subdirectory.

### 2. Open one PR per candidate against develop

Opening, updating or retargeting the PR automatically triggers **Trusted Lean verification**.
Both `develop` and `main` are supported protected targets; new work goes to `develop`.
CI reads the fixed source as data, matches approved environments, selects local
imports, prepares internal registration and generates a proof bridge when the
mapping is unambiguous. It then runs the real isolated Lean, statement comparison,
axiom and Nanoda checks. Only changed candidate files and optional bridge files
belong in this PR.

### 3. Follow the CI result

| Result | Next action |
| --- | --- |
| `needs_information` | Complete the missing candidate materials and update the PR. |
| `waiting_problem` / `waiting_review` | Maintainers prepare the official workspace and approved correspondence. |
| `waiting_environment` | Maintainers test and approve a compatible pinned environment. |
| `needs_adaptation` | Maintainers review the reported mapping/build requirements; provide an optional checked bridge if needed. |
| `infrastructure_error` | Retry the trusted workflow after resolving the source/service failure. |
| `failed` | Inspect proof evidence, correct the source/bridge and update the fixed commit. |
| `verified` | All machine checks and exact statement approval passed; the maintainer can merge after required repository checks. |

The plan artifact lists all preparation blockers. Maintainers merge preparation
and approval changes in separate PRs against the same target branch. Each target-branch
push automatically resumes waiting candidate PRs against its new revision while preserving their submitted head;
no empty commit or rebase is needed merely to pick up approved configuration.
Conflicting candidate edits still require normal conflict resolution. Manual recovery
is available on either branch; the periodic schedule runs on the default branch.
The published candidate catalog describes the current protected default branch (`main` or `develop`).

Read `lean-plan-*` / scheduler diagnostics for prerequisites, and
`lean-evidence-*` for `report.md`, `verification-result.json` and stage logs.
Published administrator acceptances are linked separately, with the accepted source
and verifier revisions. They remain historical decisions when current inputs change.
A green registry check, a build or environment test alone is not proof verification.
Maintainers require `registry`, `tests` and `lean-verification` before merging.
Formal acceptance and awards remain separate decisions.

See [the contributor guide](CONTRIBUTING.md) and
[implementation and operations](docs/simplified-intake.md) for details.

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
