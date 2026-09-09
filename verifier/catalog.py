"""Build a non-authorizing catalog from protected-main Actions job metadata.

No PR artifact, candidate HTML, printed result, or downloaded archive is trusted.
Exact main SHA + workflow ID + attempt + named execution job binds each verdict.
"""
import argparse
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import re

from .merge_gate import GitHub
from .registry import require, validate_registry, ROOT
from .revalidate import revision

WORKFLOW = 'revalidate.yml'
PATH = '.github/workflows/' + WORKFLOW
EXECUTION_STEP = 'Verify candidate with trusted Lean backend'


def trusted_run(run, workflow, repository):
    return (run.get('workflow_id') == workflow['id'] and run.get('path') == PATH
            and run.get('event') in ('push', 'workflow_dispatch')
            and run.get('head_branch') == 'main'
            and run.get('repository', {}).get('full_name') == repository
            and run.get('head_repository', {}).get('full_name') == repository
            and re.fullmatch('[0-9a-f]{40}', run.get('head_sha', '')) is not None)


def outcome(run, jobs, identifier):
    job = next((j for j in jobs if j['name'] == 'Verify candidate ' + identifier), None)
    if job is None:
        return 'running' if run['status'] != 'completed' else 'not_run'
    if job['status'] != 'completed':
        return 'queued' if job['status'] == 'queued' else 'running'
    if job['conclusion'] == 'success':
        step = next((s for s in job['steps'] if s['name'] == EXECUTION_STEP), None)
        require(step is not None and step['status'] == 'completed' and step['conclusion'] == 'success',
                'Successful job has no actual verification step')
        return 'verified'
    return 'not_run' if job['conclusion'] == 'skipped' else 'cancelled' if job['conclusion'] == 'cancelled' else 'failed'


def build(api, registry, base):
    require(api.get('branches/main')['commit']['sha'] == base, 'Catalog checkout is stale')
    workflow = api.get('actions/workflows/' + WORKFLOW)
    require(workflow['path'] == PATH, 'Unexpected verification workflow')
    def read_runs():
        runs = [r for r in api.pages('actions/workflows/' + WORKFLOW + '/runs?branch=main&head_sha=' + base,
                                    'workflow_runs', max_pages=10)
                if trusted_run(r, workflow, api.repository)]
        return sorted(runs, key=lambda r: (r.get('run_started_at', ''), r['run_number'], r['run_attempt']), reverse=True)
    runs = read_runs()
    def newest(values, identifier):
        return next((r for r in values if r['head_sha'] == base and r.get('display_title') in (
            f'Revalidate {base} all', f'Revalidate {base} {identifier}')), None)
    def identity(run):
        return (run['id'], run['run_attempt'], run['status']) if run else None
    selected = {}
    entries = dict(registry['submissions'], **registry.get('candidates', {}))
    cache, rows = {}, []
    for identifier, candidate in sorted(entries.items()):
        run = newest(runs, identifier)
        selected[identifier] = identity(run)
        row = {'id': identifier, 'title': candidate.get('title', identifier),
               'source': candidate.get('source') or {'repository': candidate['repository'], 'commit': candidate['commit']},
               'status': 'not_run', 'formal_status': 'pending', 'verifier_sha': base,
               'evidence_url': None}
        if run:
            key = (run['id'], run['run_attempt'])
            if key not in cache:
                jobs = list(api.pages(f'actions/runs/{key[0]}/attempts/{key[1]}/jobs', 'jobs'))
                require(all(j['run_id'] == key[0] and j['run_attempt'] == key[1]
                            and j['head_sha'] == base for j in jobs), 'Job identity mismatch')
                cache[key] = jobs
            row['status'] = outcome(run, cache[key], identifier)
            row['evidence_url'] = f'https://github.com/{api.repository}/actions/runs/{key[0]}/attempts/{key[1]}'
        row['history_url'] = f'https://github.com/{api.repository}/actions/workflows/{WORKFLOW}?query=branch%3Amain'
        rows.append(row)
    latest_runs = read_runs()
    require(all(selected[i] == identity(newest(latest_runs, i)) for i in entries),
            'Verification attempts changed while generating catalog; retry publication')
    require(api.get('branches/main')['commit']['sha'] == base, 'Main moved while generating catalog')
    return {'schema_version': 1, 'verifier_sha': base,
            'generated_at': datetime.now(timezone.utc).isoformat(), 'candidates': rows}


def render(catalog):
    esc = html.escape
    rows = []
    for item in catalog['candidates']:
        source = item['source']
        source_url = source['repository'] + '/tree/' + source['commit']
        evidence = ('<a href="' + esc(item['evidence_url'], quote=True) + '">CI evidence</a>'
                    if item['evidence_url'] else 'No current run')
        rows.append('<tr><td>' + esc(item['id']) + '</td><td>' + esc(item['title']) +
                    '</td><td><a href="' + esc(source_url, quote=True) + '">' + esc(source['commit'][:12]) +
                    '</a></td><td>' + esc(item['status']) + '</td><td>' + evidence + '</td><td>pending</td></tr>')
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Registered candidates</title>'
            '<meta name="viewport" content="width=device-width"><style>body{font:16px system-ui;max-width:1200px;'
            'margin:2rem auto;padding:1rem}table{border-collapse:collapse;width:100%}td,th{padding:.7rem;'
            'border:1px solid #ddd;text-align:left}code{overflow-wrap:anywhere}</style>'
            '<h1>Registered candidates</h1><p>Protected main: <code>' + esc(catalog['verifier_sha']) +
            '</code>. Updated: ' + esc(catalog['generated_at']) + '</p>'
            '<p>Verification checks the registered statement and proof. Formal acceptance and award decisions '
            'remain separate. A historical pass does not describe changed inputs.</p>'
            '<table><thead><tr><th>Candidate ID</th><th>Title</th><th>Fixed source</th><th>Current verification</th>'
            '<th>Evidence</th><th>Formal acceptance</th></tr></thead><tbody>' + ''.join(rows) +
            '</tbody></table><p><a href="candidates.json">Machine-readable catalog and historical run links</a>. '
            'Blocked preparation is not_run; open the linked CI plan for the reason. Evidence artifacts expire '
            'after 90 days; this catalog is not a durable formal archive.</p></html>')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    base = revision(os.environ['GITHUB_SHA'])
    value = build(GitHub(os.environ['GITHUB_REPOSITORY']), validate_registry(ROOT), base)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'candidates.json').write_text(json.dumps(value, indent=2) + '\n')
    (args.output / 'index.html').write_text(render(value))


if __name__ == '__main__':
    main()
