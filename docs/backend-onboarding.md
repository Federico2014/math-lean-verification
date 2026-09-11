# Source-only backend onboarding

Profile: `lean-4-34-rc2-stdlib`. Admission is limited to machine verification of source-only core/Std proofs through the trusted merge gate; it is not approval of any candidate or mathematical statement.

## Fixed components

- Lean release: `v4.34.0-rc2` (a release candidate, matching the pinned Comparator toolchain). Linux archive SHA-256: `3d011041203acacf300d343a39673f7d233743397993797c941346ae9e5df1a8`.
- Comparator: `2312244ac716564a61cc0bf4e107d9abf1757a61`.
- lean4export: `cacf989bd75f608700820f6afc595f32e7a99a4d`, locked in both Lake configuration and manifest.
- Nanoda: `05055695879dfebb6628a67da88ceca6cd6b0421`, built with Rust 1.90.0 and its Cargo lockfile.
- Ubuntu and Rust container base digests are pinned in [Dockerfile](../backend/Dockerfile). Runtime uses the immutable built image ID and records tool binary hashes and OS package versions.
- The Debian build stage uses a signed archive snapshot dated `20260907T000000Z`. Ubuntu uses `backend/ubuntu-packages.lock`, containing all 175 exact installed package versions from the successful run below; the complete installed inventory must match after installation. No unpinned dependency may be added.
- Explicit Docker seccomp profile SHA-256: `4895b5720b8c15faf3680bfee672531a4c6f8d6938b6a50c4e65f7ae822342bd`; provenance and licensing are in [NOTICE.md](../backend/NOTICE.md).

This admits exactly the tested combination, not arbitrary older releases or mutable latest versions. No Mathlib version or upstream candidate cache is approved. Compiler/core/Std release artifacts are an explicit bootstrap trust assumption. Revoke or replace this profile if a relevant checker or toolchain security issue becomes known, retaining old facts and requiring new candidate checks.

## Evidence

[GitHub backend test run 34208680221](https://github.com/Federico2014/math-lean-verification/actions/runs/34208680221) built the tools from source at verifier commit `d3e050ae88dd7dbc81fcdbd289e5ab9980ba330c` and passed the real proof/sandbox matrix on GitHub-hosted Ubuntu 24.04. The `backend-test-evidence` artifact contains per-case stage results, exports, digests, tool manifests, binary hashes, and OS package inventories. It is reproducible test evidence, not a durable award proof archive.

The matrix has two positive cases and ten negative cases. Both positives reach statement comparison, axiom auditing, the official kernel, and independent Nanoda replay. Negative tests must reach isolated Challenge build/export, and applicable cases must also reach Solution export, preventing an always-failing environment from passing the suite.

| Case | Expected behavior |
| --- | --- |
| Valid proof | Accepted by statement comparison and both kernels |
| Unused, unrelated sorry | Accepted; only required proof dependencies determine completeness |
| Direct or indirect sorry | Rejected for `sorryAx` |
| Extra axiom | Rejected for an unpermitted axiom |
| Wrong target or extra premise | Rejected for statement mismatch |
| Altered shared definition | Rejected for dependency mismatch |
| Missing required target | Rejected; no partial overall pass |
| Forged success output | Does not bypass axiom checks |
| Unchecked kernel declaration | Rejected by fresh kernel replay despite candidate compilation |
| Write to protected inputs | Rejected by the read-only sandbox |

The actual execution probes enforce non-root/PID isolation, read-only input and tool paths, no external network routes/connectivity, zero capabilities, no privilege escalation, explicit seccomp, and cgroup limits for memory, swap, CPU, and process count. Local testing also exercised a Docker daemon whose default seccomp was unconfined: execution was rejected until the pinned explicit profile was supplied. No unsafe fallback was added.

## Remaining boundaries

Review dispositions and required strict branch protection are recorded in [merge-gate-review.md](merge-gate-review.md). Subsequent backend CI reruns validate the stricter seccomp profile and locked package sources before deployment.

Approved mathematical reviewers and original-statement reviews are separate human evidence. The roster is still empty. A candidate must reference an already-approved statement on `main`; neither this profile nor a passing synthetic test supplies that approval.

The current backend supports one target module with exact official theorem names and no arbitrary dependency/build adapter. Mathlib, version migration, and bridges for Erdős #650 require separate onboarding. Durable formal archives, publication of award acceptance, identity, priority, and prize assessment remain out of scope for this machine gate and are not enabled.

## Restore pinned Ubuntu package availability — 2026-09-11

The rolling Ubuntu archive removed the locked libc development and Python 3.12
versions, causing all backend images to fail before any Lean execution in
[run 34558577172](https://github.com/Federico2014/math-lean-verification/actions/runs/34558577172).
`backend/ubuntu.sources` now selects the official Ubuntu snapshot at
`20260910T000000Z`. Its noble-updates package index contains the same locked
`2.39-0ubuntu8.8` libc development packages and `3.12.3-1ubuntu0.16` Python packages.
See the [Ubuntu snapshot service](https://snapshot.ubuntu.com/).

The 175-package lock, installed-inventory comparison, base image digest, Lean,
Comparator, exporter and Nanoda pins remain unchanged. APT still verifies Ubuntu
archive signatures with the image's Ubuntu keyring. This restores historical
package availability without upgrading the approved dependency set. Backend CI
must build and exercise every existing environment before this repair is deployed;
new image/verifier revisions require fresh candidate evidence.
