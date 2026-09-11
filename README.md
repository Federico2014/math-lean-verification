# Formal acceptance: DGG / Goemans cost conjecture counterexample

**Decision: accepted by repository administrator Federico2014 on 2026-09-11.**
Candidate: `dgg-cost-jyh`; registered problem: `dgg-cost/v1`.

The administrator confirmed that review had passed and expressly requested publication in the maintainer session. This is a specific administrator acceptance decision for the exact statement and machine-verified inputs below. No two-person independent-review record was supplied; this publication records administrator authority without asserting compliance with that separate review standard.

## Accepted result

The accepted formal target is `OfficialDGG.goemans_cost_conjecture_false`, of type `¬ DGG.DGGCostConjectureFull ℚ`, using candidate theorem `Submission.goemans_cost_conjecture_false`.

The scope is the registered rational counterexample to the Goemans cost strengthening (Conjecture 1.3 in Traub, Vargas Koch and Zenklusen, arXiv:2308.02651v1). It concerns simultaneous additive maximum-demand arc-load and fractional-cost bounds. The precise statement, definitions and correspondence materials are preserved in `verifier-source-8c6a0b0.zip` under `problems/dgg-cost/v1/`.

Upstream attribution is retained: Dmitry Rybin for the proof/discovery and Jason Hickey for formalization. Attribution and AI-contribution claims are reported from the pinned source; this acceptance does not adjudicate priority or awards.

## Verification evidence

[Trusted Lean verification run 34466489912, attempt 1](https://github.com/Federico2014/math-lean-verification/actions/runs/34466489912/attempts/1) completed successfully on 2026-09-10. The protected controller ran all required targets through sandbox probes, clean statement/proof builds, target coverage, statement comparison, transitive axiom auditing, official Lean kernel replay and independent Nanoda replay.

- Candidate source: [jyh/dinitz-verify at ffba3523f0edd14be3460d039f22a6b98c02fd9e](https://github.com/jyh/dinitz-verify/tree/ffba3523f0edd14be3460d039f22a6b98c02fd9e).
- Verification PR head: `ea41d0d948f0493b6772138833c208a94383566e` (PR #21).
- Protected verifier/base: `8c6a0b0e21fdc63536351fb934e1f66e9fc3b877` (`develop`).
- Environment: `lean-4-32-rc1-mathlib`.
- Statement digest: `9b5389b33e8c8644b9246798597f60a152d87385885875226b700fe4b8ec138b`.
- Input digest: `85fa910992cd45e8def490000be7d93f2669b04e4b2c0447faf0f6bcfd29acdd`.
- Evidence ZIP SHA-256: `f55f1f64fff9051c104f53a98821d217586d01f17d8c1d52c7ee1958d8f57ddc`.

`acceptance.json` contains the full version bindings. `verification-result.json` and the sealed evidence ZIP preserve the original machine results. `evidence-audit.json` records the publication-time integrity, source and binding checks. The original upstream license accompanies the complete candidate source snapshot.

## Archival and recovery

The release assets are the primary permanent publication. Identical files are stored in the Git tree referenced by the release tag, with an archival branch at `acceptance/dgg-cost-v1-20260911`. The release tag identifies this archival record, not a new verifier deployment.

Custodian: Federico2014. Retain this record, assets and tag indefinitely for the lifetime of the repository. Never replace historical evidence; publish a new dated record for corrections, revocation or changed inputs. Git and Release copies share GitHub as a hosting provider; an independent-provider backup is not claimed.

Download the release assets or restore the tagged Git archive, then run `shasum -a 256 -c SHA256SUMS` in the restored directory. Verify the sealed evidence inventory with the repository's Python 3.12 environment:

```bash
python -m verifier.evidence verify f55f1f64fff9051c104f53a98821d217586d01f17d8c1d52c7ee1958d8f57ddc.zip
```

Repeat recovery checks after a storage migration and at least annually. Candidate Lean, Lake and plugins must remain data during archival checks; rerunning a proof requires the approved isolated backend.

## Status interpretation

This new administrator decision follows the historical CI run. Original reports retain their original `formal_status: pending`; their bytes have not been rewritten. The current machine catalog does not ingest manual acceptance publications and may still display `pending`. This release is the versioned publication of the specific administrator acceptance above. It does not globally enable automatic formal acceptance or approve changed inputs. Award eligibility, priority, amounts and recipients remain separate decisions.
