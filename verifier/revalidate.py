"""Recheck registered candidates using the current protected main revision.

This workflow never publishes a PR status, rewrites a record, or grants an approval.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess

from .merge_gate import execute_candidates, prerequisites
from .registry import ROOT, RegistryError, VerificationError, read_json, require, validate_registry


def plan(registry, submission=None):
    if submission is not None:
        require(submission in registry['submissions'], 'Unknown submission')
    identifiers = [submission] if submission is not None else sorted(registry['submissions'])
    require(len(identifiers) <= 256, 'Revalidation exceeds matrix limit; select a submission')
    rows, blocked = [], {}
    for identifier in identifiers:
        try:
            item, _, _ = prerequisites(registry, registry, identifier)
            rows.append({'submission': identifier, 'environment': item['toolchain_id']})
        except RegistryError as exc:
            blocked[identifier] = {'status': exc.status if isinstance(exc, VerificationError) else 'not_run',
                                   'error': str(exc)}
    return {'schema_version': 1, 'selected': identifiers, 'matrix': {'include': rows},
            'blocked': blocked, 'status': 'ready' if rows else 'blocked' if blocked else 'not_applicable'}


def revision(expected):
    require(bool(re.fullmatch('[0-9a-f]{40}', expected)), 'Expected a fixed verifier revision')
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    require(actual == expected, 'Revalidation checkout differs from requested revision')
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        require(os.environ.get('GITHUB_REF') == 'refs/heads/main', 'Revalidation requires protected main')
        require(os.environ.get('GITHUB_SHA') == expected, 'Revalidation event identity mismatch')
    return actual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--submission')
    parser.add_argument('--plan', action='store_true')
    parser.add_argument('--images', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    try:
        base = revision(args.revision)
        registry = validate_registry(ROOT)
        selection = plan(registry, args.submission)
        selection['verifier_sha'] = base
        (args.output / 'selection.json').write_text(json.dumps(selection, indent=2) + '\n')
        if args.plan:
            if os.environ.get('GITHUB_OUTPUT'):
                with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
                    stream.write('has_work=' + str(bool(selection['matrix']['include'])).lower() + '\n')
                    stream.write('unblocked=' + str(not selection['blocked']).lower() + '\n')
                    matrix = selection['matrix'] if selection['matrix']['include'] else {'include': [{'submission': '', 'environment': ''}]}
                    stream.write('matrix=' + json.dumps(matrix) + '\n')
            print(json.dumps(selection))
            # Planning can succeed with blockers so supported candidates still run.
            # The final workflow job separately requires an empty blocker set.
            return 0
        require(args.submission is not None and args.images is not None,
                'Execution requires one selected submission and immutable images')
        result = execute_candidates(registry, registry, ROOT, [args.submission], base, None,
                                    None, args.output, images=read_json(args.images))
        (args.output / 'revalidation.json').write_text(json.dumps(result, indent=2) + '\n')
        return 0 if result['status'] == 'passed' else 1
    except (RegistryError, OSError, ValueError, subprocess.SubprocessError) as exc:
        (args.output / 'error.json').write_text(json.dumps({'status': 'failed', 'error': str(exc)}) + '\n')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
