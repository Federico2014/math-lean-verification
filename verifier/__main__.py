"""CLI for registry validation and explicit, non-executing preflight."""

import argparse
import json
import sys
from pathlib import Path

from .registry import ROOT, RegistryError, plan_verification, validate_registry


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Registry checkout (schemas stay trusted)")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate", help="Check metadata, references, and bound statement files")
    commands.add_parser("list", help="List registered candidates; no network or Lean execution")
    commands.add_parser('environments', help='List reusable environments, their status and canonical digest')
    plan = commands.add_parser("plan", help="Produce a preflight plan; this is NOT proof verification")
    plan.add_argument("submission_id")
    plan.add_argument("--output", type=Path, help="New output file; existing files are never overwritten")
    inspect = commands.add_parser('inspect-environment', help='Inspect local project metadata without executing Lake')
    inspect.add_argument('project', type=Path)
    draft = commands.add_parser('draft-submission', help='Generate an intake draft without executing Lean')
    draft.add_argument('project', type=Path)
    draft.add_argument('--repository', required=True)
    draft.add_argument('--commit', required=True)
    draft.add_argument('--submission-id', required=True)
    draft.add_argument('--problem-id', required=True)
    draft.add_argument('--statement-version', default='v1')
    draft.add_argument('--target', nargs=3, action='append', required=True,
                       metavar=('MODULE', 'DECLARATION', 'OFFICIAL_THEOREM'))
    draft.add_argument('--output', type=Path, required=True)
    env_draft = commands.add_parser('draft-environment', help='Generate a pending environment from static metadata')
    env_draft.add_argument('project', type=Path)
    env_draft.add_argument('--environment-id', required=True)
    env_draft.add_argument('--lean-archive-sha256', required=True)
    env_draft.add_argument('--exporter-commit', required=True)
    env_draft.add_argument('--cache-module', action='append', default=[])
    env_draft.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'draft-submission':
            from .onboarding import submission_draft, write_new
            value = submission_draft(args.project, args.root, repository=args.repository,
                commit=args.commit, identifier=args.submission_id, problem_id=args.problem_id,
                statement_version=args.statement_version, targets=args.target)
            write_new(args.output, value)
            print('Intake draft written. No proof executed; complete its listed blockers before registration.')
            return 0
        if args.command == 'draft-environment':
            from .onboarding import environment_draft
            environment_draft(args.project, args.output, identifier=args.environment_id,
                archive_sha256=args.lean_archive_sha256, exporter_commit=args.exporter_commit,
                cache_modules=args.cache_module)
            print('Pending environment written. Real compatibility tests and review are still required.')
            return 0
        if args.command == 'environments':
            from .environments import load_environments
            from .registry import canonical_digest
            print(json.dumps([{'environment_id': key, 'status': env['status'],
                               'environment_digest': canonical_digest(env)}
                              for key, env in load_environments(args.root).items()], indent=2))
            return 0
        if args.command == 'inspect-environment':
            from .environments import discover
            print(json.dumps(discover(args.project, args.root), indent=2))
            return 0
        if args.command == "plan":
            result = plan_verification(args.root, args.submission_id)
            output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
            if args.output:
                with args.output.open("x", encoding="utf-8") as stream:
                    stream.write(output)
            print(output, end="")
            # Preflight never executes proofs, even with an admitted backend.
            return 3
        registry = validate_registry(args.root)
        if args.command == "list":
            print(json.dumps(sorted(set(registry["submissions"]) | set(registry['candidates'])), indent=2))
        else:
            print(f"Registry valid: {len(registry['problems'])} problem versions, "
                  f"{len(registry['submissions'])} submissions, {len(registry['candidates'])} simplified candidates. No proofs executed.")
        return 0
    except (RegistryError, OSError) as exc:
        print(f"Validation error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
