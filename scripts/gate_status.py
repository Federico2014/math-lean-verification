"""Publish exact trusted job verdicts; never consume candidate artifacts."""
import json
import os
from pathlib import Path
import re
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
        head, base = pr['head']['sha'], pr['base']['sha']
        assert re.fullmatch('[0-9a-f]{40}', head) and re.fullmatch('[0-9a-f]{40}', base)
        assert not inputs.get('expected_head') or inputs['expected_head'] == head
        assert not inputs.get('expected_base') or inputs['expected_base'] == base
        assert os.environ['GITHUB_REF'] == 'refs/heads/' + branch
        assert os.environ['GITHUB_SHA'] == base
        branch_info = api('branches/' + branch)
        assert branch_info['protected'] and branch_info['commit']['sha'] == base
        status(head, 'pending', 'Lean proof verification is pending')
        with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
            stream.write(f'head={head}\npr={number}\nbase={base}\nbase_ref={branch}\n')
    elif mode == 'finish':
        head = os.environ['PR_HEAD']
        current = api('pulls/' + str(int(os.environ['PR_NUMBER'])))
        if (current['state'] != 'open' or current['head']['sha'] != head
                or current['base']['sha'] != os.environ['EXPECTED_BASE']
                or current['base']['ref'] != os.environ['EXPECTED_BASE_REF']
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
