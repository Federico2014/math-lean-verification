# math-lean-verification technical design

Version: v0.1 (design draft)
Date: 2026-09-08
Repository name: `math-lean-verification`
Scope: reproducible Lean proofs, statement correspondence verification, and public evidence archives for Justin Sun Prize candidates.

> Implementation boundary: this document describes the target design. Registration, non-executing preflight, and the source-only [Lean merge gate](lean-merge-gate.md) are implemented. Broader toolchains and durable formal acceptance are not integrated; see [implementation status](implementation-status.md). Candidate registrations remain pending until the required reviews and verification are complete.

## 1. Design overview

Build a repository where prize maintainers control verification standards, candidates submit proof sources, and GitHub Actions runs isolated verification. Each run pins the original problem version, official formal statement, candidate sources, dependencies, checkers, and policy, producing an independently reproducible evidence package.

The platform must answer both questions:

1. Is the candidate proof valid under the accepted logic, axioms, and checkers?
2. Does its statement faithfully represent the mathematical problem being considered for the prize?

Use two verification layers: independent mathematical review establishes the correspondence between the original problem and the official Lean statement; a protected machine-verification process checks the candidate proof against that statement. Successful compilation, a successful checker exit, or the absence of `sorry` in a source search is insufficient to establish formal verification of the mathematical problem.

The initial full-verification design uses one repository, separate toolchains per problem, and maintainer-triggered runs. Comparator will coordinate statement comparison and proof replay, with Lean's official kernel and Nanoda planned as two independent implementations. Validate and freeze version compatibility, sandbox support, and security baselines during implementation. This design does not promise direct support for every historical Lean project.

This is a design for functionality still to be implemented. Example data, proposed resource limits, and acceptance cases do not establish repository creation, CI execution, mathematical review, or verification of any candidate.

## 2. Basis, goals, and boundaries

### 2.1 Design basis

This design follows the confirmed Justin Sun Prize operating requirements and official Lean/GitHub technical materials. The repository does not publish internal candidate lists, private contact details, or unauthorized materials. Technical capabilities and formal award acceptance are recorded separately.

### 2.2 Rule mapping

| Rule | Platform implementation |
| --- | --- |
| 3.5.1, 3.5.4 | Record original results, prior work, proof strategies, and formalization contributors; technical success does not automatically establish priority or substantive problem-solving contributions |
| 5.6.1 | Archive fixed commits, versions, axiom audits, checkers, execution environments, and actual isolation configurations |
| 5.7.1 | Isolate untrusted code, maintain minimum secure versions, and use at least two independent checker implementations |
| 5.7.2 | Record original sources, review definitions, and freeze official statements; corrections invalidate old statements and require verification again |
| 5.7.3 | Complete all five steps: material inspection, axiom assessment, statement comparison, independent replay, and evidence archiving |
| 5.7.4 | Record conflicts of interest, blind drafting, two-person independence, preference for third-party statements, and public disclosure for retrospective statements |

### 2.3 Goals

- Confirm that target theorems and their transitive dependencies contain no unapproved placeholders or extra axioms.
- Confirm that candidate proofs cover every condition and conclusion of the statement considered for the award.
- Preserve traceable, reproducible evidence that third parties can inspect.
- Allow multiple proof projects for the same problem to be registered and verified independently.
- Show failure reasons, conditional results, and missing materials without presenting unknown states as successful.

### 2.4 Boundaries

CI does not decide prize amounts, recipient identity, first-solution priority, independent contributions, whether conflicts of interest have been substantively resolved, or the mathematical value of a natural-language problem. Separate review processes make these decisions and link them to the records.

The platform does not promise to eliminate every error in mathematical review, logic, checker implementations, sandboxes, operating systems, or hardware. It provides layered evidence under explicit assumptions, not a guarantee of mathematical correctness requiring no trust.

The initial version handles only sources and materials authorized for publication. KYC data, payment details, unpublished contact information, and internal risk assessments must stay out of the public repository. Candidate materials not authorized for publication require a separately designed private process.

## 3. Architecture and trust boundaries

```text
Original literature and exact award scope
          │ Independent review, definition checks, version freeze
          ▼
Official Challenge + review records + policy version
          │
          ├───────────────────────────┐
          ▼                           ▼
Candidate registration           Trusted verifier
and fixed sources                and toolchain
          │                           │
          └─────────────┬─────────────┘
                        ▼
              Isolated build and proof export
                        │ Untrusted exported data
                        ▼
              Trusted statement comparison,
              axiom audit, and independent replay
                        ▼
              Structured report + complete archive
                        ▼
              Acceptance status incorporating
              valid mathematical review records
```

