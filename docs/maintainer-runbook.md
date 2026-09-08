# Maintainer runbook

## Initial repository settings

Maintainers should verify these settings on GitHub:

- Default branch: `main`; disallow force pushes and deletion of protected branches.
- Require `registry` and `tests` to pass before merging, including for administrators. Required approvals are currently 0 and CODEOWNERS review is optional; authors with merge permission may merge their own PRs after required CI passes.
- Apply repository approval rules to workflows from external contributors; do not provide secrets or write tokens to forks.
- Give Actions read-only tokens by default; do not allow Actions to create or approve PRs automatically.
- Enable private vulnerability reporting. Do not store payment keys or internal materials in this repository.

CODEOWNERS initially assigns `@Federico2014` code maintenance responsibility, not mathematical review qualifications. Approve the mathematical reviewer roster separately. GitHub does not allow authors to Approve their own PRs; removing mandatory code approval allows self-merging. Formal acceptance still requires independent mathematical review, which self-merging cannot replace.

## Routine registration

1. Read the issue and confirm that materials may be public and that the original problem and result scope are clear.
2. Establish an official statement for a new problem, or reuse the same existing version.
3. Review registration and adapter PRs, confirming all targets, fixed sources, and attribution.
4. After merging, select Actions → Verification preflight → Run workflow, using `main` and the registered `submission_id`.
5. Read the failure reasons and temporary `verification-plan` artifact. A nonzero preflight exit is expected while the backend is unavailable; do not manually turn it into success.

This workflow currently performs preflight only. It cannot verify Lean proofs yet; see the [implementation checklist](implementation-status.md).

## Policy and security updates

Update Actions, Python dependencies, and future checkers through PRs with fixed versions. Run relevant negative regression cases after updates. Preserve old records; when security policy changes invalidate them, show "recheck required" without rewriting historical facts.

GitHub usernames in review records serve only as references. Before approval, verify actual PR reviews, signed materials, conflicts of interest, and independence. Field validation cannot replace that process.

## Future formal publishing requirements

Formal publishing is not implemented. Do not add a privileged `workflow_run` that consumes untrusted artifacts and executes scripts. Publishing must validate the trusted run origin and input digest and verify archive readback before displaying acceptance status. Actions artifacts are temporary storage and do not meet formal archival requirements.
