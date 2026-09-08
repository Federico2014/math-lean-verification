# Lean proof verification before merge

The required `lean-verification` commit status is separate from `registry` and `tests`. For a candidate registration or changed proof, it succeeds only after prerequisites, a clean isolated build/export, trusted statement comparison, transitive axiom auditing, Lean kernel replay, and independent Nanoda replay all succeed. A documentation-only PR receives an explicit "No candidate proof changes" result, not a proof-passed claim.

## Trust and execution

`lean-verification.yml` uses `pull_request_target` only to run protected-base controller code. It never checks out or executes PR code on the runner. The PR tree is obtained through bounded GitHub API responses and parsed as registry data. The execution job has read-only permissions. Separate jobs publish pending/final statuses for the exact PR head, using only the trusted execution job's result and a fixed status enum; they never consume proof artifacts or run candidate programs.

Fork PRs cannot provide their own policy, schemas, trusted Challenge, verifier, tool image, or status verdict. Workflow changes in a PR take effect only after maintainer review and merging. The required status is restricted to the GitHub Actions integration; branch protection applies to administrators. Repository write/admin access remains a trusted role and can change the verification infrastructure through reviewed PRs.

Each build/export and each checker runs in a fresh non-root Docker container with no network, a read-only root filesystem, all capabilities dropped, no privilege escalation, a pinned explicit Docker seccomp profile, bounded CPU/memory/process/file/output/time resources, read-only inputs, and disposable writable scratch space. No Docker socket, host credentials, `.git`, Actions command files, or writable verifier files are mounted. Runtime probes check the actual identity, read-only boundaries, lack of external networking, absence of credentials and host sockets, active capability/seccomp restrictions, and effective cgroup limits. A probe failure aborts verification.

The trusted Challenge is built and exported separately from the candidate. Only bounded exported data crosses into the trusted comparison/replay stage; candidate-generated olean files never enter a checker or publishing host. Comparator's statement/dependency comparison, axiom audit, primitive checks, and official kernel replay are reused at a pinned source revision. Nanoda runs separately with unpermitted axioms configured as hard errors. The integration uses Docker isolation and the export-checking path, not Comparator's Landrun build launcher or its insecure development shim.

## Currently supported proof profile

The execution profile `lean-4-34-rc2-stdlib` supports source-only Lean core/Std projects, one target module, and any declared required theorems in that module. The candidate and official declarations must have the same names. A different encoding or name requires a reviewed bridge before onboarding. Arbitrary upstream Lake programs, plugins, precompiled files, Mathlib projects, and custom build/dependency configurations are not supported by this profile and cannot pass by falling back to a weaker check.

Pinned tool sources, release checksum, and container bases are recorded under `backend/`. The official Lean release supplies the compiler and trusted core/Std library artifacts; this bootstrap trust is explicit. Candidate source is rebuilt cleanly, and submitter caches are not accepted. Operating-system package versions and tool binary hashes are recorded in each execution's evidence. The runtime uses the immutable local image ID produced from the protected recipe.

An executable profile is not automatically an approved candidate toolchain. Adding it to `policy/verification.json` requires onboarding evidence and maintainer review. The approved toolchain and independent-reviewer lists remain empty until that review is performed. No award or formal-acceptance flag is enabled by this merge gate.

## Candidate process

1. Submit the intake issue with original sources, exact scope, fixed proof commit, all targets, environment, and attribution.
2. Prepare and independently review the official problem statement in a separate problem PR. The approved statement, source snapshots, review evidence, and toolchain must already be on `main` before a candidate can pass.
3. Submit the candidate registration PR referencing that exact approved statement. Candidate PRs cannot modify their own trusted statement, policy, or approval record.
4. The gate validates prerequisites, fetches only fixed source files for the supported profile, and runs the actual proof checks. Every required target must pass.
5. Merge only after `registry`, `tests`, and `lean-verification` succeed. New commits invalidate the old head's status and trigger verification again.

The existing Erdős #650 registration cannot pass yet: its official statement is new/pending, its declared Lean/Mathlib environment has no approved backend profile, and its mapping still needs bridges. A failing gate in that PR is the expected protection, not an infrastructure test failure to suppress.

## Evidence and formal acceptance

The workflow uploads bounded exports, stage results, source/input digests, verifier and candidate commits, tool versions, binary checksums, and the immutable image ID as temporary diagnostics. These artifacts have a 30-day retention and do not satisfy durable prize evidence archival. A machine pass does not determine priority, recipient identity, independence scoring, prize amount, or formal award acceptance. The separate formal-acceptance path remains disabled until durable archives and the remaining policy requirements are met.

## Backend regression tests

`python scripts/backend_smoke.py --image <immutable-image-id> --output <new-directory>` runs real Lean proof cases. It must accept a valid proof and a proof with an unrelated unused sorry, while rejecting direct/indirect sorry, extra axioms, changed targets, extra premises, altered definitions, missing targets, forged success output, unchecked kernel declarations, and protected-file writes. All positive cases must reach both independent kernel stages. A suite where every case fails is not a passing backend.

After the workflow is installed on `main`, maintainers can rerun any open PR with **Trusted Lean verification → Run workflow → pr**. `workflow_dispatch` is restricted to `main`. Missing prerequisites, backend errors, timeouts, failed probes, unsupported profiles, and failed checkers produce non-success statuses. Never manually post a success status to unblock a candidate.

GitHub requires both a check run and a commit status if they share a required name; an unrelated fork check cannot replace this protected workflow's status. See [GitHub required-check semantics](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks).
