# DGG v1 statement correspondence: technical review

## Verdict and reviewer disclosure

**No blocking correspondence defect was identified for the registered rational
counterexample target.** The restricted-instance and walk encodings support
the required refutation direction. This is a supplemental technical assessment,
not a completed independent mathematical approval.

Prepared by Codex on 2026-09-09 at the maintainer's request, following
[Issue #12](https://github.com/Federico2014/math-lean-verification/issues/12) and
[candidate PR #14](https://github.com/Federico2014/math-lean-verification/pull/14).
The same assistant helped prepare the statement and candidate integration and
had already read candidate source. It cannot supply either required blind
draft, an independent reviewer identity or an authenticated conflict-of-interest
disclosure. **This document contributes zero accredited reviewer approvals.**

## Frozen inputs

- [Original paper](https://arxiv.org/html/2308.02651v1): Traub, Vargas Koch and
  Zenklusen, *Single-Source Unsplittable Flows in Planar Graphs*, v1 dated
  2023-08-04. Reviewed Section 1's instance definition, conservation equations,
  load notation and Conjecture 1.3. The original conjecture's first proposal
  date and discovery priority are outside this finding.
- [Official Challenge](https://github.com/Federico2014/math-lean-verification/blob/3413e29baec76e47c439eeaa2d453e744c658d8d/problems/dgg-cost/v1/Challenge.lean):
  `dgg-cost/v1`, protected revision `3413e29baec76e47c439eeaa2d453e744c658d8d`.
- Candidate revision `ffba3523f0edd14be3460d039f22a6b98c02fd9e`, registration
  revision `7f1b5029d4cb895e2e683bd9c51ed9340aaca3a8`.
- [Manifest](manifest.json): exact source, statement, environment, policy,
  CI and local evidence hashes. The statement digest excludes the review
  field; the CI workspace digest includes it. These hashes have different
  purposes and must not be interchanged.

The exact original-paper HTML was downloaded and hashed. Its bytes are kept
locally for this review; this PR publishes the retrieval identity and hash,
not a full paper copy. A durable source-snapshot archive is still outstanding.
The protected problem's `snapshot_sha256` remains null; this supplemental
manifest does not silently complete that approval requirement.

## Original claim and sufficient direction

Conjecture 1.3 asks for a polynomial-time construction of unsplittable paths
whose arc loads do not exceed the fractional loads plus the maximum demand,
and whose cost does not exceed the fractional cost. The registered target
denies even existence, over rational data. The cost-free theorem is distinct.
[Source](https://arxiv.org/html/2308.02651v1#S1.Thmtheorem3).

Let `C` denote the source claim and `F` the Lean predicate
`DGG.DGGCostConjectureFull ℚ`. The relevant implication is `C → F`, so
`¬ F → ¬ C`. This is an ordinary mathematical argument about encodings,
not a separately kernel-checked bridge to a second formalization of `C`.

To justify the implication, take any instance satisfying `F`'s hypotheses.
It is a finite rational instance in the original domain. Apply the alleged
construction and represent each resulting path as its ordered arc list.
Those lists satisfy `IsWalk`; `uload` equals the path's demand-based load.
The same family satisfies both inequalities in `F`. Therefore a proof of
`¬ F` is sufficient. Proving `F → C`, or a polynomial running-time bound,
is unnecessary for this counterexample task.

## Clause-by-clause findings

Line references below refer to the fixed official Challenge linked above.
Source anchors refer to [the instance definition](https://arxiv.org/html/2308.02651v1#S1.Thmtheorem1),
[the preceding conservation equations](https://arxiv.org/html/2308.02651v1#S1.p3)
and [Conjecture 1.3](https://arxiv.org/html/2308.02651v1#S1.Thmtheorem3).

| Clause | Official Lean location | Technical finding |
| --- | --- | --- |
| Numeric domain | Lines 39-42, 77 | The definitions are generic, but the registered theorem fixes `ℚ`. Its negation is not merely a result about integers or an unspecified coefficient ring. |
| Finite objects | Lines 41-42 | `Fintype` supplies finite vertex, arc and terminal-index sets. Decidable equality supports finite sums; it imposes no substantive restriction on these finite witnesses. |
| Graph restrictions | Lines 44-46 | Injective endpoint pairs exclude parallel arcs; unequal endpoints exclude loops; strict natural rank excludes directed cycles. These reduce the instance class. A counterexample in this class also refutes a claim over a larger class. No reduction from arbitrary graphs is needed for that inference. |
| Terminal identity | Lines 50-51 | Injectivity identifies each index with a distinct terminal, and excludes the source from that set. The encoding does not accidentally duplicate a demand or count the source as a sink. |
| Demand and maximum | Lines 53-55 | Every demand is positive, all are bounded by `dmax`, and some attains it. Thus `K` is nonempty and `dmax` is the genuine positive maximum. A refutation on positive-demand instances is sufficient even though the larger source domain admits zero demands. |
| Capacity sign | Lines 48, 57 | `0 ≤ x a ≤ u a` implies `0 ≤ u a`. A separate nonnegativity premise for `u` is redundant, not missing. The bound to verify is against `x + dmax`, not a different capacity expression. |
| Nonnegative costs | Line 56 | Negative-cost routes cannot be introduced by the instance data. |
| Non-source conservation | Lines 59-61 | The left side is inflow minus outflow. At a terminal the right side is its unique demand; elsewhere it is zero. Negating both sides gives the source's outflow-minus-inflow sign convention. Transit through a terminal is permitted without losing its net demand. |
| Source conservation | Lines 63-64 | Net source outflow is exactly total demand. This prevents an instance whose demand is supplied from nowhere. Together with the preceding clause, every vertex is covered. |
| Quantifier order | Lines 41-68 | All instance data and hypotheses precede a single existential routing family. The load and cost conditions are conjoined for that same family; separate witnesses cannot satisfy them independently. |
| Endpoint semantics | Lines 25-27, 66 | The empty list requires equal endpoints; nonempty walks must follow each arc from its tail. Since terminals differ from the source, an empty route cannot discharge a demand. |
| Load semantics | Lines 32-34 | Each demand contributes once iff its route contains the arc. This equals the source path-load sum. Even without using acyclicity, every path has such a walk encoding, so excluding all walk witnesses excludes path witnesses. |
| Repeated walks | Lines 27, 46 | Along a valid walk rank strictly increases. Revisiting a vertex would force its rank to be strictly below itself. Repeated arcs/vertices therefore cannot exploit membership-based counting in the admitted instances. |
| Both bounds | Lines 67-68 | The all-arc additive bound uses the actual `dmax`; the cost bound uses the same `x`, `c` and routing loads. No doubled constant, omitted conjunct or extra candidate premise was found. |
| Required direction | Line 77 | The target is the negation of the entire universal existence predicate, without an extra false hypothesis. The Challenge's placeholder is a comparison target, not the evidence for that negation. |

## Non-vacuity and numerical cross-check

The [fixed candidate construction](https://github.com/jyh/dinitz-verify/blob/ffba3523f0edd14be3460d039f22a6b98c02fd9e/Submission.lean#L202)
supplies concrete finite types, demands and flows. Its
[refutation call](https://github.com/jyh/dinitz-verify/blob/ffba3523f0edd14be3460d039f22a6b98c02fd9e/Submission.lean#L667)
passes evidence for the graph, capacity, terminal, demand and conservation
hypotheses; it chooses `u = x`.

The reviewer-authored [arithmetic script](witness-check.py) transcribes only
the finite data and enumerates paths independently of upstream executable
code. Running it produced [witness-check.json](witness-check.json):

- Source net outflow 40; terminal net inflows 15, 10 and 15; other balances zero.
- Maximum demand 15, fractional cost 58, two paths per terminal and eight
  routing families in total.
- Four families meet every additive load bound; their minimum cost is 60.
  None satisfies both the load and cost bounds.

This checks that the proposed instance and interpretation are concrete and
consistent. Integer values embed exactly in the rational domain. This script
is supplemental arithmetic, not a replacement for Lean checking or an
independent mathematical reviewer. It neither imports nor runs upstream code.

## Actual machine evidence

[Run 34338489851, attempt 1](https://github.com/Federico2014/math-lean-verification/actions/runs/34338489851/attempts/1)
checked the exact official and candidate targets. The preserved
[verification-result.json](verification-result.json) reports:

```text
machine_status: passed
review_status: pending
verification_status: review_pending
failed_stage: null
error: null
```

Completed stages include isolated source builds/exports, target coverage,
statement comparison, transitive axiom auditing, official Lean replay and
independent Nanoda replay. The bound proof stage took 61.124 seconds.
Downloaded source hashes and the protected statement were checked against
the archived inputs. The sealed archive's full inventory was read back and
verified (33 entries); its SHA-256 is recorded in the manifest.

The upstream placeholder is not licensed as an assumption by these checks.
A successful required-target axiom audit rules out `sorryAx` in the audited
closure. This does not mean every unrelated theorem in the upstream project
was independently registered and reviewed.

GitHub correctly marks the overall workflow failed because review remains
pending. The artifact expires on 2026-12-08. The small result copy and hashes
in this PR support review traceability; they are not a durable full proof
archive or a new execution verdict.

## Scope limits and remaining approval work

The finding is confined to the cited v1 cost conjecture and registered
rational target. It makes no planarity, stronger two-sided-bound, other
formulation, historical-priority or prize finding. The source calls the
conjecture open in 2023; that historical statement is not used to deny the
later candidate evidence.

Under [the existing approval process](../../statement-review.md), maintainers
still need two eligible reviewers' independently frozen original-source
drafts, identity and conflict disclosures, a documented reconciliation,
source archival evidence, and an authenticated roster update. Reviewers
should complete blind drafting before reading this candidate-informed report.
Once that evidence exists, a separate protected approval change can bind the
final statement digest and reviewer evidence, followed by fresh candidate CI.

This evidence PR leaves the official statement, reviewer roster, review
status, verification policy and formal-acceptance settings unchanged. It
does not resolve the `review_pending` merge gate by itself.
