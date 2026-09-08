# Trusted Lean merge gate

Candidate PRs require the stable `lean-verification` status. `registry` and `tests` remain additional requirements; their green badges do not establish proof validity.

## Execution

The protected-base workflow resolves the current PR, validates an execution plan, runs each affected candidate in an independent job (maximum two concurrent), and publishes from a separate status-only job. Candidate jobs have no write token or repository secrets. PR files are fetched as bounded data, never checked out and executed by the privileged controller.

For new submissions, the trusted problem supplies a workspace, allowed source paths, solution module and environment digest. The candidate supplies a fixed upstream commit, selected Lean sources and optional hash-bound bridges. The environment comes from protected configuration, not a candidate-specified shell command or image.

Each job builds/exports the official Challenge and solution separately, compares statements and axioms using pinned Comparator code, replays through Lean and Nanoda, and seals diagnostics with readback checks. Failures at any stage prevent a pass. Pending mathematical review can allow diagnostics for registered workspaces, but never candidate merging.

Legacy source-only registrations continue to require already-approved statements. New Mathlib and other environments require onboarding before their IDs enter the policy allowlist.

## Status semantics

- No affected candidates: maintenance result `not_applicable`, no proof claimed.
- All affected candidates verified under approved exact statements: merge gate success.
- Pending review, missing materials, unsupported environment, proof failure, cancelled/skipped required job, timeout, or archive sealing failure: non-passing.
- Changed PR head or base at publication: non-passing; rerun on current inputs.

Evidence includes actual machine/review fields, source hashes, tool and image identity, resource configuration, stage logs and bindings. The ZIP checksum proves integrity only. Actions artifacts expire, and formal award acceptance remains disabled until persistent archival and human review operations are ready.

## Rerun

A maintainer may dispatch **Trusted Lean verification** from `main`, providing an open PR number. This recomputes the trusted plan and checks the exact current inputs; it does not reuse a historical green badge.

See [environment onboarding](environment-onboarding.md) and [the full design](design.md).
