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
    plan = commands.add_parser("plan", help="Produce a preflight plan; this is NOT proof verification")
    plan.add_argument("submission_id")
    plan.add_argument("--output", type=Path, help="New output file; existing files are never overwritten")
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            result = plan_verification(args.root, args.submission_id)
            output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
            if args.output:
                with args.output.open("x", encoding="utf-8") as stream:
                    stream.write(output)
            print(output, end="")
            # Nonzero is intentional: an unconfigured backend must never be green.
            return 3
        registry = validate_registry(args.root)
        if args.command == "list":
            print(json.dumps(sorted(registry["submissions"]), indent=2))
        else:
            print(f"Registry valid: {len(registry['problems'])} problem versions, "
                  f"{len(registry['submissions'])} submissions. No proofs executed.")
        return 0
    except (RegistryError, OSError) as exc:
        print(f"Validation error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
