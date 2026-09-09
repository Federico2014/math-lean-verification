# DGG-compatible environment approval

## Evidence and scope

`lean-4-32-rc1-mathlib-dgg` is admitted using
[run 34332650985, attempt 1](https://github.com/Federico2014/math-lean-verification/actions/runs/34332650985/attempts/1)
at commit `f6bd602d9ad991b15f17970089c2da3479ae3697`. Its tree matches the
merged onboarding commit `c318c13f4b43b87120c3ec70554b4a79ea37a94a` from
[PR #10](https://github.com/Federico2014/math-lean-verification/pull/10).
The [DGG job](https://github.com/Federico2014/math-lean-verification/actions/runs/34332650985/job/102404682714)
passed all 21 real proof, cache and sandbox cases on GitHub-hosted Ubuntu 24.04.
All three environment jobs passed in the same run.

Positive cases cover checked proofs, a Mathlib lemma, multi-file bridges,
adapted Challenge imports and offline imports of `Mathlib` and
`Mathlib.Data.Nat.Basic`. Negative cases reject placeholders, extra axioms,
wrong statements, extra premises, changed definitions, missing targets,
forged output, unchecked declarations and protected writes. The cache guard
accepts current artifacts and rejects missing or stale artifacts without rebuilding.

Evidence artifact:

- Name: `backend-test-evidence-lean-4-32-rc1-mathlib-dgg`.
- [Artifact ID 10096717163](https://github.com/Federico2014/math-lean-verification/actions/runs/34332650985/artifacts/10096717163).
- GitHub archive SHA-256: `c780c21cb05816448bbace0121ff1e793f034f536f8703eb82f091f899dc9a0f`.
- Downloaded `summary.json` SHA-256: `4f8743731655b3733ad60c58a78b0a63ede940fa19e22720a64c689c013dcd7d`.

The workflow retains backend artifacts for 30 days. They are diagnostic
infrastructure evidence; persistent formal archives remain separate work.

## Approved configuration and limits

The [descriptor](../environments/lean-4-32-rc1-mathlib-dgg/environment.json)
fixes Lean `v4.32.0-rc1`, exporter
`3de59f10bc4b4a0f2de698597aeb1246caa0df0a`, Mathlib
`360da6fa66c1273b76b6b2d8c5666fd5ac2e3b56` and all nine locked dependencies.
It uses the shared pinned Comparator and Nanoda checker configuration.
Fixed dependency caches are an explicit trust assumption. Cache preparation
rejects incomplete or stale targets with a 300-second deadline and a 10-second
forced-termination grace period.

Sandbox limits are 2 CPUs, 6144 MiB memory, 2048 MiB private workspace,
3600 seconds, 2000 source files, 32 MiB source and 512 MiB export.
The successful DGG job ran for 8 minutes 45 seconds including image builds;
this is not a measurement of DGG proof execution or peak resource consumption.
Full Mathlib import coverage does not establish compatibility with every proof,
custom Lake program or native plugin. Actual candidates must pass their own
isolated build, statement/axiom checks and Lean/Nanoda replay.

## Binding the approved environment

Approval changes only description, status and evidence URL in the descriptor;
compiler, dependency, cache and resource settings match the tested configuration.

- Tested pending digest: `3dafa26debc496636202dfdde51a276efef7903b5abfa308e0e03be0b306a543`.
- Approved digest: `98af3ee95f2fe97c8abf67c05af0a89bafc0fa72a3ee8a20a4d53f3f8309a22d`.

New problem workspaces must bind the approved digest after this approval reaches
`main`. No existing problem or submission is bound to this environment, so no
candidate result is invalidated. Keep historical evidence unchanged. Future
execution-setting changes need fresh evidence and review.

This approval enables environment reuse. The DGG problem and proof remain
unregistered, the mathematical reviewer roster remains empty, and
`formal_acceptance_enabled` remains false.
