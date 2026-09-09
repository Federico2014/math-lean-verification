# Repository Guidelines

## Project Structure

- `verifier/`: Python CLI, registry validation, execution planning, and evidence handling.
- `tests/`: unittest regressions; `scripts/`: backend smoke tests and status publication.
- `backend/`: container definitions, sandbox probes, and Lean replay integration.
- `schemas/`, `policy/`, `environments/`: metadata contracts, verification rules, and pinned toolchains.
- `problems/`, `submissions/`, `proofs/`, `records/`: versioned statements, registrations, proof bridges, and evidence records.
- `templates/`, `docs/`, `.github/`: intake templates, design/runbooks, and CI workflows.

Read `README.md`, `SECURITY.md`, `docs/design.md`, and `docs/implementation-status.md` before changing the verifier.

## Development Commands

Use Python 3.12:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python -m verifier validate
python -m verifier list
```

These commands install dependencies, test, validate metadata/hashes, and list registrations. Validation does not execute Lean or establish proof validity. Inspect environments statically with `python -m verifier inspect-environment /path/to/project`.

## Style and Naming

Use English for documentation, comments, forms, registration descriptions, issues, and PRs; preserve source titles, names, notation, and identifiers. Follow existing Python style: four-space indentation, `snake_case` functions/modules, `PascalCase` classes, and `UPPER_SNAKE_CASE` constants. Registry IDs use lowercase hyphenated names. No dedicated formatter/linter is configured.

## Testing

Use `unittest`, `tests/test_*.py`, and `test_*` methods. Use synthetic temporary fixtures; cover changed behavior and rejection paths. Run both tests and registry validation for implementation changes. Environment approval requires real proof/sandbox evidence from **Lean backend tests**; mocks cannot establish checker success.

## Commits and Pull Requests

Use `feat:`, `fix:`, `docs:`, or `build(deps):` with an imperative summary. Follow `.github/pull_request_template.md`: describe the problem, behavior, validation, and invalidated evidence; link candidate issues. Required checks: `registry`, `tests`, and `lean-verification`. Prepare trusted problem/environment changes in separate maintenance PRs.

## Security Boundaries

- Treat candidate source, Lake configuration, exports, and output as untrusted. Never execute candidate Lean, Lake, plugins, or precompiled artifacts on the host.
- Candidate containers must be credential-free, without write tokens; only protected-base controllers retrieve sources or publish statuses. Never add self-hosted runners, credentials, or privileged PR execution.
- Keep original-problem review, machine checking, formal acceptance, and award decisions separate. Never automate awards or simulate checker success; unsupported, missing, and unconfigured states remain non-passing.
- Require documented onboarding evidence before enabling formal acceptance or approving reviewers/toolchains.
- Pin Actions to full commits and CI Python packages to versions/hashes; keep development versions aligned.
- Add real candidates, submissions, or internal award files only when explicitly tasked.
- Source/dependency changes invalidate bound evidence. Never overwrite immutable records.