### 3.1 Trusted components

The registration parser, policy, official statements and trusted dependencies, reviewed adapters, verification driver, pinned checkers, sandbox configuration, and result-generation/publishing code on protected branches. Being trusted means these components require maintainer review; it does not exempt them from review or imply they are free of defects.

### 3.2 Untrusted components

Candidate Lean sources, macros, tactics, plugins, build files, bundled dependencies, precompiled files, logs, printed results, exported data, and all user input in PRs and issues. Prior compilation success, a well-known author, or AI generation does not change the execution boundary.

### 3.3 Required invariants

1. Running candidate code cannot access host credentials, repository write tokens, writable checker or official-statement paths, or Actions control files.
2. The verification driver comes from a protected fixed commit; workflow edits in a candidate PR cannot affect that formal run.
3. Prepare official statements in a separate trusted workspace with no writable build artifacts or mutable caches shared with the candidate workspace.
4. Any build, tactic execution, axiom printing, or export that imports candidate modules runs inside the untrusted sandbox.
5. The trusted verifier computes the final status. Candidate-generated `passed` messages, exit wrappers, and badges are not authoritative.
6. Missing data, unknown states, timeouts, malformed output, unsupported checkers, and failed sandbox probes never become passes.

## 4. Statement correspondence: the essential prerequisite

### 4.1 Fix the exact mathematical object

Each `problem_id` identifies a precise problem, with its statement version and award scope recorded. Preserve original literature, publication date, problem-database version, citation location, original formulation, intended proof or refutation, and its relationship to the full conjecture, special cases, and stronger results.

Proving a conjecture, refuting it, and proving one special case are different verification objects. The official Challenge must state the direction explicitly. A stronger result may imply the original problem, but that implication must be included in the verification chain.

### 4.2 Independent drafting and review

For initial candidates whose proofs already exist, apply rule 5.7.4:

1. Confirm the original source and exact scope considered for the prize.
2. Two curators meeting conflict-of-interest requirements separately record their identities, relationship disclosures, materials they have seen, and independent drafting times.
3. Give drafters only the original problem materials, excluding candidate papers, proofs, and formalization code; freeze each completed draft's hash.
4. Compare the drafts publicly only after both are frozen, resolve differences, and review each nonstandard definition, notation, and instance.
5. Prefer an independent third-party statement predating the prize assessment when available, while still checking its provenance, independence, definitions, and dependency versions.
6. Publish the final statement, participants, dates, sources, resolutions, and approval records.

Code hosting can preserve timestamps, draft hashes, and review comments. It cannot independently establish that someone has never seen candidate materials; authenticity requires accountable disclosures and review. Two model sessions alone do not satisfy independence, conflict-of-interest, or blind-drafting requirements.

### 4.3 Correspondence table

Every submission must reference the problem-level `correspondence.md`, covering at least the following dimensions. Use explicit conclusions such as "satisfied", "not satisfied", or "pending verification"; blanks must not default to satisfied.

| Dimension | Checks | Typical mistake |
| --- | --- | --- |
| Problem identity | Literature, version, identifier, disputed wording | Confusing different problems with the same name or choosing the wrong formulation |
| Domain | Number system, space, object class, dimension | Replacing reals with rationals or arbitrary dimensions with one fixed dimension |
| Quantifiers | Universal/existential, order, finite/infinite | Replacing all objects with the existence of one object |
| Assumptions | Original conditions, implicit conditions, nonemptiness | Adding unauthorized hypotheses or contradictory premises that make the claim vacuous |
| Conclusion | Strength, constants, limits, optimality | Substituting finite experiments for asymptotic or infinite-existence results |
| Definitions | Every nonstandard definition and public definition version | Changing meaning through same-name functions, overloaded operations, or typeclass instances |
| Proof direction | Positive proof, counterexample, equivalence | Confusing proof with refutation or proving an insufficient direction |
| Contribution scope | First solution, new counterexample, generalization, formalization | Registering the formalization of an old proof as a recent first solution |

### 4.4 Machine-checkable relationships

