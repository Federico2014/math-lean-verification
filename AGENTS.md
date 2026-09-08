# Repository instructions

This repository is math-lean-verification. It contains no award candidates at bootstrap.

- Read README.md, SECURITY.md, docs/design.md and docs/implementation-status.md before changing the verifier.
- Run `python -m unittest discover -s tests -v` and `python -m verifier validate` for implementation changes.
- Treat candidate source, Lake configuration, exports, and printed results as untrusted.
- Never run candidate Lean, Lake, plugins, or precompiled artifacts on the host or in a credentialed job.
- Preserve the separation between original-problem review, machine checking, and award decisions.
- Do not enable formal acceptance or add approved reviewers/toolchains without the documented onboarding evidence.
- Never simulate checker success. Unsupported, missing, or unconfigured states must remain non-passing.
- Pin workflow actions to full commits and Python packages to versions and hashes.
- Do not add real candidates, copy internal award files, or create submissions without an explicit task to do so.
- Source and dependency changes invalidate bound verification evidence; immutable records are never overwritten.
- Do not add self-hosted runners, credentials, automatic award decisions, or privileged PR execution.
