# Definitions and proof interface

## Lean definitions

All non-library definitions are in [Challenge.lean](Challenge.lean).

- `DGG.IsWalk`: recursive arc-list connectivity. The empty list requires equal
  endpoints; a nonempty list must start at the current vertex and continue
  from the first arc's head. It does not independently impose simplicity.
- `DGG.uload`: finite sum of demands whose chosen lists contain the queried
  arc. Membership counts a terminal once, not once per occurrence. This agrees
  with path loading; the graph rank also excludes repeated vertices in valid
  walks. Review remains pending.
- `DGG.DGGCostConjectureFull`: the implication from the instance hypotheses to
  a simultaneous load-and-cost routing witness. The inherited name `Full`
  does not establish completeness or equivalence to other formulations.
- `OfficialDGG.goemans_cost_conjecture_false`: the sole required target over
  `ℚ`, with one deliberate `sorry` placeholder in the trusted statement.

The generic definitions use Mathlib's ordered-ring and finite-type classes;
the target fixes the canonical rational instances. No custom typeclass
instances, axioms, executable commands or proof tactics are introduced beyond
the target placeholder. Candidate proofs must use only the policy's allowed
axioms and must not depend on this placeholder.

## Source provenance and license

The definitions and target type are adapted from
[jyh/dinitz-verify/Challenge.lean](https://github.com/jyh/dinitz-verify/blob/ffba3523f0edd14be3460d039f22a6b98c02fd9e/Challenge.lean),
commit `ffba3523f0edd14be3460d039f22a6b98c02fd9e`.
The [upstream README](https://github.com/jyh/dinitz-verify/blob/ffba3523f0edd14be3460d039f22a6b98c02fd9e/README.md)
credits Jason Hickey (with Claude) for formal verification and attributes
discovery separately to Dmitry Rybin and a GPT session. These are source
attributions, not this repository's priority findings.

This version rewrites comments to expose pending review and changes the target
namespace from `Challenge` to `OfficialDGG`. Definition bodies and the target
type retain the upstream encoding. [LICENSE](LICENSE) preserves the upstream
Apache-2.0 terms for the adapted Lean source. No candidate proof is copied.

## Environment and candidate interface

The workspace binds `lean-4-32-rc1-mathlib`, approved in
[commit 3cc6661](https://github.com/Federico2014/math-lean-verification/commit/3cc6661ade37b553dd69a5d389973066321b1c97), with digest
`2549518f7e642162f4a05d3c1b0eedd6c3fc0a4431f5b40b4bbc7da9abfd1396`.
Its [backend onboarding run](https://github.com/Federico2014/math-lean-verification/actions/runs/34452461091)
passed 29 real regression cases; these do not verify the DGG candidate proof.
It pins Lean `v4.32.0-rc1`, Mathlib
`360da6fa66c1273b76b6b2d8c5666fd5ac2e3b56`, all locked dependencies and the
exporter/checker combination. `import Mathlib` uses its approved cache scope.

The solution module is `Bridge`. Allowed candidate paths are
`CandidateChallenge.lean`, `Submission.lean`, `Submission/**` and `Bridge.lean`.
These reserve room for source adaptation; they are not registered submissions.
For the source submitted in PR #20, CI will prepare the following after statement
approval:

1. Select and hash-bind the original Challenge and Submission files, rename
   the former to `CandidateChallenge.lean`, and update the latter's import.
2. Provide a bridge exposing `OfficialDGG.goemans_cost_conjecture_false` from
   `Submission.goemans_cost_conjecture_false`. The separate official namespace
   avoids colliding with the upstream placeholder declaration.
3. Build the trusted Challenge and candidate solution in separate workspaces.
   The candidate receives no trusted `Challenge.lean`. Comparator must compare
   the definitions and target, and the checkers must reject use of the
   upstream placeholder or other unapproved proof assumptions.

Different proofs may use the same interface if they derive the complete target.
No candidate Lean or Lake code may execute on the host.
