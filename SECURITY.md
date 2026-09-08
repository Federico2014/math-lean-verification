# Security model

## Current execution boundary

This bootstrap repository validates JSON registration data and bound local statement files. It does not fetch, build, import, export, or execute candidate Lean projects. The backend is deliberately unconfigured. A preflight plan is never a proof verification result.

The verifier's schemas come from its own checkout, not from the candidate data root. JSON has size limits, duplicate-key rejection, strict properties, fixed commit requirements, and path/symlink checks. Statement reviews bind content hashes and cannot be copied across statement changes.

Approved reviewer names in JSON are not identity authentication, proof of independence, or evidence of blindness. Protected-branch review and verifiable review records are required before accepting these claims. CI does not perform mathematical review.

## CI permissions

- Repository CI uses `pull_request` and `push`, GitHub-hosted ephemeral runners, and read-only repository permissions. It has no repository secrets and no deployment authority.
- PRs can modify tests and workflows. Their green checks are developer feedback, not authoritative formal evidence. Formal decisions must use an independently protected verifier revision.
- Preflight runs only on the default branch via `workflow_dispatch`. It never executes candidate source.
- All Actions use full commit pins. Checkout does not persist credentials. Python CI dependencies use exact versions and hashes.
- No `pull_request_target`, privileged `workflow_run`, self-hosted runner, candidate build cache, or automated publishing job is enabled.
- CODEOWNERS only protects files when repository branch protection requires its review. Check actual GitHub settings using the maintainer runbook.

## Mandatory boundary before enabling a Lean backend

Candidate Lean macros, tactics, Lake configurations, native plugins, dependencies, binaries, logs and exports are untrusted. Never run them directly on a host or in a job with credentials. A container without verified filesystem, process, privilege and network restrictions does not satisfy this contract.

Build and export must run in a disposable, non-root, resource-limited, offline sandbox. Prepare trusted Challenge data separately; candidate code cannot modify it, the checker, policy, or the result publisher. Do not mount the Docker socket, credentials, `.git`, runner environment, or Actions command files. Sandbox probes are mandatory and fail closed.

Candidate `.olean` and other precompiled artifacts are not trusted inputs. The formal path must rebuild source and use bounded exported data for checker handoff. A candidate-controlled stdout message, exit wrapper, generated JSON, or badge is not evidence of checker success.

Use trusted statement comparison and axiom auditing plus independent kernel implementations. Lean's official kernel and `lean4checker` are not two independent implementations. Additional assumptions must remain disclosed; `sorryAx` in the required proof closure is incomplete.

Complete the integration and adversarial acceptance tests in `docs/implementation-status.md` before changing the bootstrap policy. Removing the `backend_unconfigured` blocker is not an implementation of verification.

## Reporting

Do not disclose an exploitable sandbox or result-forgery issue in a public issue. Use GitHub private vulnerability reporting when enabled at the repository's Security tab. General documentation and non-sensitive bugs can use the bug report template.

Reference: [GitHub Actions security](https://docs.github.com/en/actions/reference/security/secure-use), [Lean proof validation](https://lean-lang.org/doc/reference/latest/ValidatingProofs/).
