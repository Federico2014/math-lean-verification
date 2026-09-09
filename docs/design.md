# Lean proof verification design

Version 1.1 — 2026-09-08. Implementation of the agreed trusted-workspace design.
See [implementation status](implementation-status.md) for tested capabilities and remaining activation requirements.

## Purpose and scope

Use GitHub Actions to verify fixed Lean proof projects against independently reviewed mathematical statements. A project is integrated once, then its PR updates run automatically. Different candidates can reuse an approved environment; a new dependency combination adds configuration, and special requirements need explicit adaptation.

This is not a promise that arbitrary Lean code works without integration. Missing dependencies, incompatible exporters/checkers, resource exhaustion and unsupported assumptions remain non-passing. CI does not decide originality, AI contribution, dates, prize amounts, recipient identity or award eligibility.

## Architecture

```text
Candidate issue
    |
Identify source, scope and all targets
    |
Review official problem        Identify and freeze environment
    |                          Reuse / version configuration / adaptation
    +--------------------------+
    |
Candidate PR: pinned source + selected files + optional proof bridge
    |
Protected-base planner -> independent candidate jobs (maximum two concurrent)
    |
Isolated build/export -> Comparator comparison + Lean replay -> Nanoda replay
    |
Exact-input result + evidence checksum/readback
    |
Trusted status publisher -> required lean-verification check
```

The workflow retains the proven export-only Comparator integration. `GateReplay.lean` is a small wrapper over pinned upstream comparison and kernel code; it does not implement a new proof checker. The upstream CLI's build launcher is replaced with separately probed Docker execution boundaries, avoiding untrusted `.olean` imports on the controller. This is an intentional integration choice, not a claim that running the stock Comparator CLI in any container is safe.

