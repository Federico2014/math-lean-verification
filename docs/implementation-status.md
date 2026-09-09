# Implementation status

The repository implements the trusted-workspace and reusable-environment architecture. No real award candidates are added by the redesign, and no real candidate is claimed to have passed.

## Implemented

- Strict registration schemas, all-target coverage, file hashes and mathematical review binding.
- Static environment discovery: read toolchain/configuration/lock files without executing Lake.
- Reusable environment descriptors, pinned dependency workspaces, onboarding status and configurable resource budgets.
- Explicit upstream subdirectory/source mapping and hash-bound local Lean proof bridges.
- Trusted-base planning, bounded two-job candidate matrix, separate status publication and current-head/base checks.
- Existing Comparator export comparison and Lean/Nanoda replay, adapted for environment-selected compilers/exporters.
- Offline non-root execution, read-only trusted inputs and dependency images, seccomp, resource limits and runtime probes.
- Diagnostic machine execution while a registered workspace review is pending; final merge remains blocked.
- Input snapshots, per-stage logs/durations, immutable image identity, environment digest and version bindings.
- Required target-module source checks and clean-checker declaration coverage/axiom audits for every registered upstream target, including declarations silently omitted by the exporter.
- Explicit unsupported/infrastructure failure categories and bound failure reports even when source retrieval fails.
- English per-candidate reports and interrupted-stage metadata; static environment discovery rejects ambiguous dynamic configuration and incomplete direct dependency locks as automatic matches.
- Content-addressed evidence ZIPs with complete inventory and readback checks, plus temporary Actions artifact transport.
- Real proof/sandbox regression workflow including multi-file bridges and a separate Mathlib onboarding configuration.

## Activation boundaries

- The existing core/Std environment retains its [prior onboarding evidence](backend-onboarding.md).
- `lean-4-28-mathlib` is admitted with [real onboarding evidence](workspace-onboarding.md). Its initial cache scope is deliberately limited to `Mathlib.Data.Nat.Basic`; it is not a claim of support for every Mathlib module or any particular candidate.
- Project compiler, exporter and shared checker compatibility must pass actual tests for each new combination. Adding JSON is not approval.
- Mathematical reviewer accreditation remains empty. Existing two-reviewer, provenance and content-binding requirements are unchanged.
- Persistent evidence storage, backup/readback operations and formal acceptance publication remain unconfigured. `formal_acceptance_enabled` remains false.
- Real candidate pilot onboarding, contribution/priority review and award decisions remain separate work.
- Unsupported custom Lake execution, dependency subdirectories, arbitrary native plugins and Lean 3 require an explicit backend extension. No automatic unsandboxed fallback exists.
- Peak resource telemetry, richer per-theorem diagnostic classifications and merge-queue support remain future improvements; execution limits, wall time and aggregate target checks are recorded now.
- Automatic revalidation of existing candidates after global controller/policy changes remains unimplemented. The protected PR controller cannot validate its own replacement; a separate protected-base revalidation workflow is needed.

## Validation

The [workspace onboarding run](workspace-onboarding.md) passed both real backend matrices (27 cases total) and 69 unit tests.

Run unit tests and registry validation locally. The **Lean backend tests** workflow builds real environment images and runs positive/negative proofs; inspect its actual run before approving a new environment. Synthetic test success is infrastructure evidence, not verification of an award candidate.

See [the design](design.md), [the candidate process](../CONTRIBUTING.md) and [the merge gate](lean-merge-gate.md).

See the [2026-09-09 conformance review](design-conformance-review.md) for requirement coverage, remaining rollout gaps and focused corrective changes.
