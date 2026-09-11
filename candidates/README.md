# Submit a Lean candidate

Copy `templates/candidate.json` into this directory as `<candidate-id>.json`,
complete the source, targets and attribution, confirm publication permission,
and open one PR against `main`. An issue is optional.

CI prepares the registration and bridge, matches a protected problem and approved
environment, and verifies the proof. Waiting prerequisites appear in the plan;
maintainers prepare them separately and the open PR resumes automatically after
`main` updates. Do not edit workflows, approval policy, hashes or README status.

Use `python -m verifier candidate submit <id> <file> --repository OWNER/REPO` to
validate materials and open the candidate PR together. Follow the four-stage
[operator lifecycle](../docs/candidate-lifecycle.md); trusted configuration and
publication changes remain separate from candidate-controlled files.
