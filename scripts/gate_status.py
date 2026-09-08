"""Publish the trusted job verdict for an exact PR head; never consume proof artifacts."""
import json
import os
from pathlib import Path
import re
import sys
import urllib.request

repo = os.environ['GITHUB_REPOSITORY']
assert re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo)


def api(path, data=None):
    payload = None if data is None else json.dumps(data).encode()
    request = urllib.request.Request('https://api.github.com/repos/' + repo + '/' + path,
        data=payload, headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
        'Accept': 'application/vnd.github+json', 'User-Agent': 'math-lean-verification'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def status(head, state, description):
    assert re.fullmatch('[0-9a-f]{40}', head)
    api('statuses/' + head, {'state': state, 'context': 'lean-verification',
        'description': description, 'target_url': 'https://github.com/' + repo + '/actions/runs/' + os.environ['GITHUB_RUN_ID']})


if sys.argv[1] == 'resolve':
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    number = int(event.get('pull_request', {}).get('number') or event['inputs']['pr'])
    assert number > 0
    pr = api('pulls/' + str(number))
    assert pr['state'] == 'open' and pr['base']['ref'] == 'main'
    assert pr['base']['repo']['full_name'] == repo
    head = pr['head']['sha']
    status(head, 'pending', 'Lean proof verification is pending')
    with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
        stream.write('head=' + head + '\npr=' + str(number) + '\nbase=' + pr['base']['sha'] + '\n')
else:
    result = os.environ['EXECUTION_RESULT']
    gate = os.environ['PLAN_STATUS']
    success = os.environ['PLAN_RESULT'] == 'success' and ((gate == 'ready' and result == 'success') or (gate == 'not_applicable' and result == 'skipped'))
    current = api('pulls/' + str(int(os.environ['PR_NUMBER'])))
    success = success and current['head']['sha'] == os.environ['PR_HEAD'] and current['base']['sha'] == os.environ['EXPECTED_BASE']
    description = ('No candidate proof changes in this PR' if gate == 'not_applicable' else
                   'Statement, axioms, Lean and Nanoda checks passed') if success else 'Lean verification failed or prerequisites are incomplete'
    status(os.environ['PR_HEAD'], 'success' if success else 'failure', description)
