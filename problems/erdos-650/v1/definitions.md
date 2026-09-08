# Definitions and environment notes

## Draft statement

- `m N : ℕ`; `A : Finset ℕ`, with `A ⊆ Finset.Icc 1 N` excluding 0 and `A.card = m` fixing the size.
- `r : ℕ` is the matching size. `a b : Fin r → ℕ` are separately injective, preventing reuse of either endpoint.
- `x : ℝ` with `1 ≤ x`; `Set.Ioo x (x + 2 * (N : ℝ))` excludes both endpoints strictly.
- `a i ∣ b i` is natural-number divisibility. Interval membership uses the real cast of b.
- `f` takes the natural-number `sSup` of uniformly guaranteed r values. Establish nonemptiness and boundedness, especially for m = 0 and quantifiers over infeasible A.
- `⌈2 * Real.sqrt m⌉₊` is the natural-number ceiling of a nonnegative real. `min m` limits the matching to the set's size.

`Challenge.lean` is adapted from the [fixed third-party statement](https://github.com/google-deepmind/formal-conjectures/blob/c9c94dc9e64b65efa93c4f762845c39aa734adc3/FormalConjectures/ErdosProblems/650.lean) and imports only `Mathlib`. No project-approved Mathlib version has been selected and it has not been compiled. Its placeholder `sorry` must not enter a candidate proof.

## Candidate source and declared environment

SHA-256 of the original bytes of the [fixed candidate file](https://github.com/Woett/Lean-files/blob/e80f01cb0ca5197cd8acb35c818e75aaa32114dc/ErdosProblem650.lean):

```text
a42e78b06de572e11a996baac29d45c9a476b60c4a658c954c90ba803e8ac4d1
```

This digest was computed while reading the fixed public source. It is not evidence of a clean build or durable archive, and the current registration validator does not download the source to check it.

The source header declares Lean `leanprover/lean4:v4.28.0` and Mathlib `8f9d9cff6bd728b17a24e163c9402775d9e6a365`. These declarations do not establish an approved toolchain. Exact compiler provenance, build entry point, dependency closure, adapter, and independent-checker compatibility remain incomplete, so `toolchain_id` is `null`.

The candidate's `HasDivMatching` defines injective matching between positive natural numbers on the left and integers on the right. `erdos_f` uses `A.sup id`, an integer floor/ceil open interval, and arbitrary real starts. Its main theorem assumes m > 0. See [correspondence.md](correspondence.md) for differences from the draft.

The candidate source includes `#print axioms erdos_f_eq`, but it was not executed and no trusted axiom output is available. Actual dependencies, axioms, and independent replay results are unknown; source appearance does not establish kernel acceptance.
