# Implementation status

The repository implements the trusted-workspace and reusable-environment architecture.
Current registrations and machine results are listed in the
[generated candidate catalog](../README.md#registered-candidates). Changed inputs
or verifier revisions require fresh evidence.

## Implemented

- Four-stage `candidate submit/prepare/verify/publish` CLI with shared non-authorizing progress in CI evidence and the catalog.
- Candidate-only submission PR creation and normal exact-head merge; generated README and acceptance-index updates use separate protected maintenance PRs.
- Explicit administrator publication validates current protected run/artifact provenance, verifies sealed evidence, and reads back Git/archive assets before immutable release publication; retries reuse matching drafts.
- Revalidation directly calls the shared Pages publisher after proof completion. Scheduled publication remains recovery; title/body edits no longer restart PR verification.

- Strict registration schemas, all-target coverage, file hashes and mathematical review binding.
- Static environment discovery: read toolchain/configuration/lock files without executing Lake.
- Reusable environment descriptors, pinned dependency workspaces, onboarding status and configurable resource budgets.
- Explicit upstream subdirectory/source mapping and hash-bound local Lean proof bridges.
- Trusted-base planning, bounded two-job candidate matrix, separate status publication and current-head/base checks. Automatic PR entry distinguishes GitHub default-branch event context from the checked-out protected target; legacy default-branch publishers bind the original event target.
- Existing Comparator export comparison and Lean/Nanoda replay, adapted for environment-selected compilers/exporters.
- Offline non-root execution, read-only trusted inputs and dependency images, seccomp, resource limits and runtime probes.
- Diagnostic machine execution while a registered workspace review is pending; final merge remains blocked.
- Input snapshots, per-stage logs/durations, immutable image identity, environment digest and version bindings.
- Required target-module source checks and clean-checker declaration coverage/axiom audits for every registered upstream target, including declarations silently omitted by the exporter.
- Explicit unsupported/infrastructure failure categories and bound failure reports even when source retrieval fails.
- English per-candidate reports and interrupted-stage metadata; static environment discovery rejects ambiguous dynamic configuration and incomplete direct dependency locks as automatic matches.
- Content-addressed evidence ZIPs with complete inventory and readback checks, plus temporary Actions artifact transport.
- Real proof/sandbox regression workflow including multi-file bridges and a separate Mathlib onboarding configuration.
- Automatic candidate preparation and static environment draft generation with explicit unresolved fields and no automatic approvals.
- Hash-bound source renaming and exact replacements, with original/adapted source evidence and protected-path checks.
- Environment regression matrices select affected profiles for environment-only PRs, all profiles for shared changes, and an optional exact ID for manual dispatch; pending descriptors and offline cache import probes remain included.
- Protected-default-branch revalidation of registered candidates after trusted input changes, separate from PR status publication.
- A versioned verification-result summary and explicit failed-stage diagnostics.

## Activation boundaries

- The existing core/Std environment retains its [prior onboarding evidence](backend-onboarding.md).
- `lean-4-28-mathlib` is admitted with [real onboarding evidence](workspace-onboarding.md). Its initial cache scope is deliberately limited to `Mathlib.Data.Nat.Basic`; it is not a claim of support for every Mathlib module or any particular candidate.
- `lean-4-32-rc1-mathlib` is admitted using [backend run 34452461091](https://github.com/Federico2014/math-lean-verification/actions/runs/34452461091) at verifier revision `397559f4257cb9f891df6ff17413f52415d12ef7`: all 29 real regressions passed, including positive/negative proofs, independent replay, sandbox protection and both declared cache import probes. Approval preserves the tested compiler, exporter, fixed dependencies, cache scope and resource limits (6 GiB RAM, 2 CPUs, 2 GiB work storage, 3600-second timeout). This is environment compatibility evidence. The registered DGG statement is approved under the [exact administrator exception](administrator-approvals/dgg-cost-v1-2026-09-10.md); independent mathematical review remains incomplete. Candidate proof status must come from fresh CI evidence for the current inputs.
- Project compiler, exporter and shared checker compatibility must pass actual tests for each new combination. Adding JSON is not approval.
- Mathematical reviewer accreditation remains empty. Existing two-reviewer, provenance and content-binding requirements are unchanged.
- Automatic formal acceptance remains disabled (`formal_acceptance_enabled: false`). The DGG administrator acceptance is published as an immutable Release with a Git backup and recorded readback checks; see `acceptance-publications.json`. This scoped manual publication does not activate automatic acceptance.
- Real candidate pilot onboarding, contribution/priority review and award decisions remain separate work.
- Unsupported custom Lake execution, dependency subdirectories, arbitrary native plugins and Lean 3 require an explicit backend extension. No automatic unsandboxed fallback exists.
- Peak resource telemetry, richer per-theorem diagnostic classifications and merge-queue support remain future improvements; execution limits, wall time and aggregate target checks are recorded now.
- Revalidation conservatively selects all registered candidates, up to the 256-job matrix limit; larger registries currently require selecting individual submissions. Dependency-based incremental revalidation remains an optimization.

## Validation

The [workspace onboarding run](workspace-onboarding.md) passed both real backend matrices (27 cases total) and 69 unit tests.

Those historical runs do not validate later generic-intake changes. The expanded
backend matrix includes adapted Challenge positive/negative cases and cache import
probes; inspect a run of the current revision before admitting changed environments.

Run unit tests and registry validation locally. The **Lean backend tests** workflow builds real environment images and runs positive/negative proofs; inspect its actual run before approving a new environment. Synthetic test success is infrastructure evidence, not verification of an award candidate.

See [the design](design.md), [the candidate process](../CONTRIBUTING.md) and [the merge gate](lean-merge-gate.md).

See the [2026-09-09 conformance review](design-conformance-review.md) for requirement coverage, remaining rollout gaps and focused corrective changes.

## Single-PR intake implementation

Implemented candidate schemas/templates, static hash-bound preparation, protected
exception mappings, automatic import closure/bridging, current-protected-target PR delta
application, target-branch recovery, stale-status suppression and a generated
Pages candidate catalog. See [operations and deployment](simplified-intake.md).
No existing approved environment, reviewer policy or candidate is changed by this
implementation. Real backend tests now exercise the generated constant-type bridge.

Production activation requires merging this implementation, enabling GitHub Pages,
and recording actual recovery/merge/catalog event-chain evidence. Local orchestration
tests do not satisfy that acceptance requirement. Formal acceptance remains disabled.

## Default-branch catalog and published administrator decisions

Catalog publication and candidate revalidation follow the current protected default
branch (`main` or `develop`) and reject stale revisions, unprotected branches and
foreign workflow evidence. The catalog links pinned immutable administrator
acceptance releases as historical decisions, separately from current machine
verification. The DGG acceptance is indexed in `acceptance-publications.json`; its
archive remains independent of the automatic acceptance policy.
