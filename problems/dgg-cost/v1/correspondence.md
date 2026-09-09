# Statement correspondence review

## Status and provenance

**Pending; no independent approval is recorded.** This working statement
adapts the public candidate project's definitions after reading candidate
materials. It is not a blind draft. The upstream description of faithfulness
is not adopted as an approval finding.

Primary reference: [Traub–Vargas Koch–Zenklusen, arXiv:2308.02651v1](https://arxiv.org/html/2308.02651v1),
Definition 1.1 and Conjecture 1.3. The following entries identify review
obligations and the proposed reasoning, rather than completed reviewer verdicts.

## Correspondence checklist

| Element | Lean encoding | Proposed correspondence; review pending |
| --- | --- | --- |
| Domain | Target specializes `R` to `ℚ`; `W`, `E`, `K` have `Fintype` instances | Vertex and arc types may be arbitrary finite types; no counterexample size is built into the claim. |
| Graph | `tail`, `head`, injective endpoint pairs, unequal endpoints, increasing natural rank | Simple, loopless, acyclic instances form a subclass. A refutation on this subclass must suffice; no equivalence to every graph convention is asserted. |
| Terminals | Injective `term : K → W`, with `term k ≠ src` | Each index represents one distinct non-source terminal. |
| Demands | `0 < d k`, `d k ≤ dmax`, and an attained equality | Positive demands restrict the nonnegative domain. The equality requires a nonempty terminal set and makes `dmax` the actual maximum. Review the refutation direction, not a claim that zero-demand cases were formalized. |
| Capacities | `0 ≤ x a` and `x a ≤ u a` | Nonnegative capacities follow; no missing capacity-sign premise is needed. |
| Conservation | Non-source inflow minus outflow equals demand; source outflow minus inflow equals total demand | Check signs and indexing, including terminal transit flow and vertices without terminals. |
| Quantifiers | All instance data precede hypotheses, then `∃ P` | One routing family must satisfy both bounds simultaneously. The target negates this universal existence statement. |
| Paths and loads | `IsWalk` and membership-based `uload` | Ordinary paths are included and their loads agree. On a ranked acyclic graph, a walk cannot repeat a vertex. Audit these relationships; no extra path-equivalence theorem is registered. |
| Conclusion | All-arc additive bound and total cost bound | Both conditions are required, with neither an extra premise nor a relaxed constant. |
| Algorithmic scope | Existence predicate only | Refuting existence also rules out any algorithm producing a witness; the target makes no independent complexity claim. |

## Required approval evidence

Follow [the repository statement-review process](../../../docs/statement-review.md):

1. Obtain two eligible curators' independent drafts from original sources,
   with identities, dates and conflict-of-interest disclosures. Curators must
   avoid candidate materials while drafting; this document cannot serve as
   either independent draft.
2. Freeze both drafts before comparison, then document discrepancies and
   resolutions against this candidate-informed encoding.
3. Preserve an identifiable source snapshot and its SHA-256. The versioned
   source link and retrieved HTML hash are recorded in `problem.json`;
   durable source archival remains outstanding for formal acceptance.
4. Confirm the approved reviewer roster and bind the final statement digest
   only after the evidence is complete. Changed meaning requires a new
   statement version and invalidation of affected verification evidence.

Independent mathematical review remains pending. A separately authorized
administrator exception, if activated, changes the merge-gate approval basis
without completing these independent-review obligations. See
[the authorization record](../../../docs/administrator-approvals/dgg-cost-v1.md).
