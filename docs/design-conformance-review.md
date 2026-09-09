# Design conformance review

Reviewed on 2026-09-09 against repository commit
`06d943034de9cfb196feb8d4517dc3499459ae04` and version 2 of the
[Lean design baseline](https://troneco.atlassian.net/wiki/spaces/javatronx/pages/2442231810/Lean).
This report describes the implementation and the accompanying local corrections.
It does not approve an environment, a mathematical reviewer or an award candidate.

## Verdict

The architecture substantially follows the design, but the system has not met its
full pilot and formal-acceptance criteria. The actual registry has zero problems
and zero submissions. Working synthetic infrastructure tests must not be presented
as completed real-candidate verification.

The protected controller, isolated execution, statement comparison, axiom policy,
independent replay and status publication are meaningful implemented components.
Replacing them with another custom verification framework would add duplication.
The next substantial work should be pilot integration, evidence operations and
revalidation of existing candidates when trusted inputs change.

## Requirement coverage

| Design requirement | Implementation evidence | Assessment |
| --- | --- | --- |
| Protected-base controller and separate publisher | `lean-verification.yml`, `merge_gate.run`, `gate_status.py` | Implemented; publisher uses trusted job outcomes rather than candidate artifacts |
| Fixed source commit and bounded source mapping | `GitHub.tree/blob`, `candidate_sources` | Implemented; blob identities, paths, file modes, hashes and budgets are checked |
| Trusted Challenge and mathematical correspondence | `check_problem`, `prerequisites`, workspace digests | Implemented mechanism; reviewer accreditation and real problem reviews remain absent |
| Reusable pinned environments | `environments.py`, `build_environment.py`, two descriptors | Implemented for the admitted scope; Mathlib cache coverage is deliberately narrow |
| Safe static environment discovery | `inspect_project`, `discover` | Implemented advisory matching; dynamic Lake requirements still need manual review |
| All required targets, statement match, accepted axioms, Lean and independent replay | `verify`, `GateReplay.lean`, Nanoda invocation | Implemented and supported by actual synthetic backend runs; not a real-candidate acceptance claim |
| Non-root offline execution with bounded resources | `sandbox`, `probe.py`, seccomp policy | Implemented runtime restrictions and probes; infrastructure evidence remains specific to tested environments |
| Stable fail-closed merge gate | Matrix aggregation and status publisher | Required GitHub checks were confirmed; unknown, failed, cancelled and skipped required jobs cannot pass |
| Version-bound results and diagnostics | Result bindings, input digests, sealed evidence | Implemented; accompanying changes preserve candidate-level bindings for early failures too |
| Uniform failure categories and readable reports | Controller and backend result handling | Improved in this patch; conditional assumptions and per-theorem axiom inventories remain incomplete |
| Trusted changes invalidate and rerun affected candidates | Candidate selector and current-base check | Partial; global policy/controller changes do not automatically revalidate merged candidates |
| Durable archive and recovery | `evidence.py`, temporary Actions artifacts | Integrity/readback implemented; durable storage, retention and recovery operations remain unconfigured |
| Real Erdős 650, DGG and Erdős 90 pilots | Empty problem/submission registry | Not completed |
| Peak memory, disk and export-size telemetry | Resource limits, stage duration, export files | Partial; resource limits are not actual peak measurements |

## Corrected defects and redundancy

1. **Missing registered upstream declarations could still pass.** A real
   reproduction with a valid official proof and `solution_declarations` containing
   a nonexistent `missing_upstream` returned `machine_status: passed`. The exporter
   silently omitted the unknown name, while Comparator's original target list
   covered only official theorems. The independent checker checked the available
   export without knowing which additional declarations were required. The clean
   checker now uses upstream `Export.parseStream` to require every declared target
   and upstream `Comparator.checkAxioms` to audit its closure, before statement
   comparison and both kernel replays. Two actual backend regressions cover a
   missing upstream declaration and a declared upstream theorem depending on
   `sorryAx`. This hole bypassed candidate target coverage; it did not establish
   an ability to prove a false official Challenge statement.
2. Static discovery could suggest a stdlib environment when a TOML dependency was
   absent from an otherwise valid empty lock. It also ignored a dynamic Lake file
   when a TOML file existed alongside it. Both situations now produce warnings and
   suppress automatic matches. Malformed dependency field types now produce normal
   validation errors instead of uncaught regular-expression type errors.
3. Candidate retrieval did not check whether each declared target module was in
   the selected source set. It now rejects omitted target modules before execution.
   This complements the backend's declaration checks; it does not claim to prove
   author attribution or implement an independent Lean import parser.
4. Candidate selection compared only submissions and problem records. It now also
   compares referenced environments and effective policies. Unreferenced environment
   changes do not rerun unrelated candidates. This is selection logic, not the
   missing global revalidation workflow described below.
5. Early source/prerequisite failures discarded version identity, and sandbox
   exceptions omitted the failed stage's execution metadata. Candidate-level
   failures now retain identity and required targets, plus JSON and English reports.
   Interrupted stages retain command, duration and error; partial stdout is still
   unavailable. Unsupported execution profiles and runtime failures have distinct
   non-passing categories. Classification comes from controller errors/exit codes,
   never keyword searches in candidate output.
6. Removed the unused `checked` helper, `MAX_EXPORT`, `VERSION` and unused imports.
   Comparator and Nanoda now derive the same axiom list from the registry's
   `STANDARD_AXIOMS`. The legacy backend path and `GateReplay.lean` remain: the
   former is documented compatibility, and the latter delegates to upstream
   Comparator rather than duplicating its proof checker.

## Outstanding work, in priority order

1. **Complete one real pilot, then demonstrate cross-version reuse.** Fix exact
   source commits, licenses, all target declarations, problem workspaces and
   mathematical review records. Expand Mathlib cache coverage only with real
   compatibility and resource evidence. Do not enable formal acceptance from
   synthetic regression results.
2. **Add protected revalidation for trusted maintenance changes.** The current
   selector runs against PR registry data while policy is intentionally copied
   from the protected base. Global verifier/workflow changes can receive
   `not_applicable`; a later manual PR rerun still selects only changed candidates.
   Add a separate protected-base maintenance/revalidation entry point that follows
   references and records new results without rewriting historical acceptance.
   Testing the old controller against unchanged candidates would not validate a
   proposed new controller, so this patch does not add a misleading green rerun.
3. **Configure durable evidence storage and test restoration.** A SHA-addressed ZIP
   and a 90-day Actions artifact are not a persistent archive. Choose retention,
   access control, provenance/license handling and recovery operations before
   formal acceptance is activated.
4. **Finish the result/evidence contract.** Add a versioned result schema,
   Issue/PR/run links, per-theorem checker outcomes and actual axiom inventories,
   independently supported conditional classifications, peak resource telemetry,
   and executable local reproduction instructions. The current image ID records
   the executed image but the environment descriptor does not pin a distributable
   OCI runtime digest; pinning and retaining that image would improve restoration.
5. **Review the deployed maintenance trust controls.** At review time, `main`
   required strict `registry`, `tests` and `lean-verification` checks and enforced
   them for administrators. GitHub approving-review count was zero and CODEOWNERS
   review was not required. This permits the configured self-merge workflow, but
   it does not itself enforce independent review of trusted verifier changes.
   Mathematical reviewer accreditation remains a separate policy mechanism.

## Validation evidence

- Python 3.12 baseline: 69 unit tests passed and registry validation passed.
- After these corrections: 77 unit tests passed, including failure evidence,
  environment matching, omitted target modules and affected-candidate selection.
- The corrected Lean wrapper compiled against the pinned Comparator. A local
  Core/Std run passed all 15 actual proof/sandbox cases, including both new
  registered-target regressions, using image
  `sha256:e38a3dacc554923e130f70a873614c253f75b5dc82e25d14b29da25133f80dd1`.
  The Mathlib matrix was not rerun locally for this patch; it must run in backend
  CI before the changed checker is admitted for that environment.
- Actual existing cross-version onboarding was independently checked through the
  GitHub API: [run 34230107878](https://github.com/Federico2014/math-lean-verification/actions/runs/34230107878)
  completed successfully at `f6850defaa4a23ab89736adea620f30f0257878d`.
  Its documented scope is 27 synthetic cases across the two admitted environments.
- This patch adds no real registration, reviewer accreditation, formal archive,
  remote status, repository setting change or acceptance record.

To rerun the corrected Core/Std matrix from this checkout with Python 3.12 and
the repository's development dependencies installed:

```bash
docker build -t lean-gate-review backend
LEAN_REVIEW_IMAGE=$(docker image inspect lean-gate-review --format '{{.Id}}')
python scripts/backend_smoke.py --image "$LEAN_REVIEW_IMAGE" --output /tmp/lean-review-evidence
python -m unittest discover -s tests -v
python -m verifier validate
```

Use a new evidence output directory on each run. The existing **Lean backend
tests** workflow runs both reusable environments and includes the two new cases
automatically; its matrix therefore contains 15 Core/Std and 16 Mathlib cases.
