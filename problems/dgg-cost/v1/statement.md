# DGG / Goemans cost conjecture: v1

## Source and requested result

This pending problem registration follows [Issue #12](https://github.com/Federico2014/math-lean-verification/issues/12).
The reference is Vera Traub, Laura Vargas Koch and Rico Zenklusen,
[Single-Source Unsplittable Flows in Planar Graphs, arXiv:2308.02651v1](https://arxiv.org/html/2308.02651v1),
Definition 1.1, the preceding flow-conservation equations and Conjecture 1.3.
The paper version is dated 2023-08-04; the conjecture's first proposal date
and priority are not established by this registration.

For a feasible rational single-source fractional flow `x`, terminal demands
with maximum `dmax`, and nonnegative arc costs `c`, the conjecture asks for
one path per terminal with both:

```text
load(a) ≤ x(a) + dmax                       for every arc a
sum_a c(a) * load(a) ≤ sum_a c(a) * x(a)
```

The requested result is a counterexample to existence, which also refutes
the stated polynomial-time construction. The cost-free congestion theorem
(Theorem 1.2) is a separate result.

## Registered Lean target

Module: `Challenge`. Declaration:

```lean
OfficialDGG.goemans_cost_conjecture_false : ¬ DGG.DGGCostConjectureFull ℚ
```

The predicate quantifies over finite vertex, arc and terminal-index types.
Its hypotheses impose a simple, loopless, acyclic graph, distinct non-source
terminals, positive demands with an attained maximum, nonnegative flow/costs,
capacities above the flow, and conservation at every vertex. Its conclusion
selects one finite walk per terminal satisfying both inequalities.

The intended inference is that failure already on this restricted class
refutes the general claim. Walks include paths; ruling out every such walk
routing is sufficient. These correspondence arguments require the review
record in [correspondence.md](correspondence.md); they are not separately
formalized implications from a second encoding of the paper.

## Boundaries

This version does not register a planar-graph claim, real-number target,
two-sided load bounds, other published conjecture variants, a proof of
optimal numerical constants, discovery priority or an award decision.
It contains no candidate proof or fixed counterexample instance.

The statement is candidate-informed and mathematically **pending**. Its
placeholder supplies the comparison target, not a proof. Registration CI
checks metadata and hashes; real Lean elaboration/export and candidate proof
checks occur in the later isolated candidate workflow.
