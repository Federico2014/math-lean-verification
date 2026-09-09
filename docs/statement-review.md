# Original-problem and Lean-statement correspondence review

## Review chain

Original mathematical problem → approved Lean Challenge → candidate proof. Independent mathematical review validates the first step; trusted verification tools validate the second once the backend is available.

## Checklist

| Topic | Required checks |
| --- | --- |
| Original problem | Literature, version, exact citation location, first proposal date, and disputed formulations |
| Scope | Full conjecture, counterexample, special case, generalization, or partial progress |
| Domain | Number system, dimension, finite/infinite scope, and object classes |
| Quantifiers | Universal/existential, order, and dependencies |
| Assumptions | Added hypotheses and conditions that could make the claim vacuously true |
| Conclusion | Completeness of constants, optimality, asymptotics, and infinite-existence claims |
| Definitions | Nonstandard definitions, overloads, typeclass instances, and trusted library versions |
| Direction | Proof, refutation, or equivalence; whether bridges cover sufficient directions |
| Attribution | Distinguish first solutions, prior proofs, new results, and formalization work |

## Retrospective official statements

Two curators meeting conflict-of-interest requirements independently draft statements using only the original problem, without referring to the candidate paper, proof, or formalization. Freeze both draft hashes before comparing them publicly and resolving differences. Preserve identities, relationship disclosures, dates, sources, independent drafts, and resolution records.

Existing independent third-party statements may be preferred, but still require definition review and version freezing. Two model outputs or two GitHub usernames do not establish independence by themselves.

## Approval records

`review.status` defaults to `pending`. It may become `approved` only when public review evidence is complete and maintainers confirm it through a protected PR. Both reviewers must belong to the approved roster in `policy/verification.json`, which is currently empty.

`review.statement_digest` is the SHA-256 of canonicalized `problem.json` with the `review` field removed. It includes trusted file hashes, targets, scope, original sources, and toolchain ID. Compute it with `verifier.registry.statement_digest(problem)`. Changing any bound content after approval invalidates the previous digest.

Maintainers must verify the authenticity of identities, blind drafting, and conflict-of-interest disclosures. Code validation checks only field completeness, roster consistency, and hash binding.

## Statement adaptation

If a candidate uses a different encoding, provide a reviewed Lean bridge proof deriving the complete official target from the candidate result. Claims of equivalence require both directions. Do not change official definitions or add unauthorized assumptions to make a submission pass.

The initial version does not allow arbitrary definition holes. Corrections invalidate the old official statement and require a new version and review. Keep old evidence records and mark them invalidated.

## Supplemental technical evidence

- [DGG v1 correspondence assessment, 2026-09-09](reviews/dgg-cost-v1-2026-09-09/review.md):
  candidate-informed technical analysis with exact-input machine evidence and
  a finite arithmetic cross-check. It is not an independent blind draft or an
  accredited reviewer approval. Prospective blind reviewers should draft from
  the original sources before reading this report.
