# Correspondence between the original problem, draft statement, and candidate

This table records relationships that still need to be established. Every item is pending review. A third-party statement does not replace this project's independent mathematical review.

| Topic | Draft statement | Fixed candidate source | Required work |
| --- | --- | --- | --- |
| Set and interval length | A ⊆ Finset.Icc 1 N for every N; length 2N | A is a set of positive natural numbers; length 2 × A.sup id | Establish the relationship between the two optimal guarantees; both bound directions must suffice for the exact formula |
| Interval start | Real x ≥ 1 | Any real x | Check restriction/translation directions and preservation of divisibility |
| Right-side domain | Natural b | Integer b | Prove domain conversions preserving injectivity, divisibility, and interval membership |
| Interval endpoints | Real open interval Set.Ioo x (x + 2N) | Integer open interval Finset.Ioo floor(x) ceil(x + 2 max A) | Prove membership correspondence for integer and noninteger endpoints |
| Range of m | All natural numbers, including 0 | Main theorem assumes 0 < m | Prove m = 0 separately and bridge the positive case |
| Matching | a and b are separately injective on Fin r | HasDivMatching likewise requires both sides to be injective | Check indexing, finite-set membership, and divisibility definitions |
| Optimal value | Natural-number sSup | Natural-number sSup | Establish nonemptiness and boundedness of feasible sets; rule out vacuous conclusions from default sSup behavior |
| Exactness | min(m, ceil(2 sqrt(m))) | erdos_f_eq gives the same numerical formula | Derive the complete official-function target from the candidate-function result; matching strings is insufficient |

## Fixed sources and targets

- [Statement source](https://github.com/google-deepmind/formal-conjectures/blob/c9c94dc9e64b65efa93c4f762845c39aa734adc3/FormalConjectures/ErdosProblems/650.lean): `Erdos650.f` and `Erdos650.erdos_650.parts.i`.
- [Candidate source](https://github.com/Woett/Lean-files/blob/e80f01cb0ca5197cd8acb35c818e75aaa32114dc/ErdosProblem650.lean): `HasDivMatching`, `erdos_f`, and `erdos_f_eq`; additional review entry points are `erdos_f_lower_bound` and `erdos_f_upper_bound`.
- The candidate module is `ErdosProblem650`. `erdos_f_eq_ge4` covers only m ≥ 4 and cannot replace the main target.
- The submission's `official_theorem` field is a requested verification mapping, with no verified adapter yet; `adapter_id` remains `null`.

## Required review evidence

1. Approve interval conventions and all quantifiers against the original problem; freeze statement and definition versions.
2. Check relationships between third-party statement authors and the candidate. Arrange two reviewers meeting independence requirements and preserve public evidence. This compilation cannot count as blind drafting or approval.
3. Compile the target in an approved toolchain and provide Lean bridges covering the differences above. Include adapters in the same axiom audit and checker replay.
4. Check transitive dependencies. Same-name candidate definitions, extra assumptions, or dependency on the placeholder in `Challenge.lean` must not produce a pass.
5. Record results only after the full backend and durable archive are integrated. Current preflight artifacts are not formal passing evidence.
