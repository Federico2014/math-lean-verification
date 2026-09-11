"""Recheck registered candidates using the current protected default branch.

This workflow never publishes a PR status, rewrites a record, or grants an approval.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from .merge_gate import GitHub, execute_candidates, prerequisites
from .registry import ROOT, RegistryError, VerificationError, read_json, require, safe_file, validate_registry


def plan(registry, submission=None):
    all_ids = set(registry['submissions']) | set(registry.get('candidates', {}))
    if submission is not None:
        require(submission in all_ids, 'Unknown submission')
    identifiers = [submission] if submission is not None else sorted(all_ids)
    require(len(identifiers) <= 256, 'Revalidation exceeds matrix limit; select a submission')
    rows, blocked = [], {}
    for identifier in identifiers:
        intake = registry.get('intake', {}).get(identifier)
        if identifier not in registry['submissions'] or (intake and intake['intake_status'] != 'ready'):
            blocked[identifier] = intake or {'intake_status': 'needs_adaptation', 'blockers': ['Preparation required']}
            continue
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
        require(os.environ.get('GITHUB_REF') in ('refs/heads/main', 'refs/heads/develop'),
                'Revalidation requires protected main or develop')
        require(os.environ.get('GITHUB_SHA') == expected, 'Revalidation event identity mismatch')
    return actual


def protected_default_branch(api, expected):
    branch = api.get('')['default_branch']
    require(branch in ('main', 'develop'), 'Unsupported default branch')
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        require(os.environ.get('GITHUB_REF') == 'refs/heads/' + branch,
                'Workflow is not running on the current default branch')
    info = api.get('branches/' + branch)
    require(info.get('protected') is True, 'Default branch must be protected')
    require(info['commit']['sha'] == expected, 'Default branch moved; retry with its current revision')
    return branch


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
        api = GitHub(os.environ['GITHUB_REPOSITORY']) if os.environ.get('GITHUB_ACTIONS') == 'true' else None
        branch = protected_default_branch(api, base) if api else None
        registry = validate_registry(ROOT)
        from .intake import prepare_registry
        with tempfile.TemporaryDirectory(prefix='lean-revalidate-') as temporary:
            prepared_root = Path(temporary)
            if not args.plan and args.submission in registry['submissions']:
                item = registry['submissions'][args.submission]
                for file in item.get('execution', {}).get('proof_files', []):
                    relative = 'proofs/' + args.submission + '/' + file['path']
                    source = safe_file(ROOT, relative)
                    destination = prepared_root / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(source.read_bytes())
            registry = prepare_registry(registry, ROOT, ROOT, prepared_root,
                                        [args.submission] if args.submission else None)
            result = execute(args, base, registry, prepared_root)
            if api:
                require(protected_default_branch(api, base) == branch, 'Default branch changed during verification')
            return result
    except (RegistryError, OSError, ValueError, subprocess.SubprocessError) as exc:
        (args.output / 'error.json').write_text(json.dumps({'status': 'failed', 'error': str(exc)}) + '\n')
        return 1


def execute(args, base, registry, prepared_root):
    selection = plan(registry, args.submission)
    selection['verifier_sha'] = base
    (args.output / 'selection.json').write_text(json.dumps(selection, indent=2) + '\n')
    from .workflow import from_plan, write_summary
    write_summary(from_plan(selection), args.output / 'workflow.json')
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
    require(args.submission not in selection['blocked'], 'Candidate preparation is blocked')
    result = execute_candidates(registry, registry, prepared_root, [args.submission], base, None,
                                None, args.output, images=read_json(args.images))
    (args.output / 'revalidation.json').write_text(json.dumps(result, indent=2) + '\n')
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
