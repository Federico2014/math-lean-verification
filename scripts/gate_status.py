"""Publish exact trusted job verdicts; never consume candidate artifacts."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.request


def api(path, data=None):
    repo = os.environ['GITHUB_REPOSITORY']
    assert re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo)
    request = urllib.request.Request('https://api.github.com/repos/' + repo + '/' + path,
        data=None if data is None else json.dumps(data).encode(), headers={
            'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
            'Accept': 'application/vnd.github+json', 'User-Agent': 'math-lean-verification'})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(16 * 1024**2 + 1)
    assert len(data) <= 16 * 1024**2
    return json.loads(data)


def run_url():
    return ('https://github.com/' + os.environ['GITHUB_REPOSITORY'] + '/actions/runs/'
            + os.environ['GITHUB_RUN_ID'])


def status(head, state, description):
    assert re.fullmatch('[0-9a-f]{40}', head)
    api('statuses/' + head, {'state': state, 'context': 'lean-verification',
        'description': description, 'target_url': run_url()})


def checked_out_revision():
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'],
        cwd=Path(__file__).resolve().parents[1], text=True, timeout=30).strip()


def event_target(event, number, head):
    """Bind automatic events to their original PR identity, including retargets."""
    pr = event['pull_request']
    assert pr['number'] == number and pr['head']['sha'] == head
    assert pr['base']['repo']['full_name'] == os.environ['GITHUB_REPOSITORY']
    branch = pr['base']['ref']
    assert branch in ('main', 'develop')
    return branch


def main(mode):
    if mode == 'resolve':
        event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
        inputs = event.get('inputs') or {}
        number = int(event.get('pull_request', {}).get('number') or inputs['pr'])
        assert number > 0
        pr = api('pulls/' + str(number))
        assert pr['state'] == 'open'
        branch = pr['base']['ref']
        assert branch in ('main', 'develop')
        assert pr['base']['repo']['full_name'] == os.environ['GITHUB_REPOSITORY']
        branch_info = api('branches/' + branch)
        head, base = pr['head']['sha'], branch_info['commit']['sha']
        assert re.fullmatch('[0-9a-f]{40}', head) and re.fullmatch('[0-9a-f]{40}', base)
        assert not inputs.get('expected_head') or inputs['expected_head'] == head
        assert not inputs.get('expected_base') or inputs['expected_base'] == base
        assert branch_info['protected']
        if os.environ['GITHUB_EVENT_NAME'] == 'pull_request_target':
            assert event_target(event, number, head) == branch
            # GitHub runs this event in the default branch context, even for a
            # PR targeting develop. The checkout must still be the live base.
            default = event['repository']['default_branch']
            assert default in ('main', 'develop')
            assert event['repository']['full_name'] == os.environ['GITHUB_REPOSITORY']
            assert os.environ['GITHUB_REF'] == 'refs/heads/' + default
        else:
            assert os.environ['GITHUB_EVENT_NAME'] == 'workflow_dispatch'
            assert os.environ['GITHUB_REF'] == 'refs/heads/' + branch
            assert os.environ['GITHUB_SHA'] == base
        assert checked_out_revision() == base, 'Controller checkout is not the current protected target'
        status(head, 'pending', 'Lean proof verification is pending')
        with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
            stream.write(f'head={head}\npr={number}\nbase={base}\nbase_ref={branch}\n')
    elif mode == 'finish':
        head = os.environ['PR_HEAD']
        expected_branch = os.environ.get('EXPECTED_BASE_REF')
        if os.environ.get('GITHUB_EVENT_NAME') == 'pull_request_target':
            event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
            original_branch = event_target(event, int(os.environ['PR_NUMBER']), head)
            # The default branch may still contain the earlier workflow, which
            # does not forward base_ref. Its immutable event supplies that binding.
            assert not expected_branch or expected_branch == original_branch
            expected_branch = original_branch
        assert expected_branch in ('main', 'develop')
        assert checked_out_revision() == os.environ['EXPECTED_BASE']
        current = api('pulls/' + str(int(os.environ['PR_NUMBER'])))
        if (current['state'] != 'open' or current['head']['sha'] != head
                or current['base']['ref'] != expected_branch
                or current['base']['repo']['full_name'] != os.environ['GITHUB_REPOSITORY']):
            return
        branch = current['base']['ref']
        if branch not in ('main', 'develop'):
            return
        branch_info = api('branches/' + branch)
        if not branch_info['protected'] or branch_info['commit']['sha'] != os.environ['EXPECTED_BASE']:
            return
        latest = None
        for page in range(1, 101):
            statuses = api(f'commits/{head}/statuses?per_page=100&page={page}')
            latest = next((s for s in statuses if s['context'] == 'lean-verification'), None)
            if latest or len(statuses) < 100:
                break
        if not latest or latest.get('target_url') != run_url() or latest['state'] != 'pending':
            return
        gate, result = os.environ['PLAN_STATUS'], os.environ['EXECUTION_RESULT']
        success = os.environ['PLAN_RESULT'] == 'success' and (
            (gate == 'ready' and result == 'success') or (gate == 'not_applicable' and result == 'skipped'))
        description = ('No candidate proof changes in this PR' if gate == 'not_applicable' else
            'Statement, axioms, Lean and Nanoda checks passed') if success else (
            'Lean verification failed or prerequisites are incomplete')
        status(head, 'success' if success else 'failure', description)
    else:
        raise ValueError('Unknown mode')


if __name__ == '__main__':
    main(sys.argv[1])