Use Comparator to compare target statements and related declaration dependencies between the trusted Challenge and candidate Solution, audit actual proof dependencies, and replay proofs. Capabilities and configuration depend on the pinned version; validate cases such as malicious same-name definitions during implementation. This assumes the Challenge and its import environment are trusted. [Comparator documentation](https://github.com/leanprover/comparator)

If candidate and official statements use encodings the tool cannot directly match, maintainers must review an adapter and provide a Lean bridge deriving the complete official statement from the candidate theorem. Claims of equivalence require both directions. The bridge and all dependencies also undergo axiom auditing and dual-checker replay.

The initial version does not let candidates fill arbitrary `Prop` definitions or other definition holes in official statements, which could make a target trivially true. Definition holes require a separate future design.

### 4.5 Challenge placeholders versus candidate placeholders

Some Comparator integration modes allow a trusted Challenge to use `sorry` for a proof target. This is a statement-template mechanism, not permission for incomplete candidate proofs. Manage templates separately; final Solution targets and their transitive proof dependencies must neither borrow Challenge placeholders nor contain `sorryAx`. Repository-wide `sorry` searches are diagnostic only, not the final criterion.

### 4.6 Version invalidation

Approval records bind hashes of original snapshots, Challenge, definitions, trusted dependencies, and policy versions. Changes require reassessing whether the previous review still applies. Official statement corrections invalidate the old version and require republication and verification under the rules.

A candidate-only source change does not automatically require rewriting the original problem, but it does require reverification of that candidate and renewed checks of its adapter and contribution scope. Whether a formatting-only change preserves mathematical review must be established in a protected diff-review record, not by the submitter's own assertion.

## 5. Repository structure and data model

```text
math-lean-verification/
├── README.md
├── CONTRIBUTING.md
├── SECURITY.md
├── LICENSE
├── docs/design.md
├── policy/
│   ├── verification.md
│   ├── axioms.json
│   └── toolchains.json
├── schemas/
│   ├── submission.schema.json
│   ├── review.schema.json
│   └── result.schema.json
├── problems/<problem-id>/<statement-version>/
│   ├── statement.md
│   ├── correspondence.md
│   ├── Challenge.lean
│   ├── definitions.md
│   ├── review.json
│   └── toolchain.lock.json
├── submissions/<problem-id>/<submission-id>.json
├── adapters/<adapter-id>/
├── verifier/
│   ├── intake.py
│   ├── prepare.py
│   ├── verify.py
│   └── report.py
├── tests/fixtures/
├── records/<problem-id>/<run-id>/
└── .github/
    ├── CODEOWNERS
    ├── ISSUE_TEMPLATE/
    └── workflows/{intake,verify,publish}.yml
```

These are proposed interfaces, not a description of the current implementation. Store large source snapshots, complete logs, and exported proofs in durable evidence storage; Git holds structured summaries, hashes, and stable indexes.

### 5.1 Core entities

| Entity | Required fields |
| --- | --- |
| Problem | `problem_id`, original sources and snapshots, claim direction, scope, `statement_version`, Challenge and definition hashes |
| Review | Reviewers and roles, conflict disclosures, independent draft hashes, blind-drafting materials, resolution of differences, approval status, approved-content hash |
| Submission | `submission_id`, problem version, upstream URL, full commit, target modules and theorems, source directory, adapter, proof strategy, intended public attribution |
| Toolchain | Lean version and source commit, Mathlib and all dependency commits, tool binary hashes, checker commits, image digest, security policy version |
| Run | Input-set digest, verifier commit, run ID, initiator, time, machine architecture, resource limits, stage results, and exit reasons |
| Record | Per-theorem results, axiom sets, statement matches, dual-checker results, evidence-package hash and URI, review references, current acceptance status |

All commits must use complete fixed identifiers. Mutable references such as `main` and `latest` are not formal verification inputs. When applying adapter patches, preserve both original sources and patches and state explicitly that the adapted version was verified. Do not attribute that result directly to unverified upstream sources.

A candidate may declare multiple required target theorems. Every target and bridge must pass before the candidate receives an overall machine-passed status. Maintainers approve the target list; submitters cannot remove difficult targets to obtain a green status.

## 6. CI pipeline

### 6.1 Intake: register materials

Issue forms collect public source URLs, commits, problems, modules, theorems, papers, and intended attribution. PR checks validate structure, fields, and directory changes without building candidate projects.

Use strict schemas, field lengths, and enums. Reject unknown executable configuration, path traversal, escaping symlinks, and shell fragments. Initially accept only validated public GitHub HTTPS repository URLs. Dependency sources must be separately locked and explicitly allowed.

Maintainers approve registration and adapter configuration before merging into a protected branch. Merging a candidate registration into the default branch does not make candidate source trusted.

### 6.2 Plan: create an immutable execution request

Maintainers trigger full verification from the default branch using `workflow_dispatch`, supplying only a registered candidate ID and configuration version. A trusted scheduler resolves all fixed commits, creates the execution request and input hash, and binds the problem, reviews, sources, adapters, toolchain, and policy.

Do not resolve mutable branches again during verification. Retries use the same inputs with a new run ID. Limit concurrency; subsequent submissions do not overwrite earlier run results.

### 6.3 Prepare: obtain materials

The online stage downloads only fixed sources, required dependencies, and approved tools. It does not execute candidate build files, hooks, download scripts, or binaries. Check archive extraction, submodules, file counts, sizes, and paths. Remove credentials and `.git` metadata to produce a workspace containing only approved inputs.

Pin Mathlib and candidate dependencies to exact sources. Unknown dependencies, recursive submodules, and Git LFS objects must not be fetched implicitly online. List them explicitly in the material manifest or stop with incomplete materials.

### 6.4 Sandbox: build and export

Use a disposable workspace for each candidate. Trusted build adapters generate or review Lake configuration; never execute upstream `lakefile.lean` directly on the host. Any candidate configuration and plugins that must execute remain sandboxed code.

Formal verification rejects submitter-provided `.olean` files, shared `.lake` build caches, and precompiled native libraries. Rebuild Mathlib and candidate dependencies from source. Maintainers provide the base toolchain and record its source version, binary digest, and build provenance. Disclose its bootstrap trust; do not claim every CI run bootstraps the compiler from scratch.

Only sandboxed build/export tools may read candidate-generated `.olean` files. Pass only prescribed exported data to later checks; never import candidate `.olean` files on the trusted publishing host.

### 6.5 Check: axioms, statements, and replay

In a trusted verification environment isolated from candidate execution, validate export format, correspondence to the official statement, and transitive axiom dependencies, then run approved independent replay checks. Exports remain untrusted data: bound their size, structure, parsing resources, and checker permissions.

The initial dual-checker plan uses Lean's official kernel and Nanoda; verify that both cover every target and required dependency. Comparator coordinates verification and is not a third kernel. `lean4checker` reuses Lean's kernel and is not another independent implementation. [Lean proof validation guide](https://lean-lang.org/doc/reference/latest/ValidatingProofs/)

Keep `#print axioms` output as evidence and diagnostics. The final verdict comes from the trusted chain checking actual exported proofs, not from parsing candidate build stdout alone.

### 6.6 Archive: preserve evidence and compute status

The trusted driver generates canonical results. Save the complete evidence package and verify readback hashes before publishing a summary. Archive failure prevents final `formal_verified` status.

A separate publishing job accepts only strictly validated data and never executes evidence-package scripts or imports Lean modules. It validates allowed workflow origins, run ID, verifier commit, complete input digest, and all check results. Grant only the minimal publishing permissions; candidate execution jobs never receive publishing authority.

## 7. GitHub and execution security

### 7.1 Execution environment

The initial design uses ephemeral GitHub-hosted Linux runners plus explicit process, filesystem, and network isolation. Runner ephemerality does not itself isolate candidate execution, and an ordinary Docker container is not sufficient evidence of isolation.

Use a reviewed Landrun/container or another isolation combination. Validate compatibility and escape-related probes before adopting it. Fail closed when required host capabilities are missing; never fall back to unsandboxed execution. Review Comparator's sandbox prerequisites, version-specific limitations, and mitigations with the pinned version. [Comparator documentation](https://github.com/leanprover/comparator)

| Boundary | Design requirement |
| --- | --- |
| Network | Disable network access during execution, including IPv4, IPv6, DNS, loopback, and unauthorized Unix sockets |
| Identity | Non-root, no privilege escalation, no host Docker socket |
| Files | Read-only inputs and a separate writable output directory; no writes to official statements, checkers, or host directories |
| Processes | Isolate host processes, environment variables, and credential files; deny access to host Actions file-command channels |
| Resources | Limit wall time, memory, CPU, process count, disk, logs, and export size |
| Caches | No candidate-supplied or cross-job mutable build caches for formal verification |
| Probes | Verify network/file/credential boundaries and effective limits before every run; abort on probe failure |

The proposed starting configuration is one workspace per candidate and at most two concurrent full verifications. Measure timeouts and memory requirements on pilots before recording protected resource tiers. Heavy proofs may use reviewed larger tiers. Insufficient resources mean verification is incomplete, not that the theorem is false.

### 7.2 Repository permissions

- Protected branches require PRs and the reviews appropriate to the operation; assign CODEOWNERS for policy, Challenge, adapters, verifier, and workflows. See the [maintainer runbook](maintainer-runbook.md) for current registration merge settings.
- CODEOWNERS only enforces a boundary when corresponding branch rules require its review.
- Record mathematical statement approvals separately from infrastructure code approvals. A generic PR approval cannot replace both.
- Verification jobs receive only necessary read permissions. Disable checkout credential persistence and do not mount Actions environments or tokens in the sandbox.
- Pin every Action to a full commit and every image to a digest. Revalidate negative cases after tool or policy changes.
- Do not execute external PR code with `pull_request_target` or let a write-enabled `workflow_run` consume and execute candidate artifacts.
- Publishing code must escape Markdown/HTML and filenames and limit displayed content size.

These boundaries follow the official documentation and are explicit platform implementation requirements. [GitHub Actions security reference](https://docs.github.com/en/actions/reference/security/secure-use)

## 8. Axiom and version policy

### 8.1 Axiom assessment

The initial standard path allows `propext`, `Classical.choice`, and `Quot.sound`. Prize maintainers must publish and version the actual allowlist. The empty set or any subset may pass; a proof need not use all three axioms.

| Condition | Handling |
| --- | --- |
| Target dependencies contain `sorryAx` | `proof_incomplete`; reject acceptance |
| Only published standard axioms are used | Continue statement comparison and independent replay |
| Custom axioms or extra computational trust appear | `extra_assumptions`; specialized review, without automatically expanding the allowlist |
| A checker does not support the proof construct or version | `unsupported`; do not present it as proof failure or success |
| Logs are missing or tool output cannot be parsed | `verification_error`; no pass |

Prize rules allow individual review of custom axioms. The initial version automatically accepts only the standard-axiom path. Exceptions require assessment of assumption meaning, literature evidence, relationship to the official statement, and policy grounds. A human checkbox accepting an axiom cannot turn an unproved assumption of the original problem into an unconditional proof. Any applicable exception must be explicitly disclosed in the conclusion and must preserve official-statement correspondence requirements.

### 8.2 Version freezing and updates

Each problem may use a different approved Lean/Mathlib combination. Execution tools, exporters, and checkers must be compatible and satisfy current security policy. Pinning an old version aids reproducibility but does not establish perpetual eligibility for acceptance.

The rules require current released checkers and minimum secure versions. Preserve version-policy snapshots and corresponding upstream release records, and publish the approved list before launch. After checker upgrades, run positive and negative regressions, then rerun affected candidates. If the latest approved checker cannot handle an old project, report `unsupported` or `recheck_required`; never silently use a revoked version to preserve a pass.

Lean/Mathlib migrations may change definitions or adapters. Review the differences and rebind statement review records. Preserve historical verification facts and display both the result at the time and its current acceptance status.

## 9. Status model and acceptance criteria

### 9.1 Separate status dimensions

| Dimension | Proposed values |
| --- | --- |
| Materials | `incomplete`, `ready` |
| Statement review | `pending`, `approved`, `rejected`, `invalidated` |
| Machine verification | `not_run`, `running`, `passed`, `failed`, `timeout`, `unsupported`, `error` |
| Axioms | `standard_only`, `extra_assumptions`, `proof_incomplete`, `unknown` |
| Archive | `pending`, `complete`, `failed` |
| Formal acceptance | `pending`, `formal_verified`, `not_accepted`, `recheck_required`, `withdrawn` |
| Award eligibility | Separately maintained external review status and record links |

Record results per theorem and aggregate all required targets into the project status. Successful workflow orchestration means only that the program completed, not that machine verification or formal acceptance passed. A formal required check must reflect the aggregate verdict rather than merely successful report generation.

### 9.2 Initial formal acceptance criteria

```text
formal_verified =
  evidence_complete
  AND statement_review_approved_for_exact_input
  AND clean_build_passed
  AND all_required_theorems_match_challenge
  AND all_required_proofs_use_only_standard_axioms
  AND official_kernel_passed
  AND independent_kernel_passed
  AND sandbox_policy_passed
  AND versions_accepted_by_current_policy
  AND archive_complete_and_readback_verified
```

A trusted process generates these fields and binds them to immutable inputs and reviewed content. Adding identically named booleans to submission JSON grants no approval. Custom-axiom exceptions are outside this automatic formula and require a finalized exception policy and human decision.

Even `formal_verified` does not automatically establish recipient identity, priority, dimension-C independence, or prize amount. In particular, replay on two kernels is not equivalent to two independent academic validation channels qualifying under scoring dimension C.

## 10. Evidence packages, public presentation, and reproduction

### 10.1 Evidence package contents

- Original sources and authorized snapshots, official statement version, correspondence documentation, and nonstandard-definition review.
- Review records, draft hashes, approved-content hashes, relationship disclosures, and public attribution materials.
- Fixed commits for upstream sources and all dependencies, authorized source snapshots, adapters, and patches.
- Versions, commits, and digests of Lean, Mathlib, checkers, exporters, verifier, and images.
- All target theorems, actual formal statements, transitive axiom lists, and statement-comparison results.
- Clean-build logs, exported proofs, both checker results, exit codes, and error classifications.
- Machine architecture, actual sandbox configuration, probe results, resource limits, times, and run ID.
- `result.json`, complete file checksum manifest, archive index, and content hashes.

### 10.2 Storage and retention

Git holds small summaries, policies, reviews, and indexes. Complete evidence packages use object storage or release attachments with a durable retention policy and independent backups. Select the provider and retention policy before launch; temporary Actions artifacts cannot be the only formal archive.

Publication and redistribution of source snapshots must comply with upstream licenses and preserve attribution. Resolve archive authorization when licensing is absent. Saving a URL alone does not establish complete archival of the materials.

File hashes verify integrity but do not establish who generated a conclusion. Traceability requires jointly binding protected workflows, fixed versions, run identities, and publication records. Signatures and artifact attestations may strengthen this later, but cannot replace verification itself.

### 10.3 Presentation and reproduction

README/GitHub Pages should show candidate projects by problem, including source commits, statement versions, machine results, statement reviews, acceptance status, latest verification time, and evidence links. A green repository badge must not imply that all candidates have passed.

The following local interfaces are planned, not currently executable:

```text
verify submission <submission-id> --input-lock <lock-file>
verify replay <record-id> --mode historical
verify replay <record-id> --mode current-policy
```

Historical reproduction replays fixed inputs and identifies the original security policy. Reverification under current policy creates a new record. Both modes require the same isolation; historical reproduction does not justify directly executing old proof code on the host.

## 11. Candidate onboarding strategy

Bootstrap starts with no candidates. Add candidates later through issues and registration PRs, testing the system with temporary synthetic examples before selecting authorized real projects. Register different proof projects for the same problem separately. Distinguish conditional results, prior work, special cases, and first solutions to the original problem.

## 12. Acceptance tests

### 12.1 Mathematics and statement correspondence cases

| Case | Expected result |
| --- | --- |
| Complete proof covers the official target and all reviews are valid | Eligible for `formal_verified` after archiving |
| Same theorem name but conclusion changed to `True` | Statement mismatch |
| Added `False` or unauthorized premise | Complete approved proof cannot derive the official target; no pass |
| Universal changed to existential, infinite to finite, or real to rational | Statement mismatch or human-review rejection |
| Same-name definitions/typeclass instances change meaning | Dependency comparison or review rejects |
| Mathematically equivalent but differently encoded | Pass only after a verified bridge is supplied |
| Only some required targets completed | Show completed theorem-level results, but no overall pass |
| Candidate proof depends on the official Challenge placeholder | Axiom audit detects incompleteness; no pass |
| Unrelated files contain `sorry` | Report separately; source searches do not replace target-dependency analysis |

### 12.2 Axiom and infrastructure cases

| Case | Expected result |
| --- | --- |
| Target indirectly depends on `sorryAx` | `proof_incomplete` |
| Custom unproved axioms or computational trust beyond policy | `extra_assumptions`; no automatic acceptance |
| One checker passes and another fails or is unsupported | No overall pass; preserve the discrepancy |
| Candidate prints forged axiom lists or `passed` | No effect on the trusted verdict |
| Malicious `.olean` or old caches supplied | Never loaded on the trusted host; rebuild from source |
| Attempts to network, read tokens, or write official statements or Actions control files | Block and record; abort the entire run if sandbox probes fail |
| Path traversal, escaping links, invalid URLs, or shell injection | Intake/Prepare rejection |
| Memory, process, disk, log, or time exhaustion | Resource/execution failure; no pass |
| Forged/replaced result package or old report reused across commits | Input-digest or provenance validation failure |
| PR workflow edits alone try to bypass verification | Formal verification still uses the protected verifier |
| Definitions/trusted dependencies change after approval | Old approval invalidated; renewed review required |
| Checker security version revoked | Preserve historical record; current status requires rechecking |
| Evidence package lost, corrupted, or fails readback | No final formal acceptance |

These are required system acceptance tests, not substitutes for reviewing candidate mathematics. The initial full-verification version must include automated positive and negative regressions and at least one manual statement-correspondence exercise.

## 13. Implementation phases and deliverables

| Phase | Main deliverables | Completion criteria |
| --- | --- | --- |
| P0: Rules and baseline | Final design, publication scope, roles, draft toolchain and axiom policies | Clarify formal acceptance versus technical reproduction; choose pilot inputs and responsibilities |
| P1: Reproducible verifier | Local CLI, trusted Challenge mode, sandbox, dual checkers, structured results | A small valid proof passes and all core negative cases are correctly rejected |
| P2: GitHub CI | Forms, schemas, protected workflows, permissions, evidence archiving | A run binds all versions, archives pass readback, and local replay works |
| P3: Real candidate pilot | Onboarding report and statement-review materials for a future selected pilot | Pilot completes technical verification; only candidates with complete materials proceed to formal acceptance |
| P4: Multiple projects and expansion | Multiple projects per problem, separate eligibility, conditional-result presentation | Accurate multi-target and conditional statuses, followed by resource-based expansion |

Trigger full verification manually at first to prevent public submissions from immediately consuming large amounts of compute. Measure pilot build times, peak memory, export sizes, failure retries, and storage growth before deciding automatic triggers and budgets. Do not promise fixed durations or costs without measurements.

## 14. Decisions required before launch

1. Repository owner/organization, visibility, administrators, mathematical reviewers, and infrastructure reviewers.
2. Supported Lean/Mathlib/exporter/checker combinations, recognition of independent implementations, minimum secure versions, and update process.
3. Sandbox capabilities, resource tiers, workflow permissions, and probe results in the actual execution environment.
4. Original-literature snapshots, two-person blind-drafting and conflict disclosures, official statements, and definition reviews.
5. Evidence storage, retention, backups, source redistribution authorization, and publication scope.
6. Review responsibilities and public wording for custom-axiom exceptions; until established, only the standard-axiom path is eligible for automatic acceptance.

These decisions affect formal launch and acceptance. They do not prevent initial implementation of the local verifier, registration schemas, and negative fixtures.

## 15. Technical references

Reference review date: 2026-09-08. Web pages and default branches change; freeze the adopted tool versions, source snapshots, and policy during implementation.

- [Lean: Validating a Lean Proof](https://lean-lang.org/doc/reference/latest/ValidatingProofs/): distinguishes building, axiom checks, replay, and trusted statement verification.
- [Comparator](https://github.com/leanprover/comparator): trusted Challenges, statement comparison, export replay, external checkers, and sandbox prerequisites.
- [lean4checker](https://github.com/leanprover/lean4checker): additional replay using Lean's kernel.
- [lean-eval security model](https://github.com/leanprover/lean-eval/blob/main/SECURITY.md): reference for separating trusted problems from untrusted submissions.
- [lean-eval-submissions security model](https://github.com/leanprover/lean-eval-submissions/blob/main/SECURITY.md): reference for fixed inputs, submission handling, and execution boundaries; its cache and private-material policies do not replace prize rules.
- [GitHub Actions security reference](https://docs.github.com/en/actions/reference/security/secure-use): workflow permissions, external input, dependency pinning, and runner security.

This design uses the documented capabilities of those components and separately defines prize workflows, status models, storage, and acceptance criteria. Reusing an upstream project does not automatically satisfy prize rules.
