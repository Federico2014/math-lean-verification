# DGG candidate source mapping

This submission follows [Issue #12](https://github.com/Federico2014/math-lean-verification/issues/12)
and the protected [dgg-cost/v1 workspace](../../problems/dgg-cost/v1/statement.md).
The [registration](../../submissions/dgg-cost/dgg-cost-jyh.json) selects
`Challenge.lean` and `Submission.lean` from
[jyh/dinitz-verify at ffba3523f0edd14be3460d039f22a6b98c02fd9e](https://github.com/jyh/dinitz-verify/tree/ffba3523f0edd14be3460d039f22a6b98c02fd9e).

The only upstream adaptations are renaming `Challenge.lean` to
`CandidateChallenge.lean` and replacing the single `import Challenge` in
`Submission.lean`, with a modification notice beside that import. Original hashes and exact occurrence counts are bound in
the registration. No upstream definition or proof body is changed.

[Bridge.lean](Bridge.lean) exposes
`OfficialDGG.goemans_cost_conjecture_false` using
`Submission.goemans_cost_conjecture_false`. It imports the candidate solution,
which receives no trusted `Challenge.lean`. The different official namespace
avoids a duplicate declaration with the upstream placeholder. CI must audit
both registered targets and reject any dependency on that placeholder.

The upstream [README](https://github.com/jyh/dinitz-verify/blob/ffba3523f0edd14be3460d039f22a6b98c02fd9e/README.md)
attributes discovery to Dmitry Rybin with GPT assistance and formalization
to Jason Hickey with Claude. These are source attributions pending independent
review. The Apache-2.0 license is included verbatim in the bridge comment so
it accompanies the original and adapted sources in CI evidence snapshots.

Real CI uses the approved DGG environment, compares the official statement and
definitions, audits axioms, and performs Lean plus Nanoda replay. The original
run passed machine checks and reported `review_pending`. The protected problem
is now approved by a documented administrator exception; fresh CI can report
`verified` only after machine checks pass again, with
`review_approval_kind: administrator_exception`. Independent mathematical review
and formal acceptance remain incomplete. No source script or candidate Lake
configuration is run on the host.
