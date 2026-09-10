# Identify, reuse and onboard an environment

An environment is a shared configuration, not a workflow per candidate. Its descriptor fixes compiler/exporter versions, dependency workspace hashes, cache scope and resource limits. The descriptor digest is included in every problem workspace and result.

Use `python -m verifier draft-environment --help` to generate a pending descriptor
from static metadata and explicitly supplied tool pins. Backend regression CI now
discovers descriptors automatically; no per-environment workflow entry is needed.
See [generic intake](generic-intake.md) for the complete draft and test procedure.

## Static discovery

```bash
python -m verifier environments
python -m verifier inspect-environment /path/to/project
```

The command reads bounded files only. Dynamic Lake code is never evaluated. Matching compares the Lean version and fixed dependency identities, ignoring project names and lock formatting. The environment listing supplies canonical digests. Results are suggestions with `machine_status: not_run`; reviewers check the lock, special requirements and proposed reuse.

## Reuse

Select an approved environment already admitted in `policy/verification.json`. Configure project subdirectory, source patterns, target declarations and bridge separately. Do not create another environment just because a file or theorem has a different name.

## New version or special requirements

1. Copy an environment descriptor under a new ID; keep `status: pending` and `evidence_url: null`.
2. Pin the official Lean release archive SHA-256 and a compatible official exporter commit. Freeze every dependency and hash all environment files.
3. Use `dependency_mode: none` for core/Std or `mathlib-cache` with a reviewed static Lake workspace and complete lock. The latter explicitly trusts fixed dependency caches. Set `cache_modules` to the approved module closure needed by the workspace; an empty list asks the upstream cache tool for its full default cache and may exceed runner disk.
4. Choose bounded resource limits. Run the real proof/negative cases before deciding a configuration is supported.
5. Record the immutable workflow run and measured limitations. Only then may a separate reviewed change set `status: approved` and add the ID to the policy allowlist. Recompute the descriptor digest when status or content changes.
6. Bind a new/reviewed problem workspace to that approved digest. Updating an in-use environment invalidates workspace binding; prefer new IDs.

After cache retrieval, image preparation runs `lake --no-build build` for the
declared module scope. This can fill missing input hash metadata while rejecting
stale or absent build targets without compiling them. The check has a 300-second
deadline and a 10-second forced-termination grace period. Incomplete caches and
budget failures stop onboarding; there is no automatic full-Mathlib rebuild.

## Select the CI scope

For a PR, **Lean backend tests** compares the complete PR with its merge base:
changes under `environments/<id>/` select only those existing environment IDs.
Renaming selects the new ID; a fully deleted environment is not built. Changes to
shared backend/verifier code, schemas, verification policy, the smoke driver,
pinned CI dependencies or this workflow select all environments. Documentation
and the static entrypoints listed in the workflow need no backend run. Missing
history, invalid metadata and unknown manual IDs fail rather than silently skip.

Manual dispatch tests all environments when `environment` is omitted or empty.
To test one environment on `develop`:

```bash
gh workflow run backend-ci.yml \
  --repo Federico2014/math-lean-verification \
  --ref develop \
  -f environment=lean-4-32-rc1-mathlib
```

Use the exact ID, not a directory path; `all` is not a reserved keyword. To run
all environments, omit `-f environment=...`. Direct pushes do not trigger this
backend workflow; use manual dispatch after direct maintenance commits.

The selection job summary lists the tested scope. An empty selection skips the
backend job and supplies no verification evidence. A successful single-environment
run establishes evidence only for that environment and revision. Each selected
job still runs its complete proof, negative, import and sandbox regression suite.
No selection or successful run grants environment approval. Different manual
selections have separate concurrency groups; repeated runs of the same selection
may supersede one another.

## Local diagnostic execution

These commands require Docker. Candidate Lean never executes on the host.

```bash
docker build -t lean-gate-tools backend
python -m verifier.build_environment lean-4-28-mathlib --allow-pending --output images.json
```

Pass the immutable image ID in `images.json` to `scripts/backend_smoke.py --image <image-id> --environment lean-4-28-mathlib --output <new-evidence-directory>`. `--allow-pending` is only for onboarding; the trusted candidate gate still rejects pending environments.

The shared checker uses pinned Comparator and Nanoda implementations. The project Lean version can differ, but export compatibility must be tested. Build failures, unsupported primitives, missing caches or missing runtime isolation never downgrade to unchecked execution.
