# Formal verification and acceptance policy

Version: lean-workspace-v2. The source-only machine verification profile is admitted with [onboarding evidence](../docs/backend-onboarding.md). Independent statement review and durable formal acceptance remain separate; explicit administrator acceptance records are published separately from machine results.

## Three separate conclusions

1. **Registration valid:** fields, hashes, version references, and target coverage are complete. Current CI provides this check.
2. **Machine verification passed:** approved checkers have validated the target proofs, axioms, and statement correspondence. Enabled for the admitted environment scopes through the trusted merge gate.
3. **Formal acceptance passed:** the normal independent-review acceptance pipeline remains disabled. Explicitly authorized administrator decisions have a separate, scoped archive/publication path and must not be described as completion of two-person independent review.

Award eligibility, priority, contributions, independence scores, and amounts are assessed separately. Replay by two kernels does not automatically constitute two independent academic validation channels.

## Statement fidelity

The path from the original problem to the official Lean statement requires review of domains, quantifiers, assumptions, definitions, conclusions, and direction. Initial statements and corrected versions require independent materials. Retrospective statements for existing results must satisfy conflict-of-interest, blind-drafting, two-person independence, preference for third-party sources, and public-disclosure requirements.

Machines can verify relationships between formal statements. They cannot independently establish correct natural-language interpretation or the authenticity of reviewers' blind drafting.

A repository administrator may grant a narrowly scoped exception through a
protected policy change, as described in [administrator exceptions](../docs/statement-review.md#administrator-exceptions).
Such approval permits the machine merge gate to proceed for the exact bound
statement while explicitly recording incomplete independent review. It grants
no reviewer accreditation or formal acceptance and never waives proof checking.

## Axioms

The proposed standard allowlist is `propext`, `Classical.choice`, and `Quot.sound`. The empty set or any subset is acceptable. `sorryAx` in the transitive target proof dependencies is unacceptable; extra axioms require individual review and do not disappear when compilation succeeds.

Trusted Challenge templates may use placeholders for proof targets. Candidate Solutions and their dependencies must not borrow those placeholders. Searching the entire repository for `sorry` is insufficient to determine target completeness.

## Toolchains and isolation

The approved list contains `lean-4-34-rc2-stdlib`, limited to source-only Lean core/Std projects, with exact sources, release checksum, compatibility tests, and isolation evidence in the [onboarding record](../docs/backend-onboarding.md). The additional `lean-4-28-mathlib` environment is admitted only for its fixed `Mathlib.Data.Nat.Basic` cache closure, with [workspace onboarding evidence](../docs/workspace-onboarding.md). Neither profile approves arbitrary dependencies or all Lean versions. New combinations require their own source identities, binary hashes, security baseline, and compatibility tests.

Builds run offline without privileges, under resource limits, and rebuild candidate sources while ignoring submitter caches. Dependencies come only from the pinned, immutable environment image. Record the bootstrap trust in the toolchain itself. Formal results cover all required top-level targets and bridge proofs.

## Archives

Formal evidence requires durable storage, file checksums, and readback verification. Actions artifacts alone are insufficient. Redistribution of original materials must follow upstream licenses. Records pin the problem, submission, toolchain, policy, and verifier versions.

`policy/verification.json` is the machine-enforced policy. It admits the tested machine backend and source-only profile while keeping `formal_acceptance_enabled` false. A boolean switch cannot implement durable archives or complete missing mathematical review.

## Explicit administrator publication

The [four-stage lifecycle](../docs/candidate-lifecycle.md#4-merge-publish-and-accept)
provides an operator command for administrator-approved archival publication.
It requires an authenticated administrator, an explicit decision and exact successful
protected-run evidence. It does not change `formal_acceptance_enabled`, the approved
reviewer roster, statement-exception grants or machine verdicts. The protected
publication index and README are generated together in a maintenance PR; historical
acceptance is displayed separately from current proof status.
