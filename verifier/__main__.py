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
    env_draft = commands.add_parser('draft-environment', help='Generate a pending environment from static metadata')
    env_draft.add_argument('project', type=Path)
    env_draft.add_argument('--environment-id', required=True)
    env_draft.add_argument('--lean-archive-sha256', required=True)
    env_draft.add_argument('--exporter-commit', required=True)
    env_draft.add_argument('--cache-module', action='append', default=[])
    env_draft.add_argument('--output', type=Path, required=True)
    candidate = commands.add_parser('candidate', help='Submit, prepare, verify and publish a candidate')
    actions = candidate.add_subparsers(dest='action', required=True)
    submit = actions.add_parser('submit', help='Validate materials and open one candidate PR using your gh login')
    submit.add_argument('identifier')
    submit.add_argument('file', type=Path)
    submit.add_argument('--bridge', type=Path)
    submit.add_argument('--repository', required=True)
    submit.add_argument('--dry-run', action='store_true')
    prepare = actions.add_parser('prepare', help='Read sources and show prerequisite blockers; never execute Lean')
    prepare.add_argument('identifier')
    verify = actions.add_parser('verify', help='Dispatch the protected CI gate for an open PR')
    verify.add_argument('--pr', type=int, required=True)
    verify.add_argument('--repository', required=True)
    publish = actions.add_parser('publish', help='Merge and synchronize registration; optionally publish explicit administrator acceptance')
    publish.add_argument('identifier')
    publish.add_argument('--pr', type=int)
    publish.add_argument('--repository', required=True)
    acceptance = publish.add_mutually_exclusive_group()
    acceptance.add_argument('--approval', type=Path, help='Explicit administrator decision bound to a current proof run')
    acceptance.add_argument('--release-tag', help='Import an already published immutable acceptance')
    sync = commands.add_parser('sync-readme', help='Generate the marked README table from registry data; no proof claims')
    sync.add_argument('--repository', required=True)
    sync.add_argument('--output', type=Path, help='Write a preview to a new file instead of updating README')
    args = parser.parse_args(argv)
    try:
        if args.command == 'candidate':
            from . import candidate
            if args.action == 'prepare':
                value = candidate.prepare(args.root, args.identifier)
            else:
                api = candidate.Session(args.repository)
                if args.action == 'submit':
                    value = candidate.submit(api, args.identifier, args.file, args.bridge, dry_run=args.dry_run)
                elif args.action == 'verify':
                    value = candidate.verify(api, args.pr)
                else:
                    value = candidate.publish(api, args.identifier, pr=args.pr,
                                              approval=args.approval, release_tag=args.release_tag)
            print(json.dumps(value, indent=2))
            return 3 if args.action == 'prepare' else 0
        if args.command == 'sync-readme':
            from .registration import render, update
            from .registry import read_json, safe_file
            readme = safe_file(args.root, 'README.md')
            value = update(readme.read_text(encoding='utf-8'), render(validate_registry(args.root),
                read_json(safe_file(args.root, 'docs/acceptance-publications.json')), args.repository))
            if args.output:
                with args.output.open('x', encoding='utf-8') as stream:
                    stream.write(value)
            else:
                readme.write_text(value, encoding='utf-8')
            print('Registration summary generated; current proof status remains in the live catalog.')
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
