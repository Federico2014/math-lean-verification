# Maintainer runbook

## Initial repository settings

Maintainers should verify these settings on GitHub:

- Default branch: `main`; disallow force pushes and deletion of protected branches.
- Require `registry`, `tests`, and the GitHub Actions `lean-verification` status to pass before merging, including for administrators. Required approvals are currently 0 and CODEOWNERS review is optional; authors with merge permission may merge their own PRs after required CI passes.
- Apply repository approval rules to workflows from external contributors; do not provide secrets or write tokens to forks.
- Give Actions read-only tokens by default; do not allow Actions to create or approve PRs automatically.
- Enable private vulnerability reporting. Do not store payment keys or internal materials in this repository.

CODEOWNERS initially assigns `@Federico2014` code maintenance responsibility, not mathematical review qualifications. Approve the mathematical reviewer roster separately. GitHub does not allow authors to Approve their own PRs; removing mandatory code approval allows self-merging. Formal acceptance still requires independent mathematical review, which self-merging cannot replace.

For the trusted status workflow, isolation boundaries, supported profiles, and manual reruns, see the [Lean merge gate](lean-merge-gate.md).

## Routine registration

1. Review `candidates/<candidate-id>.json` in the candidate PR; an Issue is optional. Confirm publication permission, original problem scope, fixed proof commit, targets and attribution.
2. Inspect the automatically triggered **Trusted Lean verification** plan and evidence. Resolve missing official workspaces, statement reviews or environments in separate maintenance PRs.
3. Run real backend compatibility tests before approving a new environment. Merging approved preparation changes lets the scheduler resume the original candidate PR against current main.
4. Merge the candidate only after `registry`, `tests` and `lean-verification` pass. A green environment build or static plan does not verify the candidate.
5. Check protected-main revalidation and the generated candidate catalog after merging. Retain the exact run and revision evidence; formal acceptance remains separate.

For recovery, manual retries and one-time Pages setup, see
[single-PR operations](simplified-intake.md). For local static diagnostics, use
`python -m verifier plan <candidate-id>`; it never executes a proof and exits `3`
after a valid plan.

## Policy and security updates

Update Actions, Python dependencies, and future checkers through PRs with fixed versions. Run relevant negative regression cases after updates. Preserve old records; when security policy changes invalidate them, show "recheck required" without rewriting historical facts.

GitHub usernames in review records serve only as references. Before approval, verify actual PR reviews, signed materials, conflicts of interest, and independence. Field validation cannot replace that process.

## Future formal publishing requirements

Formal publishing is not implemented. Do not add a privileged `workflow_run` that consumes untrusted artifacts and executes scripts. Publishing must validate the trusted run origin and input digest and verify archive readback before displaying acceptance status. Actions artifacts are temporary storage and do not meet formal archival requirements.
