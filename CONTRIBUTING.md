# Adding candidates and contributing

Use English for repository content, issues and PRs. Preserve mathematical notation
and original names for attribution. Registration and CI results do not decide awards.

## Submit a candidate

See the [complete candidate lifecycle](docs/candidate-lifecycle.md) for the full
submission, review, verification, registration and acceptance process.

1. **Submit:** complete [the candidate template](templates/candidate.json) and run
   `python -m verifier candidate submit <id> <file> --repository OWNER/REPO` to validate
   materials and open a candidate-only PR. Contributors without repository write
   access can open a fork PR through GitHub's UI.
2. **Prepare:** CI reports prerequisites; maintainers approve the statement,
   environment and adaptation in separate maintenance PRs. Keep waiting PRs open.
3. **Verify:** inspect actual trusted proof evidence and all three required checks.
   Use `candidate verify --pr N --repository OWNER/REPO` for an explicit retry.
4. **Publish:** a maintainer runs `candidate publish <id> --pr N --repository OWNER/REPO`
   to merge and generate the registration publication PR. After explicit administrator
   approval, the same command with `--approval <file>` handles archive and acceptance
   publication. The command waits for normal checks/review before merging generated maintenance PRs.

A new problem description uses `problem: {"title": "…", "source_url": "https://…",
"scope": "…"}` instead of `problem_id`. A maintainer must map it to an approved
statement. A similar title alone cannot establish mathematical correspondence.

For unusual layouts, set `source.project_root` or an explicit source selection.
If automatic bridging is ambiguous, supply `bridge: "Bridge.lean"` and place the
file at `proofs/<candidate-id>/Bridge.lean`. This is untrusted proof code subject
to all normal checks. See [intake operations](docs/simplified-intake.md).

## Maintainer responsibilities

Prepare new workspaces, review correspondence, and onboard environments in separate
maintenance PRs. Follow [statement review](docs/statement-review.md) and
[environment onboarding](docs/environment-onboarding.md). Required evidence and
policy approval are mandatory; draft generation and onboarding tests do not approve
anything automatically. Protect exceptional mappings in `intake-mappings/`.

Once those changes reach the candidate PR's protected target branch, the scheduler rechecks open PRs and dispatches ready
ones automatically. It does not run Lean while prerequisites are missing. Resolve
any proof failures with the author. Merge only after exact statement approval and
all required `registry`, `tests`, `lean-verification` checks pass. Protect the
required status against unrelated writers using repository settings.

Merging registers the candidate on the target branch. Each protected default-branch
push starts revalidation. The generated
[Registered candidates page](https://Federico2014.github.io/math-lean-verification/)
updates immediately after revalidation, with scheduled recovery. The publication
command generates the README summary and any acceptance-index change together;
the catalog supplies current status.

## Repository implementation changes

Read `AGENTS.md`, `README.md`, `SECURITY.md`, `docs/design.md` and
`docs/implementation-status.md` before changing the verifier. Use Python 3.12 and run:

```bash
python -m unittest discover -s tests -v
python -m verifier validate
```

Describe changed behavior and test evidence in the PR. Link related issues when
applicable. Never execute candidate Lean or Lake on the host. Backend CI runs real
positive and adversarial proof cases in isolated containers; tests with a fake
checker do not establish proof validity or production event-chain acceptance.
