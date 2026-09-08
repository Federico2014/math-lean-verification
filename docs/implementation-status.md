# Implementation status and formal-verification activation checklist

The initial repository is **a candidate registry and verification infrastructure skeleton**. This document separates implemented behavior from the missing backend so that green repository CI is not mistaken for a verified mathematical proof.

## Implemented

- [x] Problem, submission, adapter, and record directories and registration structure; no formal verification records exist.
- [x] Candidate and problem intake forms, templates, and operating documentation.
- [x] JSON Schema 2020-12, duplicate-key/nonfinite-number rejection, and size limits.
- [x] Fixed commits, directory identities, complete target coverage, and cross-file reference validation.
- [x] Trusted file hashes, complete directory binding, and path traversal/symlink rejection.
- [x] Statement review digests and reviewer roster consistency checks.
- [x] CLI commands that do not execute candidates: `validate`, `list`, and `plan`.
- [x] Restricted preflight status: an unconfigured backend always exits nonzero and never reports formal success.
- [x] Automated tests and registration CI, plus a manual preflight entry point.
- [x] Commit-pinned Actions and hash-pinned Python CI dependencies.

## Before enabling full Lean verification

- [ ] Approve and pin compatible Lean/Mathlib/Comparator/exporter/Nanoda combinations.
- [ ] Implement preparation that fetches only fixed public sources and safely handles archives, dependencies, and licensing.
- [ ] Validate non-root execution, disabled networking, filesystem/process isolation, and resource limits in the target Linux environment.
- [ ] Run sandbox probes on every execution; never fall back to unsandboxed execution on failure.
- [ ] Rebuild cleanly from source and export inside the sandbox; trusted Challenge and candidate workspaces must not share writable artifacts.
- [ ] Compare trusted statement dependencies, audit axioms, and replay with two independent kernels.
- [ ] Pin and review adapters; include bridge proofs among all required targets.
- [ ] Implement complete result schemas, trusted result generation, and aggregation across every target.
- [ ] Implement durable evidence archives, readback validation, version binding, and separate publishing with minimal permissions.
- [ ] Publish review roles, independent blind-drafting materials, and the current toolchain security policy.

Removing `backend_unconfigured`, setting `formal_acceptance_enabled` to true, or returning fabricated success JSON does not complete these tasks. The bootstrap policy schema explicitly rejects such activation. Integrate the complete backend through a separate implementation and review PR.

## Required tests for the real backend

Use a valid small synthetic proof as a positive case. The following negative cases must be rejected or reported as incomplete:

| Case | Required result |
| --- | --- |
| Same theorem name but conclusion changed to True, weakened quantifiers, or changed domain | Statement mismatch |
| Added False premise or another unauthorized assumption | Complete official conclusion not established |
| Custom definitions/instances change mathematical meaning | Dependency comparison or human review rejects |
| Indirect sorryAx or borrowed Challenge placeholder | Incomplete proof |
| Custom axioms or extra computational trust | Extra assumptions pending review |
| Only some required targets completed | No overall pass |
| One kernel fails or is unsupported | No pass |
| Forged stdout, result JSON, or old evidence | No effect on the trusted verdict |
| Malicious .olean or shared-cache contamination | Cannot enter the trusted execution boundary |
| Networking, token reads, or changes to Challenge/checker/Actions control files | Blocked by isolation and recorded |
| Timeout, resource exhaustion, or malformed output | Explicitly incomplete; no pass |
| Lost archive, changed inputs, or reused stale approval | No formal acceptance |

These real Lean/sandbox tests have not run yet. Existing Python tests cover only the implemented registration and preflight behavior.
