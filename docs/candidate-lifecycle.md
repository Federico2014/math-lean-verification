# Candidate submission through acceptance

This guide describes the repository workflow as of 2026-09-11. New candidate PRs
currently target protected `develop`, which is also the default branch. Catalog
publication and post-merge verification follow the protected default branch.

## Roles and outcomes

| Stage | Responsible party | Completion evidence |
| --- | --- | --- |
| Submit materials | Contributor | One candidate PR with a fixed proof commit and complete attribution |
| Approve prerequisites | Maintainer and authorized reviewers | Protected official statement, correspondence approval and admitted environment |
| Verify the proof | Trusted CI | Exact candidate/head/base run with all proof stages passing and sealed evidence |
| Register the candidate | Maintainer | Candidate PR merged into the protected target branch |
| Publish current status | Trusted CI; maintainer for README | Default-branch revalidation and live catalog; README links recorded evidence |
| Publish formal acceptance | Authorized decision maker and archive maintainer | Explicit decision and durable, checked archive for fixed revisions |
| Decide any award | Separate award process | Separate decision; none of the preceding stages grants an award |

## 1. Prepare one candidate file

Copy [the template](../templates/candidate.json) to
`candidates/<candidate-id>.json`. Use a lowercase, hyphenated ID and English
registration descriptions. Preserve original names, source titles and notation.

Include:

- The title and existing `problem_id` (and statement version when applicable), or
  `problem: {"title": "…", "source_url": "https://…", "scope": "…"}` for a new problem.
- The public proof repository and full 40-character immutable source commit.
- Every target Lean module and theorem declaration.
- Proof authors, formalization authors, proof route, AI contribution and known assumptions.
- `public_source_authorized: true` only with permission to submit the public source.

For a project in a subdirectory, set `source.project_root`. If automatic statement
bridging is ambiguous, provide the reviewed mapping requested by the maintainer
or an explicit `proofs/<candidate-id>/Bridge.lean`, referenced by `bridge`.

An Issue, local Lean installation, precomputed hashes and README edits are not
submission requirements. Never run candidate Lean, Lake or plugins on the host.

## 2. Open a candidate PR against develop

Use one PR per candidate. Include the candidate JSON and any required proof bridge.
Do not put trusted problem, policy, environment or approval changes in that PR.

**Trusted Lean verification** automatically prepares a plan: it reads the fixed
source as data, matches an approved environment, selects source files, computes
hashes and prepares the internal registration and bridge. Static preparation alone
does not verify a proof.

## 3. Clear any prerequisites

| Plan/result | Required action |
| --- | --- |
| `needs_information` | Contributor completes or corrects the submitted materials. |
| `waiting_problem` / `waiting_review` | Maintainer prepares the official statement and obtains exact correspondence approval. |
| `waiting_environment` | Maintainer runs real backend compatibility and isolation tests, then approves the pinned environment. |
| `needs_adaptation` | Maintainer and contributor resolve the source layout, mapping or bridge requirements. |
| `infrastructure_error` | Maintainer investigates and retries the trusted workflow after repair. |
| `failed` | Inspect the stage evidence and correct the proof or integration failure before retrying. |

Official statements must describe the original problem's exact domain,
quantifiers, assumptions, definitions, conclusion and direction. Normal review
requires two accredited independent reviewers. The approved reviewer roster is
currently empty; do not infer completed independent review from a green PR.

An explicitly authorized administrator exception must bind one problem, statement
version and digest. Merge its protected policy grant before activating the
statement approval in a separate maintenance PR. It is neither independent review
nor a formal acceptance decision. Follow [statement review](statement-review.md)
and [environment onboarding](environment-onboarding.md).

Keep the candidate PR open while prerequisites are prepared. After protected
configuration changes merge into its target branch, the scheduler replans it
against the new base and dispatches ready work. An empty candidate commit is not
needed. Resolve actual merge conflicts normally.

## 4. Inspect the actual proof evidence

For a ready candidate, isolated CI builds the submitted sources, checks every
required target and bridge, compares the official statements, audits transitive
axioms, and performs Lean and Nanoda replay. It seals and uploads the evidence.

Inspect `lean-plan-*` and `lean-evidence-*`, including `report.md`,
`verification-result.json` and stage logs. Require all three PR checks:
`registry`, `tests` and `lean-verification`. Registry validation, unit tests,
environment builds and Markdown-only maintenance passes do not establish candidate
proof validity. The candidate itself needs a successful proof execution.

The result binds the candidate source, PR head, protected base, statement,
environment and policy. Changed bindings require fresh verification; a pass on
another revision or target branch is historical evidence.

## 5. Merge and publish registration

After required checks and applicable review are satisfied, a maintainer merges
the candidate PR. Verify GitHub says **Merged**: a PR that is merely **Closed**
without merging does not register its files on the target branch.

Every push to the protected default branch starts **Revalidate registered Lean
proofs**, including documentation pushes because the verifier revision changes.
**Publish registered candidates** publishes the live
[candidate catalog](https://Federico2014.github.io/math-lean-verification/).
Publication also runs on a 15-minute schedule, which GitHub may delay.

Check the catalog's branch revision, generation time, candidate ID, proof commit
and evidence link. Only a successful run for the current default-branch revision
can show current `verified`; older runs remain historical.

The [README summary](../README.md#registered-candidates) is maintained separately.
Add the candidate there with links to its registration, fixed source and recorded
verification; include formal acceptance only when a decision has actually been
published. Its cited run is a historical snapshot. The live catalog supplies the
current status.

## 6. Publish formal acceptance separately

Machine verification does not automatically publish formal acceptance. The
machine policy still has `formal_acceptance_enabled: false`; the automatic formal
acceptance pipeline is not enabled.

For an explicitly authorized, scoped administrator acceptance:

1. Record the administrator, explicit decision, date, review basis and limitations.
   Do not label it as two-person independent review.
2. Bind the decision to the exact problem/statement digest, source, verifier,
   environment/policy and successful run/attempt with its evidence.
3. Preserve the complete evidence and licenses in a durable archive with file
   checksums. Verify uploaded files by reading them back; temporary Actions
   artifacts alone are insufficient. Never overwrite immutable records.
4. Publish the immutable acceptance record and verify its release/tag, archive
   commit, author and acceptance-file checksum.
5. In a protected maintenance PR, add the pinned publication reference to
   `docs/acceptance-publications.json` and update the README acceptance link.
   Check the deployed catalog after publication.

The catalog validates the publication and displays `accepted_historical` for the
accepted revisions. That decision persists as a historical record when the branch
changes; it does not grant current machine success. Source or statement changes
need new verification and any necessary fresh approval. Awards remain separate.

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
