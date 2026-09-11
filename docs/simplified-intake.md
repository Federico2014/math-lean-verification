# Single-PR Lean candidate verification

This implements the [Lean v2 design](https://troneco.atlassian.net/wiki/spaces/javatronx/pages/2446557193/Lean+v2+PR).
Users submit candidate materials; maintainers own mathematical correspondence,
approved environments and merge decisions. CI owns preparation and machine checking.

## Four-stage operator interface

`python -m verifier candidate` exposes submit, prepare, verify and publish. Shared
`workflow.json` summaries report progress and next actions without authorizing
checks or approvals. The [lifecycle runbook](candidate-lifecycle.md) defines each
command, generated registration publication, and explicit administrator acceptance.

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

`resume-candidates.yml` runs on `main` and `develop` pushes and manual dispatch;
the 15-minute schedule runs on the default branch only. Each invocation uses its
own protected target branch and current configuration, paginates open PRs, skips
closed/draft PRs, and replans relevant candidate changes as data. Multiple blockers
remain visible in the uploaded `candidate-resume-*` report. Waiting tasks finish;
no runner is held open while a maintainer works.

Each new candidate identity receives a short protected plan run through an explicit `workflow_dispatch` of `lean-verification.yml` on
the PR target branch with PR number, expected head and expected base. The gate applies only changed
PR registry files to current protected data. Candidate PRs cannot change their own
approval, policy, environment or preparation mappings. Dispatches are deduplicated
by PR/head/base/target branch. All gate entry points share PR concurrency; resolver and publisher status writes
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
retries, without changing candidate materials. A new target-branch revision creates a new
verification identity and an automatic recovery opportunity.

Protect `develop` with the same required checks and configuration review controls
as `main` before using it as a trusted target. The resolver checks the workflow
checkout revision, target branch and live protection; the publisher repeats the
branch/revision checks. Retargeting a PR invalidates its previous verdict even
when both branches point at the same commit. Unsupported targets cannot authorize
execution. A green historical check is not evidence for the new target.

## Result publication

Every push to the protected default branch starts registered-candidate revalidation, including documentation
commits because verifier bindings include the exact revision. At the end of
revalidation, a publication-only job calls the reusable `candidate-catalog.yml`. It
rebuilds a static page and JSON from protected-default-branch registry and GitHub Actions
metadata. It reads only the configured workflow ID/path, default-branch event/repository/SHA,
exact run attempt and the candidate's named verification job and step. A successful
job requires real backend execution and sealed evidence upload. Candidate artifacts,
HTML and printed success strings cannot grant a catalog pass. All displayed strings
are escaped. Full stage results remain linked in the CI evidence artifact.

Only a run for the current default-branch revision can show `verified`. A newer failed,
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

The protected `docs/acceptance-publications.json` index links separately published
administrator decisions. The catalog validates the immutable release, administrator,
tag commit and acceptance-record asset checksum against each pinned reference.
`accepted_historical` describes that published source/verifier version; it never
grants current machine success or enables automatic formal acceptance. The original
CI and archive records remain unchanged. Update this index only through protected
maintenance review after publishing and checking the corresponding archive.

## Deployment

Merge the reviewed implementation after unit/registry and real backend CI pass.
Protected workflows intentionally cannot use this PR's controller to authorize
itself. Their production event-chain test follows deployment to the protected target.
Development PRs target `develop`; catalog publication and post-merge
revalidation follow the current default branch, limited to protected `main` or `develop`.

Once, select **Settings → Pages → Build and deployment → Source: GitHub Actions**.
Allow the `github-pages` environment to deploy from the selected protected default branch. The catalog build
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

**Lean backend tests** selects changed environments for environment-only PRs.
Shared backend, execution-controller, schema, verification-policy, test-driver,
pinned-dependency or workflow changes select all configured environments. Renames
select the new environment ID; fully deleted profiles do not create jobs. Changes confined to catalog generation,
the recovery scheduler, the static environment-draft command or the general CLI
use Registry CI's unit tests instead. Manual dispatch accepts an optional exact
`environment` ID; omit it to test all environments. Empty selections skip backend
execution and are not verification evidence. See [selection rules and commands](environment-onboarding.md#select-the-ci-scope).
The standalone preflight workflow has been removed; `verifier plan` remains a
local diagnostic command.

Default-branch revalidation cancels superseded runs for the same selection; manually
selected candidates use `selected-<id>` in concurrency groups and run titles,
distinct from the `all` scope even for a candidate whose ID is `all`. Every new default-branch revision
still needs its own evidence, including documentation commits. Recovery and
catalog schedules remain available for recovery; completed revalidation jobs
now call publication directly. See GitHub's
[workflow filtering and concurrency rules](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).

## Automatic PR entrypoint and GitHub branch context

GitHub's `pull_request_target` uses the repository's default branch for the
workflow source and `GITHUB_REF` / `GITHUB_SHA`, including PRs targeting `develop`.
See the [GitHub event change](https://github.blog/changelog/2025-11-07-actions-pull_request_target-and-environment-branch-protections-changes/).
The resolver checkout explicitly selects the event's base commit, limited to
`main` or `develop`. Before posting a pending status, it checks the actual Git
checkout against the live protected target SHA and matches the event's PR head,
repository and target branch against the API. Default-branch SHA equality is not
a target-branch check. Stale checkouts, changed heads, retargeted events and
unprotected targets fail closed. A protected target push still invokes recovery
with the fresh base; an old event is never allowed to authorize a stale checkout.

Manual dispatch retains exact `GITHUB_REF` / `GITHUB_SHA` checks for its selected
protected branch. The publisher rechecks checkout, live branch/head/protection,
and status ownership. For the earlier default-branch workflow that already
checks out `pull_request.base.sha` but does not forward `EXPECTED_BASE_REF`, an
automatic publisher derives that binding from the original immutable event.
This allows the resolver/publisher fix on `develop` to serve the existing
`main` entrypoint without changing `main` or manually dispatching candidate runs.
The updated workflow also labels automatic runs with their target branch/base.
Workflow trigger additions (such as `edited`) take effect only when that workflow
file is deployed to the default branch.

PR `edited` events enter the gate only when the base changed. Documentation bots
editing descriptions do not alter proof inputs and no longer trigger duplicate
verification; source updates and retargeting retain the exact identity checks.
