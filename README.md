# math-lean-verification

[![Registry CI](https://github.com/Federico2014/math-lean-verification/actions/workflows/ci.yml/badge.svg)](https://github.com/Federico2014/math-lean-verification/actions/workflows/ci.yml)

Infrastructure for verifying Lean formalizations of mathematical results, initially for the Justin Sun Prize. The goal is to check both that **a proof is valid under the accepted logic and that it proves the intended mathematical problem.**

## Current status

The repository supports candidate registration. **No results have been formally verified.** Use `python -m verifier list` to list registered submissions and inspect their referenced statement review records.

Available components include candidate intake forms, registration schemas, original-problem and statement-correspondence templates, hash and target-coverage validation, CI tests, and a maintainer preflight entry point. The CI badge reports only repository code and registration checks.

**The Comparator and dual-checker execution backend, approved toolchains, and durable archive are not integrated.** The current `plan` command reports preflight blockers and exits with a nonzero code. It does not download or execute candidate code or produce a proof-passed result. Backend activation requires the [implementation checklist](docs/implementation-status.md).

## Adding a candidate

1. Use the [candidate submission form](https://github.com/Federico2014/math-lean-verification/issues/new?template=candidate.yml) to provide the original problem, paper, Lean repository, full commit, and target theorems.
2. For a new problem, register a pending statement draft. Independent review is required before formal acceptance. An existing statement version may be reused.
3. Open a registration PR following the [contribution process](CONTRIBUTING.md). Do not include credentials, KYC data, or materials that are not authorized for publication in an issue.
4. A maintainer merges the registration and runs preflight. Full proof verification runs separately once the backend is available.

## Verification principles

```text
Original mathematical problem
    ↓ Independent mathematical review: quantifiers, definitions, scope, assumptions, conclusion
Official Lean statement (fixed version)
    ↓ Machine comparison + axiom audit + independent checker replay
Candidate proof (fixed commit)
    ↓ Complete evidence archive linked to review records
Formal acceptance status (separate from prize amount, priority, and recipient identity)
```

Faithfulness from natural language to Lean requires independent review; machine checking alone cannot establish that the natural-language problem was understood correctly. Candidates cannot change the problem or allowlist to make their proofs pass.

## Local development

Use Python 3.12. Install the pinned development dependencies as follows; `requirements-dev.txt` is not used for formal CI.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python -m verifier validate
python -m verifier list
```

CI uses `requirements-ci.lock` and `--require-hashes` on Linux x86_64 / Python 3.12. The two dependency lists must keep matching versions.

After registration, run `python -m verifier plan <submission-id> --output plan.json`. Exit codes: `0` means registration validation succeeded; `2` means invalid input; `3` means preflight completed but formal verification is blocked. None of these exit codes indicates that a proof has been verified.

## Documentation

- [Technical design](docs/design.md)
- [Candidate contribution process](CONTRIBUTING.md)
- [Statement correspondence review](docs/statement-review.md)
- [Maintainer runbook](docs/maintainer-runbook.md)
- [Implementation status and acceptance checklist](docs/implementation-status.md)
- [Verification and acceptance policy](policy/verification.md)
- [Security boundaries](SECURITY.md)

Original repository code is licensed under MIT. Third-party materials retain their own licenses and must include applicable notices. External papers and proof sources retain their owners' licenses; integration or archiving does not change those licenses.
