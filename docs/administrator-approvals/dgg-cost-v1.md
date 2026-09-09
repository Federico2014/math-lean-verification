# DGG v1 administrator authorization

## Authority and decision

Administrator: `Federico2014`. On 2026-09-09, the maintainer explicitly requested
changing DGG's review status to `approved` and authorized administrator approval
after being informed that two independent reviewer records were absent.
Codex records that authorization on the maintainer's behalf; it is not a GitHub
review submitted by an independent mathematician.

The authenticated GitHub account was checked with `GET /user` and the repository
with `GET /repos/Federico2014/math-lean-verification`: the account was
`Federico2014` and `permissions.admin` was `true`. This is the authorization
context at preparation time, not a permanent identity attestation or a claim
that the source-paper authors approved the statement.

The exception is limited to `dgg-cost/v1` at the exact statement digest in the
protected policy grant. It waives the two-person independent mathematical
review prerequisite for this statement's machine merge gate. It does not add
anyone to the accredited reviewer roster or represent AI analysis as blind
review. All other statements retain the normal two-reviewer requirement.

## Evidence and remaining limitations

- [Technical correspondence assessment, fixed revision](https://github.com/Federico2014/math-lean-verification/blob/97cb2fefc8edd905ba902460a74ad84720bba1b4/docs/reviews/dgg-cost-v1-2026-09-09/review.md):
  no blocking mismatch identified; candidate-informed and not independent.
- [Original DGG machine diagnostic](https://github.com/Federico2014/math-lean-verification/actions/runs/34338489851/attempts/1):
  Lean, statement/axiom checks and Nanoda passed for the prior input binding.
- [Original paper v1](https://arxiv.org/html/2308.02651v1), retrieved HTML SHA-256:
  `683aa833792e7bedc7e017cfc3b7af4da8ac88c95e4ebaf6b673b80d0f2c1004`.
  This hash identifies the actual downloaded bytes. A durable source archive
  is not established by this record.

The statement's Lean code, definitions, target and environment are unchanged.
Recording the source hash and this approval context changes the bound problem
metadata. Old machine evidence remains historical and must not be relabeled
as a pass for the new statement/policy digest. Candidate CI must run again
after activation on protected main.

## Activation and reporting

First merge the mechanism and exact policy grant with the problem still
pending. A subsequent maintenance PR activates `approved` with
`approval_kind: administrator_exception`, `administrator: Federico2014`,
an empty independent-reviewer list and matching evidence/digest fields.
This separation lets the protected-base controller validate the activation.

Future results must display the administrator approval kind and authority.
Failed proofs, unsupported environments and sandbox failures remain non-passing.
Formal acceptance stays disabled, and priority, award decisions, independent
review and durable archival are not declared complete by this authorization.
