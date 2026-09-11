# Four-stage candidate workflow

The CLI, CI summaries, candidate catalog and publication tooling share four stages:
submit, prepare, verify, and publish. New PRs currently target protected `develop`.
The commands use Python 3.12 and the installed development dependencies. Network
writes use the operator's authenticated `gh` session; they never run in candidate
containers or receive credentials from proof jobs.

## 1. Submit materials and open a PR

Fill [candidate.json](../templates/candidate.json), then run:

```bash
python -m verifier candidate submit my-candidate /path/to/candidate.json --repository OWNER/REPO
```

This validates the ID, fixed source commit, targets, attribution and public-source
permission before writing. It creates a commit containing only the candidate JSON
and optional bridge, then opens a PR on an isolated branch. It does not execute Git
hooks, Lean, Lake or plugins. Add `--bridge /path/to/Bridge.lean` for a declared
bridge and `--dry-run` for a read-only preview. Repeat submissions reuse an existing
open PR for the same base and materials, after checking that its files still match.
Already registered IDs are rejected by the submission shortcut; use an explicit
reviewed update/version-change PR for existing candidates.

The operator needs repository write access. A contributor without it may create a
fork PR through GitHub's UI; all candidate-only scope and verification rules still
apply. An Issue and local Lean installation are optional.

## 2. Clear prerequisites

Trusted CI automatically prepares each candidate. To inspect a candidate already
present in a local checkout:

```bash
python -m verifier candidate prepare my-candidate
```

This reads bounded source metadata and shows preparation blockers and the next
stage; exit code `3` signals non-executing diagnostics. Missing problem review,
environment approval or adaptation remains non-passing. Maintainers prepare
trusted configuration in separate maintenance PRs. Keep the candidate PR open;
the scheduler resumes it against the updated protected base without an empty commit.

Normal statement review requires two accredited independent reviewers. The roster
is currently empty. An explicitly authorized administrator exception must bind
one problem, statement version and digest through protected policy and approval
changes. It does not grant independent-review accreditation or formal acceptance.
See [statement review](statement-review.md) and [environment onboarding](environment-onboarding.md).

## 3. Verify the proof

Ready candidates run automatically. For an explicit retry:

```bash
python -m verifier candidate verify --pr 123 --repository OWNER/REPO
```

The command dispatches the existing protected gate with the exact PR head and
current protected target revision. Candidate builds stay in credential-free,
offline containers. All targets, bridges, statements, axioms, Lean and Nanoda replay
must pass. Inspect `lean-plan-*`, `lean-evidence-*`, `report.md`,
`verification-result.json` and the four-stage `workflow.json` summary.

Require `registry`, `tests` and `lean-verification`. Static validation, environment
tests and documentation-only passes do not verify a candidate. New source/base
bindings require fresh evidence. PR title/body edits do not change those inputs
and no longer restart verification; retargeting still does.

## 4. Merge, publish and accept

Publish a verified candidate with:

```bash
python -m verifier candidate publish my-candidate --pr 123 --repository OWNER/REPO
```

The command checks that the PR contains only this candidate's files and is
mergeable under normal branch protection. It merges the exact head, loads the
current protected registry and opens a maintenance PR containing the generated
README summary. By default it waits up to five minutes and merges that exact
generated head only when normal checks/review permit it. Use `--wait-seconds 0` to
return immediately, or rerun after a pending review/check completes. This keeps protected
publication data out of candidate-controlled changes. Rerunning reuses the open
publication PR or confirms synchronization. Omit `--pr` for an already merged candidate.

Each protected default-branch push starts revalidation. On completion, the workflow
calls the shared catalog publisher directly; failed/blocked proof outcomes remain
visible. The scheduled publisher provides recovery. No privileged `workflow_run`
or candidate-artifact reader is added to Pages publication.

The README's marked table is generated from candidate metadata and the protected
acceptance index. Live verification links avoid committing volatile proof status
or creating publication/revalidation loops. Registry CI uploads a preview; the
publication command creates the actual protected README change. For a local
maintenance preview, run:

