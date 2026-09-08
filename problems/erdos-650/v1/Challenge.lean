/-
Copyright 2026 The Formal Conjectures Authors.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-/

import Mathlib

/-!
DRAFT statement adapted from Formal Conjectures, commit
c9c94dc9e64b65efa93c4f762845c39aa734adc3, ErdosProblems/650.lean.
Changes: import Mathlib directly; retain only f and the exact-formula target;
remove project-specific annotations and other problem variants.

This file has NOT been compiled or independently approved by this registry.
The sorry below is a statement placeholder, never an accepted proof.
A future verifier must reject candidate proofs depending on this placeholder.
See correspondence.md and NOTICE.md for provenance and outstanding obligations.
-/

namespace Erdos650

noncomputable def f (m : ℕ) : ℕ :=
  sSup {r : ℕ | ∀ N : ℕ, ∀ A ⊆ Finset.Icc 1 N, A.card = m → ∀ x : ℝ, 1 ≤ x →
    ∃ a b : Fin r → ℕ, (Function.Injective a) ∧ (Function.Injective b) ∧
      (∀ i, a i ∈ A) ∧ (∀ i, (b i : ℝ) ∈ Set.Ioo x (x + 2 * (N : ℝ))) ∧ (∀ i, a i ∣ b i)}


/-- Draft target: the exact optimal matching guarantee, including m = 0. -/
theorem erdos_650.parts.i (m : ℕ) : f m = min m ⌈2 * Real.sqrt m⌉₊ := by
  sorry

end Erdos650
