# Security model

## Current execution boundary

The registry validates JSON metadata and bound statement files. The PR merge gate additionally provides reusable, hash-bound environments and trusted workspaces with Comparator and independent Nanoda replay. Candidate execution requires an approved environment and a registered trusted workspace on the protected base. Pending mathematical review permits diagnostics only and never a merge pass. See [the merge gate](docs/lean-merge-gate.md). A preflight plan and a metadata CI pass are never proof verification results.

The verifier's schemas come from its own checkout, not from the candidate data root. JSON has size limits, duplicate-key rejection, strict properties, fixed commit requirements, and path/symlink checks. Statement reviews bind content hashes and cannot be copied across statement changes.

Approved reviewer names in JSON are not identity authentication, proof of independence, or evidence of blindness. Protected-branch review and verifiable review records are required before accepting these claims. CI does not perform mathematical review.

## CI permissions

- Repository CI uses `pull_request` and `push`, GitHub-hosted ephemeral runners, and read-only repository permissions. It has no repository secrets and no deployment authority.
- PRs can modify tests and workflows. Their green checks are developer feedback, not authoritative formal evidence. Formal decisions must use an independently protected verifier revision.
- Preflight runs only on the default branch via `workflow_dispatch`. It never executes candidate source.
- All Actions use full commit pins. Checkout does not persist credentials. Python CI dependencies use exact versions and hashes.
- The trusted `pull_request_target` gate checks out only protected-base controller code. PR files are bounded data; candidate execution is confined to disposable containers in the read-only job. Separate status-only jobs consume trusted job outcomes, never candidate artifacts. No privileged `workflow_run`, self-hosted runner, or candidate build cache is enabled. Reviewed environment images may contain explicitly trusted, fixed Mathlib dependency caches; candidate builds cannot write to them.
- CODEOWNERS only protects files when repository branch protection requires its review. Check actual GitHub settings using the maintainer runbook.

## Mandatory boundary before enabling a Lean backend

Candidate Lean macros, tactics, Lake configurations, native plugins, dependencies, binaries, logs and exports are untrusted. Never run them directly on a host or in a job with credentials. A container without verified filesystem, process, privilege and network restrictions does not satisfy this contract.

Build and export must run in a disposable, non-root, resource-limited, offline sandbox. Prepare trusted Challenge data separately; candidate code cannot modify it, the checker, policy, or the result publisher. Do not mount the Docker socket, credentials, `.git`, runner environment, or Actions command files. Sandbox probes are mandatory and fail closed.

Candidate `.olean` and other precompiled artifacts are not trusted inputs. The formal path must rebuild source and use bounded exported data for checker handoff. A candidate-controlled stdout message, exit wrapper, generated JSON, or badge is not evidence of checker success.

Use trusted statement comparison and axiom auditing plus independent kernel implementations. Lean's official kernel and `lean4checker` are not two independent implementations. Additional assumptions must remain disclosed; `sorryAx` in the required proof closure is incomplete.

The source-only backend must pass its real proof and sandbox regressions before deployment. Complete the remaining integration and adversarial acceptance requirements in `docs/implementation-status.md` before enabling formal acceptance or adding broader toolchains. A green diagnostic or manually posted status cannot replace verification.

## Reporting

Do not disclose an exploitable sandbox or result-forgery issue in a public issue. Use GitHub private vulnerability reporting when enabled at the repository's Security tab. General documentation and non-sensitive bugs can use the bug report template.

Reference: [GitHub Actions security](https://docs.github.com/en/actions/reference/security/secure-use), [Lean proof validation](https://lean-lang.org/doc/reference/latest/ValidatingProofs/).

## Candidate preparation and publication

The main-only recovery scheduler has Actions/status write access and handles bounded
candidate data without executing Lean, Lake or plugins. Candidate PRs cannot alter
protected mappings or approvals used for their own preparation. An exact candidate
and metadata digest binds exceptional static adaptation. Description-only problem
matching requires maintainer correspondence; a matching title is insufficient.

Catalog generation consumes protected-main Actions job metadata with workflow,
repository, revision, attempt and verification-step checks. It does not ingest PR
artifacts or trust candidate-provided success JSON. Only the separate Pages deploy
job has deployment permissions. A published timestamp/revision identifies stale
views after API or deployment failures. Formal evidence retention remains separate.