```bash
python -m verifier sync-readme --repository OWNER/REPO --output /tmp/README.preview.md
```

Only the content between the registration markers is replaced; surrounding prose
and local notes are preserved. Immutable acceptance references are verified through
the GitHub API before any accepted label is rendered, including CI previews. Without
`--output`, the command updates local README.

### Explicit administrator acceptance

Automatic formal acceptance remains disabled in machine policy. After a deliberate
administrator decision, fill [the approval template](../templates/administrator-acceptance.json)
and run:

```bash
python -m verifier candidate publish my-candidate --approval /path/to/approval.json --repository OWNER/REPO
```

The approval must say `decision: accepted` and bind the administrator, date, reason,
source commit, statement digest, current verifier SHA, successful revalidation run
and attempt, GitHub artifact ID, and sealed archive SHA-256. Obtain these from the
trusted run's plan/result and sealed evidence inventory. Supplying this file is an
explicit publication instruction by the authenticated administrator; a candidate
cannot approve itself through a PR or fabricated report.

The command performs the mechanical publication work together:

- Checks authenticated administrator authority and repository release immutability.
- Validates protected workflow/run/job/attempt identities and actual proof execution.
- Downloads the exact GitHub artifact, verifies its digest and sealed inventory,
  and checks complete proof stages, source, statement and result bindings.
- Creates an archive Git commit and a draft release containing the unchanged sealed
  evidence, acceptance record and checksums. Reads both copies back before publishing.
- Publishes immutably, repeats asset readback, then generates the protected
  acceptance-index and README changes in one maintenance PR.

No Actions artifacts are executed or extracted onto the host. The command bounds
API transport to 128 MiB and both outer and sealed archives' uncompressed contents to 64 MiB; larger
archives need a separately reviewed publication path. Keep release assets and the
Git archive indefinitely. Verify checksums after migrations and at least annually;
both copies share GitHub as their storage provider.

A failed upload or readback leaves the release in draft. Rerun with the same
approval to reuse and check existing assets; mismatching or unexpected assets stop
publication. Never replace an immutable record. A changed current verifier revision
requires freshly reviewed evidence for a new decision. An acceptance already
published by this command can be resumed without reissuing it.

For existing immutable administrator decisions, use:

```bash
python -m verifier candidate publish my-candidate --release-tag ACCEPTANCE-TAG --repository OWNER/REPO
```

This imports and checks the published record, administrator, tag commit and asset
checksum. Statement identity must match explicit registered IDs or a protected
correspondence mapping bound to the exact candidate digest; an inline description
alone cannot establish correspondence. It does not create a new approval. A different existing index entry is
not overwritten; corrections/version changes require a separate reviewed change.

Registration may complete with formal acceptance pending. A published decision is
`accepted_historical` for its accepted inputs, not a current proof pass or two-person
independent review. Award eligibility, priority, recipients and amounts remain separate.

## DGG example

[DGG's registration](../candidates/dgg-cost-jyh.json) targets a rational
counterexample to the Goemans cost conjecture, statement `dgg-cost/v1`, from
[jyh/dinitz-verify at ffba3523f0ed](https://github.com/jyh/dinitz-verify/tree/ffba3523f0edd14be3460d039f22a6b98c02fd9e).
It does not claim to refute the separate Dinitz-Garg-Goemans congestion theorem.

[Run 34560237399, attempt 1](https://github.com/Federico2014/math-lean-verification/actions/runs/34560237399/attempts/1)
passed at verifier revision `ab95172eade9ee9036b26db460d696eb901efc46`.
The [administrator acceptance published on 2026-09-11](https://github.com/Federico2014/math-lean-verification/releases/tag/acceptance-dgg-cost-v1-20260911)
binds its own earlier verification revision and archived evidence. These are
separate records, not a claim that the later run was the acceptance basis.
