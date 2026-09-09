"""Validate registry data without fetching or executing candidate code."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_REGISTRY_FILES = 5000
ID = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
MANDATORY_FILES = {"Challenge.lean", "statement.md", "correspondence.md", "definitions.md"}
STANDARD_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}


class RegistryError(ValueError):
    """Invalid input or a registry invariant violation."""


class VerificationError(RegistryError):
    """A controller-classified failure; never infer a verdict from candidate logs."""

    def __init__(self, message: str, status: str):
        if status not in {"failed", "unsupported", "infrastructure_error", "not_run"}:
            raise ValueError("Invalid failure classification")
        super().__init__(message)
        self.status = status


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RegistryError(message)


def safe_file(root: Path, relative: str) -> Path:
    """Reject traversal and every symlink, including in a parent directory."""
    part = PurePosixPath(relative)
    require(bool(relative) and "\\" not in relative, "Invalid relative path")
    require(not part.is_absolute(), "Absolute paths are forbidden")
    require(all(p not in ("", ".", "..") for p in relative.split("/")), "Unsafe path component")
    require(all(re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.-]*", p) for p in part.parts), "Unsupported path characters")
    current = root.resolve()
    for piece in part.parts:
        current /= piece
        require(not current.is_symlink(), "Symlinks are forbidden")
    require(current.is_file(), f"Missing regular file: {relative}")
    require(current.stat().st_size <= MAX_INPUT_BYTES, "Input exceeds size limit")
    return current


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in data, "Duplicate JSON key")
        data[key] = value
    return data


def _constant(value: str) -> None:
    raise RegistryError("Non-finite JSON numbers are forbidden")


def read_json(path: Path) -> Any:
    require(not path.is_symlink() and path.is_file(), "JSON must be a regular file")
    require(path.stat().st_size <= MAX_JSON_BYTES, "JSON exceeds size limit")
    try:
        with path.open(encoding="utf-8") as stream:
            return json.load(stream, object_pairs_hook=_pairs, parse_constant=_constant)
    except (json.JSONDecodeError, UnicodeDecodeError, RecursionError) as exc:
        raise RegistryError("Invalid JSON encoding or structure") from exc


def schema_validate(kind: str, data: Any) -> None:
    # Schemas always come from the verifier checkout, never a candidate root.
    schema = read_json(ROOT / "schemas" / f"{kind}.schema.json")
    Draft202012Validator.check_schema(schema)
    errors = list(Draft202012Validator(schema).iter_errors(data))
    if errors:
        error = errors[0]
        location = "/".join(str(x) for x in error.absolute_path) or "root"
        # Do not echo arbitrary candidate-controlled contents into CI output.
        raise RegistryError(f"{kind}: schema violation at {location} ({error.validator})")


def canonical_digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def data_files(root: Path, folder: str) -> list[Path]:
    base = root / folder
    require(base.is_dir() and not base.is_symlink(), f"Missing registry directory: {folder}")
    files = []
    for index, path in enumerate(base.rglob("*")):
        require(index < MAX_REGISTRY_FILES, "Registry exceeds file limit")
        require(not path.is_symlink(), f"Symlink in {folder}")
        if path.is_file():
            safe_file(root, path.relative_to(root).as_posix())
            if path.suffix == ".json":
                files.append(path)
    return sorted(files)


def read_policy(root: Path) -> dict[str, Any]:
    policy = read_json(safe_file(root, "policy/verification.json"))
    schema_validate("policy", policy)
    require(set(policy["standard_axioms"]) == STANDARD_AXIOMS, "Unexpected standard axiom policy")
    reviewers = policy["approved_reviewers"]
    require(len({x.lower() for x in reviewers}) == len(reviewers), "Duplicate reviewer identity")
    exceptions = policy.get('administrator_exceptions', [])
    keys = [(e['problem_id'], e['statement_version']) for e in exceptions]
    require(len(set(keys)) == len(keys), 'Duplicate administrator exception scope')
    return policy


def statement_digest(problem: dict[str, Any]) -> str:
    # Bind meaning, all trusted files, target list, and environment selection.
    return canonical_digest({key: value for key, value in problem.items() if key != "review"})


def review_approval_kind(review):
    if review['status'] != 'approved':
        return 'unapproved'
    return review.get('approval_kind', 'independent_review')


def check_problem(root: Path, path: Path, policy: dict[str, Any]) -> dict[str, Any]:
    data = read_json(path)
    schema_validate("problem", data)
    expected = root / "problems" / data["problem_id"] / data["statement_version"] / "problem.json"
    require(path == expected, "Problem identity does not match its directory")
    declared = {item["path"]: item["sha256"] for item in data["trusted_files"]}
    require(len(declared) == len(data["trusted_files"]), "Duplicate trusted-file path")
    require(MANDATORY_FILES <= set(declared), "Missing mandatory statement files")
    for relative, digest in declared.items():
        require(relative != "problem.json", "problem.json cannot hash itself")
        file = safe_file(path.parent, relative)
        require(file_digest(file) == digest, "Trusted-file hash mismatch")
    actual = set()
    for file in path.parent.rglob("*"):
        require(not file.is_symlink(), "Symlink in statement package")
        if file.is_file() and file != path:
            actual.add(file.relative_to(path.parent).as_posix())
    require(actual == set(declared), "Unbound file in statement package")
    review = data["review"]
    if review["status"] == "approved":
        require(review["statement_digest"] == statement_digest(data), "Stale statement review")
        if review_approval_kind(review) == 'administrator_exception':
            require(not review['reviewers'], 'Administrator exception cannot claim independent reviewers')
            matches = [e for e in policy.get('administrator_exceptions', [])
                       if e['problem_id'] == data['problem_id']
                       and e['statement_version'] == data['statement_version']
                       and e['statement_digest'] == review['statement_digest']
                       and e['administrator'] == review.get('administrator')
                       and e['evidence_url'] == review['evidence_url']]
            require(len(matches) == 1, 'Missing exact protected administrator authorization')
        else:
            require('administrator' not in review, 'Administrator identity requires an explicit exception')
            reviewers = {x.lower() for x in review["reviewers"]}
            allowed = {x.lower() for x in policy["approved_reviewers"]}
            require(len(reviewers) == len(review["reviewers"]), "Duplicate review identity")
            require(len(reviewers) >= policy["minimum_independent_reviewers"], "Two distinct reviewers required")
            require(reviewers <= allowed, "Reviewer is not in the approved registry")
        require(review["evidence_url"] is not None, "Missing review evidence")
        require(data["toolchain_id"] is not None, "Approved statement must bind its environment")
        require(all(x["snapshot_sha256"] for x in data["original_sources"]), "Approved statement needs source snapshots")
    # Review identity/independence is a protected human approval, not proven by JSON.
    return data


def validate_registry(root: Path) -> dict[str, Any]:
    from .environments import load_environments, relative_path
    root = root.resolve()
    policy = read_policy(root)
    environments = load_environments(root)
    problems: dict[tuple[str, str], dict[str, Any]] = {}
    problem_files = data_files(root, "problems")
    for path in problem_files:
        if path.name != "problem.json":
            continue
        item = check_problem(root, path, policy)
        key = (item["problem_id"], item["statement_version"])
        require(key not in problems, "Duplicate problem version")
        problems[key] = item
        if 'workspace' in item:
            require(item['toolchain_id'] in environments, 'Workspace references unknown environment')
            env = environments[item['toolchain_id']]
            require(item['workspace']['environment_digest'] == canonical_digest(env), 'Stale workspace environment digest')
            for pattern in item['workspace']['submission_paths']:
                relative_path(pattern, pattern=True)
    for path in problem_files:
        relative = path.relative_to(root / "problems").parts
        require(len(relative) >= 3 and (relative[0], relative[1]) in problems,
                "JSON file outside a registered statement package")
    submissions: dict[str, dict[str, Any]] = {}
    for path in data_files(root, "submissions"):
        item = read_json(path)
        schema_validate("submission", item)
        expected = root / "submissions" / item["problem_id"] / (item["submission_id"] + ".json")
        require(path == expected, "Submission identity does not match its path")
        require(item["submission_id"] not in submissions, "Submission IDs must be globally unique")
        key = (item["problem_id"], item["statement_version"])
        require(key in problems, "Submission references an unknown problem version")
        problem = problems[key]
        mapped = [target["official_theorem"] for target in item["targets"]]
        require(len(mapped) == len(set(mapped)), "Duplicate official theorem mapping")
        require(set(mapped) == set(problem["required_theorems"]), "Submission must cover all and only required targets")
        require(item["toolchain_id"] == problem["toolchain_id"], "Submission toolchain differs from its problem")
        if 'execution' in item:
            execution = item['execution']
            from .source_adaptation import transforms_by_path
            from .environments import matches
            transforms = transforms_by_path(execution)
            destinations = [change['destination'] for change in transforms.values()]
            require(len(destinations) == len(set(destinations)), 'Duplicate transformed destination')
            for original, change in transforms.items():
                require(matches(original, execution['include']), 'Transform source is outside selected patterns')
                require(change['destination'] not in {f['path'] for f in problem['trusted_files']},
                        'Transformed source cannot overwrite a trusted file')
                if 'workspace' in problem:
                    require(matches(change['destination'], problem['workspace']['submission_paths']),
                            'Transformed source is outside the approved submission paths')
            relative_path(execution['project_root'], root=True)
            for pattern in execution['include']:
                relative_path(pattern, pattern=True)
            paths = set()
            for proof in execution['proof_files']:
                relative_path(proof['path'])
                require(proof['path'].endswith('.lean'), 'Only Lean proof overlays are supported')
                require(proof['path'] not in paths, 'Duplicate proof overlay')
                require(proof['path'] not in destinations, 'Proof overlay collides with transformed source')
                paths.add(proof['path'])
                file = safe_file(root, 'proofs/' + item['submission_id'] + '/' + proof['path'])
                require(file_digest(file) == proof['sha256'], 'Proof overlay hash mismatch')
        submissions[item["submission_id"]] = item
    # Formal acceptance and durable archive publication are not enabled.
    require(not data_files(root, "records"), "Formal records require durable archival and acceptance onboarding")
    from .intake import read_candidates, mappings
    candidates = read_candidates(root, submissions)
    mappings(root)  # Validate protected mapping data without retrieving candidate sources.
    return {"policy": policy, "problems": problems, "submissions": submissions,
            "environments": environments, "candidates": candidates}


def plan_verification(root: Path, submission_id: str) -> dict[str, Any]:
    require(len(submission_id) <= 80 and bool(ID.fullmatch(submission_id)), "Invalid submission ID")
    root = root.resolve()
    registry = validate_registry(root)
    if submission_id in registry.get('candidates', {}):
        candidate = registry['candidates'][submission_id]
        return {'schema_version': 1, 'submission_id': submission_id,
                'candidate_digest': canonical_digest(candidate), 'machine_status': 'not_run',
                'formal_status': 'pending', 'blockers': ['trusted_ci_preparation_required'],
                'candidate_repository': candidate['source']['repository'],
                'candidate_commit': candidate['source']['commit']}
    require(submission_id in registry["submissions"], "Unknown submission ID")
    submission = registry["submissions"][submission_id]
    problem = registry["problems"][(submission["problem_id"], submission["statement_version"])]
    base = f"problems/{problem['problem_id']}/{problem['statement_version']}"
    paths = {"policy/verification.json", f"{base}/problem.json",
             f"submissions/{problem['problem_id']}/{submission_id}.json"}
    paths.update(f"{base}/{item['path']}" for item in problem["trusted_files"])
    environment = registry['environments'].get(submission['toolchain_id'])
    if environment:
        env_base = 'environments/' + environment['environment_id']
        paths.add(env_base + '/environment.json')
        paths.update(env_base + '/' + item['path'] for item in environment['files'])
    paths.update('proofs/' + submission_id + '/' + item['path']
                 for item in submission.get('execution', {}).get('proof_files', []))
    inputs = [{"path": p, "sha256": file_digest(safe_file(root, p))} for p in sorted(paths)]
    blockers = ["durable_archive_unconfigured"]
    if registry["policy"]["backend"] == "unconfigured":
        blockers.insert(0, "backend_unconfigured")
    if submission["toolchain_id"] not in registry["policy"]["toolchains"]:
        blockers.append("approved_toolchain_unconfigured")
    if problem["review"]["status"] != "approved":
        blockers.append("statement_review_pending")
    result = {
        "schema_version": 1, "submission_id": submission_id,
        "input_digest": canonical_digest(inputs), "inputs": inputs,
        "candidate_repository": submission["repository"], "candidate_commit": submission["commit"],
        "required_theorems": problem["required_theorems"], "blockers": blockers,
        "machine_status": "not_run", "formal_status": "pending", "backend": registry["policy"]["backend"],
    }
    schema_validate("plan", result)
    return result
