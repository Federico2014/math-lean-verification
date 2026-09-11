# Maintainer runbook

## Initial repository settings

Maintainers should verify these settings on GitHub:

- Default branch: `develop` (as of 2026-09-11); disallow force pushes and deletion of protected branches.
- Require `registry`, `tests`, and the GitHub Actions `lean-verification` status to pass before merging, including for administrators. Required approvals are currently 0 and CODEOWNERS review is optional; authors with merge permission may merge their own PRs after required CI passes.
- Apply repository approval rules to workflows from external contributors; do not provide secrets or write tokens to forks.
- Give Actions read-only tokens by default; do not allow Actions to create or approve PRs automatically.
- Enable private vulnerability reporting. Do not store payment keys or internal materials in this repository.

CODEOWNERS initially assigns `@Federico2014` code maintenance responsibility, not mathematical review qualifications. Approve the mathematical reviewer roster separately. GitHub does not allow authors to Approve their own PRs; removing mandatory code approval allows self-merging. Self-merging does not complete independent mathematical review or authorize formal
acceptance. Explicit administrator exceptions and published administrator decisions
retain their separate, limited scope; see the [candidate lifecycle](candidate-lifecycle.md).

For the trusted status workflow, isolation boundaries, supported profiles, and manual reruns, see the [Lean merge gate](lean-merge-gate.md).

## Routine registration

Follow the [complete candidate lifecycle](candidate-lifecycle.md) for roles, waiting
states, README publication and scoped administrator acceptance.

1. **Submit:** review the candidate-only PR created by `candidate submit` or GitHub's UI.
2. **Prepare:** use CI diagnostics or `candidate prepare`; merge trusted statement,
   mapping and environment approvals separately. Run real backend tests for onboarding.
3. **Verify:** inspect actual candidate proof stages and require `registry`, `tests`
   and `lean-verification` to pass. Retry with `candidate verify` when appropriate.
4. **Publish:** run `candidate publish` to merge the candidate and generate its README
   publication PR. Revalidation calls the shared catalog publisher on completion.
   After explicit administrator approval, use `--approval` to archive, read back and
   publish the immutable decision and generate the acceptance-index/README PR.
   The command waits for normal required checks/review and merges only its generated head; rerun if still pending.

For recovery, manual retries and one-time Pages setup, see
[single-PR operations](simplified-intake.md). For local static diagnostics, use
`python -m verifier plan <candidate-id>`; it never executes a proof and exits `3`
after a valid plan.

## Policy and security updates

Update Actions, Python dependencies, and future checkers through PRs with fixed versions. Run relevant negative regression cases after updates. Preserve old records; when security policy changes invalidate them, show "recheck required" without rewriting historical facts.

GitHub usernames in review records serve only as references. Before approval, verify actual PR reviews, signed materials, conflicts of interest, and independence. Field validation cannot replace that process.

## Formal publishing requirements

Automatic formal acceptance remains disabled. Scoped administrator decisions may
be published as immutable archives and linked by the protected publication index,
as described in the [candidate lifecycle](candidate-lifecycle.md#4-merge-publish-and-accept). Do not add a privileged `workflow_run` that consumes untrusted artifacts and executes scripts. Publishing must validate the trusted run origin and input digest and verify archive readback before displaying acceptance status. Actions artifacts are temporary storage and do not meet formal archival requirements.
