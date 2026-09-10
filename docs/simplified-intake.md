# Single-PR Lean candidate verification

This implements the [Lean v2 design](https://troneco.atlassian.net/wiki/spaces/javatronx/pages/2446557193/Lean+v2+PR).
Users submit candidate materials; maintainers own mathematical correspondence,
approved environments and merge decisions. CI owns preparation and machine checking.

## Candidate preparation

`candidates/<id>.json` is the user-facing registration. `verifier.intake` reads
only bounded, immutable GitHub blobs. It never evaluates Lake. It inspects compiler
and dependency identities, follows standard local imports and generates the
existing internal submission structure with exact hashes. The registered
workspace selects a compatible approved environment; multiple environments never
cause an arbitrary choice.

`python -m verifier plan` emits `plan_kind: candidate_intake` for unresolved
candidates, validated by `schemas/candidate-plan.schema.json`. Existing internal
submission plans retain `schemas/plan.schema.json`. Both remain non-executing.

A new problem description waits for a protected `intake-mappings/<id>.json`
correspondence. Each exceptional mapping binds the entire candidate digest.
Dynamic/custom Lake metadata also requires its exact `reviewed_metadata_sha256`.
Acknowledging metadata allows static preparation; it does not execute upstream
Lake or enable unsupported plugins. Missing cached modules still fail actual CI
and require environment onboarding. Source changes invalidate these acknowledgments.

Standard `Challenge.lean` collisions are renamed to `CandidateChallenge.lean`
with hash-bound import replacements. A generated bridge exposes each official
name using the submitted declaration. Its exact upstream type and universe parameters must pass Comparator;
extra premises or altered definitions cannot pass merely by renaming a theorem.
Generated bridges check the declaration's defining module against the selected
module after source renaming, including when the official and upstream names
already agree. A wrapper that merely imports another module's theorem must name
the defining module in its target, or supply an explicit checked bridge. This
module check is an integration guard, not proof of authorship or originality.
Ambiguous target mappings require a protected mapping or explicit checked bridge.
The complete upstream license, when present, is preserved as comments in the
archived overlay. Original/adapted files, candidate materials, resolved registration
and preparation digests accompany normal proof evidence.

## Automatic recovery

`resume-candidates.yml` runs on main pushes, every 15 minutes and manual dispatch.
It uses protected code and current main configuration, paginates open PRs, skips
closed/draft PRs, and replans relevant candidate changes as data. Multiple blockers
remain visible in the uploaded `candidate-resume-*` report. Waiting tasks finish;
no runner is held open while a maintainer works.

Each new candidate identity receives a short protected plan run through an explicit `workflow_dispatch` of `lean-verification.yml` on
main with PR number, expected head and expected base. The gate applies only changed
PR registry files to current protected data. Candidate PRs cannot change their own
approval, policy, environment or preparation mappings. Dispatches are deduplicated
by PR/head/base. All gate entry points share PR concurrency; resolver and publisher status writes
also share a non-cancelling per-PR job lock. Blocked plans finish without a Lean
matrix. The scheduler never writes commit statuses itself. The resolver rejects
stale identities; the publisher ignores closed/moved PRs and superseded pending
statuses. A failure before proof execution gets at most one automatic retry per identity.
Deleted head repositories are reported per PR without stopping other candidates.
Only ready or blocked plans can trigger recovery dispatches. Candidate data and
proof paths must belong to a registration; orphan files cannot receive a
maintenance-only pass. Markdown-only maintenance remains non-verifying.
An executed proof failure requires correction or an explicit retry. Maintainers
can manually dispatch the trusted workflow with the PR number for infrastructure
retries, without changing candidate materials. A new main revision creates a new
verification identity and an automatic recovery opportunity.

## Result publication

Every main push starts registered-candidate revalidation, including documentation
commits because verifier bindings include the exact revision. `candidate-catalog.yml`
rebuilds a static page and JSON from protected-main registry and GitHub Actions
metadata. It reads only the configured workflow ID/path, main event/repository/SHA,
exact run attempt and the candidate's named verification job and step. A successful
job requires real backend execution and sealed evidence upload. Candidate artifacts,
HTML and printed success strings cannot grant a catalog pass. All displayed strings
are escaped. Full stage results remain linked in the CI evidence artifact.

Only a run for the current main revision can show `verified`. A newer failed,
cancelled or incomplete run cannot fall back to an earlier pass. Unexecuted or
blocked preparation shows `not_run` with the CI plan link. Historical run links
are separate and describe their own revision. API failure stops publication rather
than inventing results; the existing page retains its displayed revision/timestamp.
A candidate pass can be displayed independently of another candidate's failure.
Before publication, the controller refetches verification jobs as well as runs
and checks job identities, statuses, conclusions and step outcomes. A job changing
inside the same running attempt invalidates the snapshot and requires a retry.
The catalog is a presentation of machine checks, not formal acceptance or a durable
archive. Actions proof artifacts have 90-day retention.

## Deployment

Merge the reviewed implementation after unit/registry and real backend CI pass.
Protected workflows intentionally cannot use this PR's controller to authorize
itself. Their production event-chain test follows deployment to main.

Once, select **Settings → Pages → Build and deployment → Source: GitHub Actions**.
Allow the `github-pages` environment to deploy only from main. The catalog build
has `contents: read` / `actions: read`; only its deployment job has `pages: write`
and `id-token: write`. Scheduler write permissions are limited to workflow dispatch; it executes no candidate code. No PAT or GitHub App
is needed. Keep required branch checks and protected configuration review enabled.

After activation, use a synthetic candidate in a disposable test repository to
exercise: supported proof pass/failure; unknown environment waiting; separate
onboarding merge; automatic dispatch preserving candidate head; merge and catalog
publication; stale/closed PR rejection; and source/base changes invalidating a pass.
Record actual run URLs and SHA/attempts. Unit mocks are not acceptance evidence for
these GitHub events. Schedule times are targets, not guaranteed delivery times.

## CI scope and cost

`registry`, `tests` and `lean-verification` remain required on candidate PRs.
The trusted gate starts expensive candidate jobs only for a ready plan; blocked
or maintenance-only PRs finish without building Lean images.

**Lean backend tests** runs on backend, execution-controller, environment, schema,
test-driver or pinned-dependency changes. Changes confined to catalog generation,
the recovery scheduler, the static environment-draft command or the general CLI
use Registry CI's unit tests instead. Manual backend dispatch remains available.
The standalone preflight workflow has been removed; `verifier plan` remains a
local diagnostic command.

Main revalidation cancels superseded runs for the same selection; manually
selected candidates have separate concurrency groups. Every new main revision
still needs its own evidence, including documentation commits. Recovery and
catalog schedules remain necessary for retries and for publishing results after
asynchronous proof jobs finish. See GitHub's
[workflow filtering and concurrency rules](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).
