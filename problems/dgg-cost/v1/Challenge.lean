/-
DGG / Goemans cost conjecture: pending official statement, version v1.

Adapted from jyh/dinitz-verify, Challenge.lean, commit
ffba3523f0edd14be3460d039f22a6b98c02fd9e, credited upstream to Jason Hickey
(with Claude). Distributed under Apache-2.0; see LICENSE and definitions.md.

Modifications: rewritten documentation and renamed the target namespace to
OfficialDGG. The definitions and target type retain the upstream encoding.
This is a candidate-informed draft, not an independently approved statement.
See statement.md and correspondence.md for scope and outstanding review.

The final sorry is a statement placeholder for Comparator, never a candidate
proof. Candidate exports must independently prove the target without sorryAx.
-/
import Mathlib

namespace DGG

section Walks

variable {W E : Type}

/-- A finite arc list connects its initial and final vertices. -/
def IsWalk (tail head : E → W) : W → List E → W → Prop
  | x, [], y => x = y
  | x, e :: l, y => tail e = x ∧ IsWalk tail head (head e) l y

end Walks

/-- Sum each terminal's demand once when its chosen walk contains the arc. -/
def uload {R K E : Type} [AddCommMonoid R] [Fintype K] [DecidableEq E]
    (d : K → R) (P : K → List E) (a : E) : R :=
  ∑ k : K, if a ∈ P k then d k else 0

/-- Existence form on finite simple loopless acyclic graphs with positive demands.
This is a restricted-instance encoding, not a claim of equivalence to every
published formulation. The registered target refutes it over the rationals. -/
def DGGCostConjectureFull (R : Type) [CommRing R] [LinearOrder R] [IsStrictOrderedRing R] :
    Prop :=
  ∀ (W E K : Type) [Fintype W] [DecidableEq W] [Fintype E] [DecidableEq E] [Fintype K]
    (tail head : E → W) (src : W) (term : K → W) (d : K → R) (dmax : R) (x c u : E → R),
    -- Simple, loopless and acyclic graph.
    Function.Injective (fun a : E => (tail a, head a)) →
    (∀ a, tail a ≠ head a) →
    (∃ r : W → ℕ, ∀ a, r (tail a) < r (head a)) →
    -- The fractional flow respects capacities.
    (∀ a, x a ≤ u a) →
    -- Terminals are pairwise distinct and different from the source.
    Function.Injective term →
    (∀ k, term k ≠ src) →
    -- Positive demands with an attained maximum; K is therefore nonempty.
    (∀ k, 0 < d k) →
    (∀ k, d k ≤ dmax) →
    (∃ k, d k = dmax) →
    (∀ a, 0 ≤ c a) →
    (∀ a, 0 ≤ x a) →
    -- Non-source inflow minus outflow equals terminal demand at that vertex.
    (∀ z : W, z ≠ src →
      (∑ a : E, if head a = z then x a else 0) - (∑ a : E, if tail a = z then x a else 0)
        = ∑ k : K, if term k = z then d k else 0) →
    -- Source outflow minus inflow equals total demand.
    ((∑ a : E, if tail a = src then x a else 0)
        - (∑ a : E, if head a = src then x a else 0) = ∑ k : K, d k) →
    ∃ P : K → List E,
      (∀ k, IsWalk tail head src (P k) (term k)) ∧
      (∀ a, uload d P a ≤ x a + dmax) ∧
      (∑ a : E, c a * uload d P a) ≤ ∑ a : E, c a * x a

end DGG

namespace OfficialDGG

open DGG

/-- Required refutation target. Mathematical correspondence review is pending. -/
theorem goemans_cost_conjecture_false : ¬ DGGCostConjectureFull ℚ := sorry

end OfficialDGG
