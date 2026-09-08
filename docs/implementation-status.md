# Implementation status and formal acceptance checklist

The repository provides candidate registration and a trusted source-only Lean merge gate. Registration CI and a machine proof verdict are distinct; neither grants formal award acceptance.

## Implemented

- [x] Strict registration schemas, fixed commits, complete target coverage, hash binding, safe paths, and statement-review digests.
- [x] Non-executing `validate`, `list`, and `plan` commands.
- [x] Protected-base PR controller, exact-head statuses, and separate status publishing.
- [x] Source-only Lean core/Std execution profile with fixed Lean/Comparator/exporter/Nanoda versions and [onboarding evidence](backend-onboarding.md).
- [x] Fresh isolated build/export environments, explicit seccomp, read-only mounts, non-root execution, no network, and resource/output/time limits with runtime probes.
- [x] Comparator statement/dependency comparison, transitive axiom audit, official Lean kernel replay, and independent Nanoda replay.
- [x] Real positive and negative Lean regression tests in CI; all positive cases must reach both kernels.
- [x] Fail-closed prerequisites: candidate changes require an already-approved official statement and supported toolchain on `main`; no self-approved Challenge or policy from the PR.
- [x] Temporary per-run exports, stage results, version/input digests, image ID, tool checksums, and package inventories.

## Still required for broader verification and formal acceptance

- [ ] Approve real mathematical reviewers and preserve their independent drafting, conflict disclosures, source snapshots, and statement review evidence.
- [ ] Onboard Mathlib and additional Lean/dependency combinations with exact locks, clean rebuilds, compatibility/security review, and adversarial tests.
- [ ] Integrate reviewed multi-module adapters and bridges; do not silently weaken targets or skip unsupported inputs.
- [ ] Establish durable evidence storage, backups, licensing authorization, readback verification, and immutable formal records.
- [ ] Implement formal acceptance aggregation and minimal-permission archival publication independently of temporary Actions artifacts.
- [ ] Review actual candidate contributions, priority, independence scoring, recipient identity, and prize decisions separately.

`formal_acceptance_enabled` remains false. The existing Erdős #650 registration is blocked until its independent statement review, supported Lean/Mathlib profile, and required bridges are completed. No successful synthetic proof test changes its status.

See the [merge gate documentation](lean-merge-gate.md) for its supported scope, submission process, and status semantics, and the [technical design](design.md) for the broader target architecture.