References: [Comparator](https://github.com/leanprover/comparator), [LeanEval](https://github.com/leanprover/lean-eval), [Lean validation guidance](https://lean-lang.org/doc/reference/latest/ValidatingProofs/).

## Three versioned objects

### Problems and trusted workspaces

`problems/<problem-id>/<version>/problem.json` binds the original sources, full claim, required official theorems, trusted Lean definitions and review evidence. `workspace` adds:

- `environment_digest`: canonical SHA-256 of the complete environment descriptor.
- `solution_module`: the module exposing the official theorem names, usually a small bridge.
- `submission_paths`: permitted candidate source locations. Patterns match path segments; `**` is recursive.

All trusted files are hashed. A candidate cannot overlay a trusted file or change its official problem in its own PR. Prepare new workspaces in separate maintenance PRs. Once used, prefer new statement versions and environment IDs over mutating the meaning of existing records.

Natural-language correspondence requires mathematical review of definitions, quantifiers, assumptions and the exact conclusion. Two distinct approved reviewers and exact statement hashes remain required by existing policy; GitHub merge permissions are separate from mathematical accreditation. No reviewers are automatically added by this implementation.

### Reusable environments

`environments/<environment-id>/environment.json` fixes the Lean release and archive SHA-256, exporter commit, dependency workspace hashes, cache mode, resource budgets, status and onboarding evidence. The shared checker image fixes Comparator and Nanoda versions independently of the project compiler; compatibility must be demonstrated, not inferred from version numbers.

| Situation | Action |
| --- | --- |
| Existing approved environment matches | Reference its ID and digest; no new CI workflow |
| Dependency/toolchain version differs | Add a pinned environment configuration; reuse the build/check implementation and run onboarding tests |
| Special libraries or unsupported build/check tools | Adapt the backend explicitly; keep unsupported until tested |
| Only directories or theorem names differ | Change candidate source mapping and bridge, normally not the environment |

`python -m verifier inspect-environment <project>` reads bounded local `lean-toolchain`, static Lake configuration and the dependency lock. It never executes Lake or fetches anything. Dynamic `lakefile.lean`, missing locks and unknown requirements need review. Suggested matches are not approvals.

Standard source projects use generated Lake library entries. Upstream executable Lake files, plugins and arbitrary shell commands are not accepted as candidate configuration. The dependency workspace is prepared from protected environment files. The initial Mathlib profile explicitly trusts a pinned dependency cache and warms only selected modules; an uncached dependency requiring writes to the read-only image fails closed. Broader module coverage is a new reviewed environment configuration, not an implicit network fetch during verification.

### Candidate submissions

The existing registration fields retain attribution and complete target coverage. Optional `execution` enables the new workspace path:

```json
{
  "project_root": "src/submission",
  "include": ["Proofs/**", "Submission.lean"],
  "proof_files": [{"path": "Bridge.lean", "sha256": "<64-hex-digest>"}]
}
```

Upstream paths are relative to `project_root`. Local proof overlays live in `proofs/<submission-id>/`, are hash-bound, and may not collide with selected upstream files or trusted workspace files. Only Lean sources enter proof execution. Target declarations are included in the solution export as well as the official targets. A bridge is an untrusted proof which must pass the same checks; it cannot change the official statement.

Legacy source-only registrations remain supported. New submissions should use explicit workspace and execution fields.

## CI and trust boundaries

1. `resolve` obtains the current open PR head and base and posts a pending status. It executes only protected-base code.
2. `plan` validates bounded PR metadata with trusted schemas and policy. It finds affected candidates, checks that workspaces and environments already exist on the base, and emits a matrix.
3. Each `verify` job prepares its approved environment, fetches the exact upstream commit and allowed source files, and validates overlay hashes. The job has read-only repository permission and no secrets.
4. Build/export runs as a non-root user in offline disposable containers with read-only inputs, explicit seccomp, dropped capabilities, CPU/memory/process/disk/time/output limits and runtime probes. Candidate and Challenge use separate fresh workspaces.
5. Fresh checking containers consume bounded exports, never candidate-controlled executables or `.olean` files. Comparator checks the official statements, dependencies and axioms; Lean and Nanoda replay the proof. Every required target must be present.
6. The controller writes results, fixed input identities, logs and source snapshots. Evidence is sealed and checksummed, then read back. Integrity does not establish proof validity.
7. `publish` uses only the trusted plan and job results, and rechecks the current head/base before posting `lean-verification`. It never downloads or executes artifacts.

A candidate PR cannot approve its own environment or alter its trusted problem. Pure maintenance/documentation PRs may receive `not_applicable`; this never represents verification of a candidate. Removing a registered submission is rejected. Changes to bound statement/environment content invalidate their digests. Global controller or policy changes require repository review and regression tests; the PR's new controller does not authorize its own execution.

The required status remains stable while candidate jobs use a dynamic matrix with `fail-fast: false` and a maximum parallelism of two. A failed, cancelled, timed-out, skipped required job or failed plan prevents success. A no-candidate plan is handled separately from an empty/failed proof run. Merge queue is not configured; add exact `merge_group` binding before enabling it.

## Verification and review results

The standard axiom policy permits only `propext`, `Classical.choice` and `Quot.sound`. A `sorry`, unproved extra axiom or native-computation trust dependency in the checked closure cannot receive full verification. Running a separate numerical program does not discharge an axiom without a checked formal connection.

For workspace submissions, an already-registered but pending mathematical review may allow diagnostic machine checks with an approved environment. The candidate still fails the final merge gate until the exact statement review is approved. A failed check does not establish that the mathematical theorem is false.

Results separate `machine_status`, `review_status`, `verification_status` and `formal_status`. Input binding includes the PR head/base, upstream commit, workspace/environment/policy digests and run ID/attempt, including candidate-level failures before proof execution. The controller distinguishes `verified`, `review_pending`, `failed`, `not_run`, `unsupported` and `infrastructure_error`. Unapproved execution profiles are unsupported; download/runtime errors, timeouts, output limits and Docker runtime failures are infrastructure errors. A nonzero proof-stage exit otherwise remains failed. These classifications never grant a pass and do not establish the mathematical cause of a failure. `conditional` requires structured assumption evidence and is not inferred from candidate log text.

Every executed candidate job writes `result.json` and an English `report.md`, including pre-execution failures. Interrupted sandbox calls retain command, elapsed time and error metadata. Partial output from interrupted calls is not retained. Required target modules must be present in selected candidate sources. The clean checker explicitly requires every official and registered upstream declaration in the solution export and audits its axiom closure using upstream APIs. Exporter exit success alone does not establish target coverage: the pinned exporter can silently omit unknown names. Comparator statement comparison and both kernel replays remain mandatory.

## Evidence and formal acceptance

Per-candidate evidence includes selected source snapshots, problem/submission metadata, resource policy, tool/image identities, exported proofs, stage logs and duration. The `evidence` CLI creates a content-addressed ZIP with a checksum inventory and verifies readback without extracting executable content.

Candidate selection compares referenced environment descriptors and effective policies in addition to submissions and problems. The live PR controller deliberately substitutes the protected policy for PR policy data. Automatic revalidation of already-merged candidates after global controller/policy changes is still missing; selection comparisons alone do not implement that lifecycle. See the [design conformance review](design-conformance-review.md).

Actions artifacts are temporary diagnostic transport (90 days for candidate evidence). Persistent archival storage, backup/readback policy, reviewer onboarding and formal acceptance aggregation remain separate activation requirements. `formal_acceptance_enabled` stays false and `formal_status` stays pending. A sealed ZIP alone is not a durable archive or award decision.

Preserve licenses and provenance for redistributed source snapshots. Retain historical versions; never rewrite a past acceptance record to make it match new inputs.

## Rollout and validation

Keep the existing gate while testing the new backend. The test suite includes source-path/overlay attacks, mutable dependencies, environment tampering, evidence tampering, and workflow permission checks. Actual Docker tests exercise correct proofs, `sorry`, indirect placeholders, extra axioms, wrong statements, extra premises, changed definitions, missing targets, forged output, unchecked declarations, protected writes and multi-file bridges.

Use synthetic fixtures for environment onboarding, not fabricated candidate approvals. Real candidate pilots remain separate intake work: Erdős 650 (single file), DGG (another Lean environment) and Erdős 90 (multi-file project). No candidate is added by this infrastructure change. Measure resource needs before increasing environment budgets or approving broader module coverage.
