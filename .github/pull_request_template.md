## Changes

Describe the problem, scope and resulting behavior. Link related issues when applicable.

## Four-stage candidate workflow (if applicable)

- [ ] Submit: candidate JSON contains the original problem, fixed proof commit and all targets.
- [ ] Publication permission, authorship, AI contribution and assumptions are documented.
- [ ] Prepare: trusted configuration and statement prerequisites have been checked.
- [ ] Verify: actual candidate proof evidence and required CI checks have been inspected.
- [ ] Publish: use the publication command after merge; include administrator acceptance only with explicit approval and a checked archive.
- [ ] Required new workspace/environment approvals are handled in separate maintenance PRs.

CI generates hashes, internal registration and the candidate catalog. An Issue,
local Lean execution and README result edits are not required.

## Implementation validation (if applicable)

- [ ] `python -m verifier validate`
- [ ] `python -m unittest discover -s tests -v`
- [ ] Relevant real backend CI evidence is linked.

## Review impact

Does this change official statements, definitions, toolchains, policy or the verifier?
Explain which previous review or verification records become stale. Metadata CI
success does not establish proof validity or formal acceptance.
