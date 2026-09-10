"""Resume open candidate PRs from a protected target branch without running candidate code."""
import json
import os
from pathlib import Path
import tempfile
import re
import subprocess

from .merge_gate import GitHub, run
from .registry import ROOT, RegistryError, require

WORKFLOW = 'lean-verification.yml'


def marker(number, head, base, branch='main'):
    return f'Lean PR {number} {head} {base} {branch}'


def current(pr, repository, head, branch='main'):
    return (pr['state'] == 'open' and pr['base']['ref'] == branch
            and pr['base']['repo']['full_name'] == repository
            and pr['head']['sha'] == head)


def resume(api, base, planner=run, *, branch='main'):
    """Dispatch once per exact identity; explicit manual dispatch remains a retry."""
    require(branch in ('main', 'develop'), 'Unexpected scheduler branch')
    # PR base.sha can lag after a target push; bind to the live branch ref.
    info = api.get('branches/' + branch)
    require(info['protected'], 'Scheduler branch must be protected')
    require(info['commit']['sha'] == base, 'Scheduler checkout is stale')
    runs = list(api.pages('actions/workflows/' + WORKFLOW + '/runs?head_sha=' + base,
                          'workflow_runs', max_pages=10))
    reports = []
    for pr in api.pages('pulls?state=open&base=' + branch):
        number, head = pr['number'], pr['head']['sha']
        if not current(pr, api.repository, head, branch) or pr.get('draft'):
            continue
        try:
            files = list(api.pages(f'pulls/{number}/files', max_pages=31))
            require(len(files) < 3000, 'Candidate PR file list may be truncated')
        except (RegistryError, OSError) as exc:
            reports.append({'pr': number, 'head': head, 'base': base, 'status': 'blocked', 'error': str(exc)})
            continue
        if not any(f['filename'].startswith(('candidates/', 'submissions/', 'proofs/')) for f in files):
            continue
        identity = marker(number, head, base, branch)
        # GitHub reports PR head_sha for pull_request_target runs, but the target branch
        # head_sha for dispatches. Query both identities to avoid cancelling an
        # already-running initial PR verification with a duplicate dispatch.
        initial = [r for r in api.pages('actions/workflows/' + WORKFLOW + '/runs?head_sha=' + head,
                                       'workflow_runs', max_pages=10)
                   if r.get('event') == 'pull_request_target']
        source_repository = (pr['head'].get('repo') or {}).get('full_name')
        if not source_repository:
            reports.append({'pr': number, 'head': head, 'base': base, 'status': 'blocked',
                            'error': 'Candidate head repository is unavailable'})
            continue
        previous = [r for r in runs + initial if r.get('display_title') == identity
                    and r.get('head_sha') == (head if r.get('event') == 'pull_request_target' else base)
                    and (r.get('head_repository') or {}).get('full_name') == (
                        source_repository if r.get('event') == 'pull_request_target' else api.repository)
                    and r.get('event') in ('pull_request_target', 'workflow_dispatch')]
        retry = False
        if len(previous) == 1 and previous[0].get('status') == 'completed' and previous[0].get('run_attempt') == 1 and previous[0].get('conclusion') in ('failure', 'cancelled', 'timed_out'):
            old_run = previous[0]
            jobs = list(api.pages(f'actions/runs/{old_run["id"]}/attempts/1/jobs', 'jobs'))
            executed = any(step.get('name') == 'Verify every required target and its trusted statement'
                           and step.get('status') == 'completed' and step.get('conclusion') != 'skipped'
                           for job in jobs for step in job.get('steps', []))
            retry = not executed  # One retry for a failure before proof execution.
        if previous and not retry:
            reports.append({'pr': number, 'head': head, 'base': base, 'status': 'already_dispatched'})
            continue
        with tempfile.TemporaryDirectory(prefix='lean-resume-') as folder:
            try:
                plan = planner(api.repository, number, head, None, Path(folder), check_only=True)
            except Exception as exc:
                plan = {'status': 'blocked', 'error': str(exc)}
        if not current(api.get(f'pulls/{number}'), api.repository, head, branch):
            continue
        info = api.get('branches/' + branch)
        if not info['protected'] or info['commit']['sha'] != base:
            break
        report = {'pr': number, 'head': head, 'base': base, 'plan': plan}
        if plan.get('status') not in ('ready', 'blocked'):
            report['status'] = 'not_applicable' if plan.get('status') == 'not_applicable' else 'blocked'
            reports.append(report)
            continue
        # A short protected plan run also publishes waiting failures through the
        # same serialized status jobs. No Lean matrix runs while blocked.
        api.request('actions/workflows/' + WORKFLOW + '/dispatches', {
            'ref': branch, 'inputs': {'pr': str(number), 'expected_head': head, 'expected_base': base}})
        report['status'] = 'dispatched' if plan['status'] == 'ready' else 'waiting'
        reports.append(report)
    return reports


def main():
    branch, base = os.environ['GITHUB_REF_NAME'], os.environ['GITHUB_SHA']
    require(branch in ('main', 'develop'), 'Unexpected scheduler branch')
    require(os.environ['GITHUB_REF'] == 'refs/heads/' + branch, 'Scheduler event branch mismatch')
    require(bool(re.fullmatch('[0-9a-f]{40}', base)), 'Expected a fixed scheduler revision')
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    require(actual == base, 'Scheduler checkout differs from event revision')
    result = resume(GitHub(os.environ['GITHUB_REPOSITORY']), base, branch=branch)
    Path('resume-report.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
