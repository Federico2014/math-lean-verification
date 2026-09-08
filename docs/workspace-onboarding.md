# Trusted-workspace backend onboarding

## Evidence

[GitHub run 34230107878](https://github.com/Federico2014/math-lean-verification/actions/runs/34230107878), at implementation commit `f6850defaa4a23ab89736adea620f30f0257878d`, clean-built both environment images on GitHub-hosted Ubuntu 24.04 and passed all actual proof/sandbox regressions:

| Environment | Cases | Positive coverage |
| --- | --- | --- |
| `lean-4-34-rc2-stdlib` | 13 | Core/Std proof, irrelevant unused placeholder, multi-file bridge with a differently named upstream declaration |
| `lean-4-28-mathlib` | 14 | The same cases plus `Function.Injective Nat.succ` proved with the pinned Mathlib theorem `Nat.succ_injective` |

Every positive case reached Comparator statement/axiom checks, the official Lean kernel and independent Nanoda replay. Negative cases covered direct/indirect placeholders, extra axioms, wrong statements, extra premises, changed definitions, missing targets, forged output, unchecked kernel declarations and protected writes. The test harness requires the appropriate build/export stages to have completed before accepting a rejection, so an always-failing environment cannot pass onboarding.

The run artifacts are named `backend-test-evidence-lean-4-34-rc2-stdlib` and `backend-test-evidence-lean-4-28-mathlib`. They contain the full environment descriptor, image ID, checker manifests/checksums, sandbox policy hash, exports, per-stage logs and result summary. They are temporary reproducible infrastructure evidence, not permanent award archives.

The registry workflow for the same commit passed 69 unit tests, including protected-workspace/overlay tampering, environment matching across different project names, pending-review diagnostics, all-matrix-job aggregation, stale-base rejection, and evidence checksum tampering. The archive seal/readback CLI was additionally run against the successful stdlib artifact, not only a synthetic JSON fixture.

## Admitted scope

The shared checker uses the Comparator, exporter and Nanoda pins in [the tool manifest](../backend/toolchain.json). The project compiler/exporter are selected independently by each [environment descriptor](../environments/). Compatibility has been demonstrated for these exact combinations, not every Lean version.

`lean-4-28-mathlib` fixes Lean 4.28.0 (official release archive SHA-256 `ceb3a3f844f7aebf63245e2b51c28d5b0ed38942c19f93cf3febd520302160bd`), exporter commit `d065b0009aed0520e9e99752847a33b337661690`, Mathlib commit `8f9d9cff6bd728b17a24e163c9402775d9e6a365` and every transitive dependency in its lock. Its cache scope is `Mathlib.Data.Nat.Basic` and that module's dependency closure. It does not admit arbitrary Mathlib modules, custom Lake programs or all prize candidates.

The dependency cache is an explicit trust assumption. Sources, Git commits and manifests are checked during image preparation; the complete immutable image ID is recorded. ProofWidgets release-tag metadata is fetched without moving its pinned checkout. Exact-path Git safe-directory entries allow non-root metadata reads from root-owned immutable dependencies; candidate inputs are never added to that trust list.

Runtime uses 2 CPUs, 6 GiB memory for this Mathlib profile, a 2 GiB private workspace, read-only input/dependency images, no network, non-root execution, explicit seccomp and privilege restrictions. Core/Std keeps its previous limits. These are tested budgets for the fixture scope, not measurements of all future candidates or a guaranteed capacity estimate.

Approval changes the descriptor digest; new problem workspaces must bind the approved descriptor. Later compiler, dependency, cache scope, checker or sandbox changes require fresh evidence and review. No candidate or reviewer is approved by this record, and formal award acceptance remains disabled.
