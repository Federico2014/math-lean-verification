# Formal verification and acceptance policy

Version: lean-gate-v1. The source-only machine verification profile is admitted with [onboarding evidence](../docs/backend-onboarding.md). Independent statement review and durable formal acceptance remain separate; there are no formal verification records.

## Three separate conclusions

1. **Registration valid:** fields, hashes, version references, and target coverage are complete. Current CI provides this check.
2. **Machine verification passed:** approved checkers have validated the target proofs, axioms, and statement correspondence. Enabled for the supported source-only profile through the trusted merge gate.
3. **Formal acceptance passed:** machine verification passed, independent review of the official statement is valid, version policy is satisfied, and evidence is durably archived. Not yet enabled.

Award eligibility, priority, contributions, independence scores, and amounts are assessed separately. Replay by two kernels does not automatically constitute two independent academic validation channels.

## Statement fidelity

The path from the original problem to the official Lean statement requires review of domains, quantifiers, assumptions, definitions, conclusions, and direction. Initial statements and corrected versions require independent materials. Retrospective statements for existing results must satisfy conflict-of-interest, blind-drafting, two-person independence, preference for third-party sources, and public-disclosure requirements.

Machines can verify relationships between formal statements. They cannot independently establish correct natural-language interpretation or the authenticity of reviewers' blind drafting.

## Axioms

The proposed standard allowlist is `propext`, `Classical.choice`, and `Quot.sound`. The empty set or any subset is acceptable. `sorryAx` in the transitive target proof dependencies is unacceptable; extra axioms require individual review and do not disappear when compilation succeeds.

Trusted Challenge templates may use placeholders for proof targets. Candidate Solutions and their dependencies must not borrow those placeholders. Searching the entire repository for `sorry` is insufficient to determine target completeness.

## Toolchains and isolation

The approved list contains `lean-4-34-rc2-stdlib`, limited to source-only Lean core/Std projects, with exact sources, release checksum, compatibility tests, and isolation evidence in the [onboarding record](../docs/backend-onboarding.md). It does not approve Mathlib, arbitrary Lake dependencies, or other Lean versions. New combinations require their own source identities, binary hashes, security baseline, and compatibility tests.

Builds run offline without privileges, under resource limits, and rebuild candidate sources and dependencies while ignoring submitter caches. Record the bootstrap trust in the toolchain itself. Formal results cover all required top-level targets and bridge proofs.

## Archives

Formal evidence requires durable storage, file checksums, and readback verification. Actions artifacts alone are insufficient. Redistribution of original materials must follow upstream licenses. Records pin the problem, submission, toolchain, policy, and verifier versions.

`policy/verification.json` is the machine-enforced policy. It admits the tested machine backend and source-only profile while keeping `formal_acceptance_enabled` false. A boolean switch cannot implement durable archives or complete missing mathematical review.
