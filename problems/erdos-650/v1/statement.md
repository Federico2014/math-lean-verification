# Erdős #650: optimal bounds for matching integers to distinct multiples

Status: **pending registration; Lean verification, award eligibility, and first-solution priority have not been established.** Linked to [Issue #4](https://github.com/Federico2014/math-lean-verification/issues/4), with submission ID `erdos-650-woett`.

## Original problem and target

The original problem is [Erdős Problems #650](https://www.erdosproblems.com/650). This draft follows the open-interval convention of the [fixed third-party statement](https://github.com/google-deepmind/formal-conjectures/blob/c9c94dc9e64b65efa93c4f762845c39aa734adc3/FormalConjectures/ErdosProblems/650.lean).

For a natural number m, let f(m) be the largest natural number r with the following property: for every natural number N, every finite set A ⊆ {1, …, N} with |A| = m, and every real x ≥ 1, there are r pairs (aᵢ, bᵢ) such that aᵢ ∈ A, bᵢ is a natural number in the open interval (x, x + 2N), aᵢ divides bᵢ, and each side has no repeated elements.

The target is the exact formula for the optimal uniform guarantee:

```text
For every m ∈ ℕ, f(m) = min(m, ceil(2 * sqrt(m))).
```

This requires both a uniform lower bound and worst cases attaining the corresponding upper bound; sufficient pairs for one particular set do not suffice. The sole registered target is `Erdos650.erdos_650.parts.i`, including m = 0. Historical coarse bounds and other variants in the upstream file are not separately registered targets.

The candidate's main theorem `erdos_f_eq` assumes m > 0 and uses a different interval encoding. The bridge to the complete target is pending. The target mapping is not evidence that equivalence has been proved. See the [correspondence checklist](correspondence.md) and [definition notes](definitions.md).

## Sources and dates

- [Paper v1: Optimal bounds for an Erdős problem on matching integers to distinct multiples](https://arxiv.org/abs/2603.28636v1), Wouter van Doorn, Yanyang Li, and Quanyu Tang; first submitted on 2026-03-30.
- [Problem discussion and contribution timeline](https://www.erdosproblems.com/forum/thread/650). The paper date does not settle first-solution priority.
- [Fixed candidate source](https://github.com/Woett/Lean-files/blob/e80f01cb0ca5197cd8acb35c818e75aaa32114dc/ErdosProblem650.lean); registration involved static reading of public source only, without executing Lean or Lake.
- [Third-party statement](https://github.com/google-deepmind/formal-conjectures/blob/c9c94dc9e64b65efa93c4f762845c39aa734adc3/FormalConjectures/ErdosProblems/650.lean); adaptation and licensing details are in [NOTICE.md](NOTICE.md). This compilation of materials has consulted candidate sources and does not constitute independent blind drafting.

## Acceptance boundary

`review.status` remains `pending`. There are no approved reviewers, approved toolchain, bridge proof, or formal machine-verification records. The `sorry` in `Challenge.lean` marks a proof target and must never be used as a proof dependency; the file has not been compiled with an approved toolchain. CI success means only that registration checks and infrastructure tests passed.
