# Environment preparation and source adaptation

The same PR controller verifies all registered candidates. This interface does not
promise compatibility with arbitrary Lean versions or executable Lake projects.
New environments remain pending until actual compatibility tests and review are
complete. No command below approves a mathematical statement or an environment.

New candidates use [one candidate JSON and one PR](../README.md#adding-a-candidate).
CI prepares the internal submission and source hashes automatically. It generates
a bridge when the target mapping is unambiguous, or checks the supplied optional
`bridge` file through the same isolated verification pipeline.
The former `draft-submission` command has been removed; use
[templates/candidate.json](../templates/candidate.json) for new entries.
Existing `submissions/` registrations remain supported. The tools below are for
maintainers resolving environment or adaptation blockers.

## Prepare a new environment

```bash
python -m verifier draft-environment /path/to/project \
  --environment-id example-environment \
  --lean-archive-sha256 FULL_64_HEX_SHA256 \
  --exporter-commit FULL_40_HEX_COMMIT \
  --cache-module Mathlib.Data.Nat.Basic \
  --output /tmp/example-environment
```

Supply independently checked tool pins. Repeat `--cache-module` for the required
Mathlib scope; omit it for Core/Std. The generated pending descriptor binds a
minimal static workspace and fixed dependency lock. Executable Lake files, custom
build options and ambiguous dependencies require manual adaptation first.

After review, place the directory under `environments/`. **Lean backend tests**
automatically discovers descriptors, including pending ones. Environment-only PRs
test the affected profiles; shared execution changes test all profiles, with at most
two jobs running concurrently. Manual dispatch can select one exact environment ID
or all environments; see [CI scope](environment-onboarding.md#select-the-ci-scope). It tests valid/invalid proofs, source adaptation,
sandbox restrictions and offline imports for the declared cache scope. Module
import probes demonstrate availability, not correctness of every possible proof
using those modules. Each new tool combination still needs real proof evidence.
Approval is a separate reviewed change; test success never edits policy.

## Adapt source modules without a fork

For simplified candidates, protected `intake-mappings/<candidate-id>.json`
provides exceptional `source_transforms` bound to the candidate digest; see
[mapping operations](simplified-intake.md#candidate-preparation).
Existing registrations use `execution.source_transforms`. Both support exact text replacement and file renaming.
Every transform binds the original UTF-8 source SHA-256 and an exact occurrence
count. It is declarative data, never a shell command or regular expression.

For a project whose `Submission.lean` imports its own `Challenge.lean`, select both
upstream files, rename the upstream challenge, and rewrite that import:

```json
{
  "source_transforms": [
    {
      "path": "Challenge.lean",
      "destination": "CandidateChallenge.lean",
      "sha256": "ORIGINAL_CHALLENGE_SHA256",
      "replacements": []
    },
    {
      "path": "Submission.lean",
      "destination": "Submission.lean",
      "sha256": "ORIGINAL_SUBMISSION_SHA256",
      "replacements": [
        {"old": "import Challenge\n", "new": "import CandidateChallenge\n", "count": 1}
      ]
    }
  ]
}
```

This is an execution-field fragment with placeholders, not a complete submission.
The approved workspace must allow the destination paths. Trusted-file collisions,
missing selected sources, stale hashes, changed occurrence counts, output growth
and overlay collisions are rejected. Target module paths refer to the original
selected modules and follow their explicit rename; theorem declaration names
still refer to the declarations exported by the adapted proof. A bridge exposes
the independently reviewed official target names.

The controller preserves original and adapted sources and their hashes. The
result verifies the adapted source, not an unmodified upstream build. Adaptation
never grants trust: all declarations and required targets still pass Comparator,
the standard axiom policy, Lean and Nanoda. A proof borrowing an upstream
Challenge's placeholder is rejected. Arbitrary Lake programs, native plugins and
non-Lean inputs remain unsupported until a separate backend extension is tested.

## Revalidate after trusted changes

**Revalidate registered Lean proofs** runs after relevant changes reach `main`.
It conservatively selects every registered candidate so global compiler,
controller, workflow and policy changes cannot omit affected proofs. It can also
be dispatched from `main`, optionally selecting one submission. It checks only
the fixed protected revision, never a proposed controller's self-reported result.

Unsupported candidates are listed as blockers while supported candidates run in
separate jobs. Any blocked, failed, cancelled or skipped required execution makes
the aggregate non-passing. An empty registry is explicitly `not_applicable`.
Revalidation does not publish or replace the `lean-verification` PR status.

Every run has fresh evidence and version bindings. `verification-result.json`
follows the versioned [result schema](../schemas/result.schema.json); `result.json`
retains detailed execution diagnostics. Failure stages identify where execution
stopped, without inferring mathematical causes from candidate log text. Archives
remain content-addressed with readback checks; the workflow retains them for 90
days. Persistent storage and formal acceptance remain separate activation work.
