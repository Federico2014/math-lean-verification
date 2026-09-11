"""Build a catalog from protected-default-branch Actions job metadata.

No PR artifact, candidate HTML, printed result, or downloaded archive is trusted.
Exact branch/SHA + workflow ID + attempt + named execution job binds each verdict.
Protected publication references display historical administrator decisions separately.
"""
import argparse
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import re

from .merge_gate import GitHub
from .registry import read_json, require, safe_file, schema_validate, validate_registry, ROOT
from .revalidate import protected_default_branch, revision

WORKFLOW = 'revalidate.yml'
PATH = '.github/workflows/' + WORKFLOW
EXECUTION_STEP = 'Verify candidate with trusted Lean backend'


def trusted_run(run, workflow, repository, branch):
    return (run.get('workflow_id') == workflow['id'] and run.get('path') == PATH
            and run.get('event') in ('push', 'workflow_dispatch')
            and run.get('head_branch') == branch
            and (run.get('repository') or {}).get('full_name') == repository
            and (run.get('head_repository') or {}).get('full_name') == repository
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


def publication_history(api, publications):
    schema_validate('acceptance-publications', publications)
    history = {}
    for entry in publications['publications']:
        identifier = entry['candidate_id']
        require(identifier not in history, 'Duplicate acceptance publication')
        release = api.get('releases/' + str(entry['release_id']))
        require(release.get('draft') is False and release.get('immutable') is True
                and release.get('published_at') and release.get('tag_name') == entry['release_tag']
                and release.get('target_commitish') == entry['archive_commit']
                and (release.get('author') or {}).get('login') == entry['administrator'],
                'Acceptance release differs from protected publication reference')
        tag = api.get('git/ref/tags/' + entry['release_tag'])
        require(tag.get('object') == {'sha': entry['archive_commit'], 'type': 'commit',
                'url': 'https://api.github.com/repos/' + api.repository + '/git/commits/' + entry['archive_commit']},
                'Acceptance archive tag mismatch')
        assets = [a for a in release.get('assets', []) if a.get('name') == 'acceptance.json']
        require(len(assets) == 1 and assets[0].get('state') == 'uploaded'
                and assets[0].get('digest') == 'sha256:' + entry['record_sha256'],
                'Acceptance record checksum mismatch')
        history[identifier] = dict(entry, url='https://github.com/' + api.repository + '/releases/tag/' + entry['release_tag'])
    return history


def build(api, registry, base, publications=None):
    branch = protected_default_branch(api, base)
    history = publication_history(api, publications) if publications else {}
    workflow = api.get('actions/workflows/' + WORKFLOW)
    require(workflow['path'] == PATH, 'Unexpected verification workflow')
    def read_runs():
        runs = [r for r in api.pages('actions/workflows/' + WORKFLOW + '/runs?branch=' + branch + '&head_sha=' + base,
                                    'workflow_runs', max_pages=10)
                if trusted_run(r, workflow, api.repository, branch)]
        return sorted(runs, key=lambda r: (r.get('run_started_at', ''), r['run_number'], r['run_attempt']), reverse=True)
    runs = read_runs()
    def newest(values, identifier):
        return next((r for r in values if r['head_sha'] == base and r.get('display_title') in (
            f'Revalidate {base} all', f'Revalidate {base} selected-{identifier}')), None)
    def identity(run):
        return (run['id'], run['run_attempt'], run['status']) if run else None
    def read_jobs(key):
        jobs = list(api.pages(f'actions/runs/{key[0]}/attempts/{key[1]}/jobs', 'jobs'))
        require(all(j['run_id'] == key[0] and j['run_attempt'] == key[1]
                    and j['head_sha'] == base for j in jobs), 'Job identity mismatch')
        return jobs
    def job_snapshot(jobs):
        return sorted((j['name'], j.get('id'), j['status'], j['conclusion'],
                       tuple((s['name'], s['status'], s['conclusion']) for s in j.get('steps', [])))
                      for j in jobs if j['name'].startswith('Verify candidate '))
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
        if identifier in history:
            acceptance = history[identifier]
            require(candidate.get('problem_id') == acceptance['problem_id']
                    and candidate.get('statement_version') == acceptance['statement_version'],
                    'Acceptance publication refers to a different registered problem')
            row['acceptance_history'] = acceptance
            row['formal_status'] = 'accepted_historical'
        if run:
            key = (run['id'], run['run_attempt'])
            if key not in cache:
                cache[key] = read_jobs(key)
            row['status'] = outcome(run, cache[key], identifier)
            row['evidence_url'] = f'https://github.com/{api.repository}/actions/runs/{key[0]}/attempts/{key[1]}'
        row['history_url'] = f'https://github.com/{api.repository}/actions/workflows/{WORKFLOW}?query=branch%3A{branch}'
        rows.append(row)
    for key, jobs in cache.items():
        require(job_snapshot(jobs) == job_snapshot(read_jobs(key)),
                'Verification jobs changed while generating catalog; retry publication')
    latest_runs = read_runs()
    require(all(selected[i] == identity(newest(latest_runs, i)) for i in entries),
            'Verification attempts changed while generating catalog; retry publication')
    require(protected_default_branch(api, base) == branch, 'Default branch changed while generating catalog')
    return {'schema_version': 1, 'branch': branch, 'verifier_sha': base,
            'generated_at': datetime.now(timezone.utc).isoformat(), 'candidates': rows}


def render(catalog):
    esc = html.escape
    rows = []
    for item in catalog['candidates']:
        source = item['source']
        source_url = source['repository'] + '/tree/' + source['commit']
        evidence = ('<a href="' + esc(item['evidence_url'], quote=True) + '">CI evidence</a>'
                    if item['evidence_url'] else 'No current run')
        acceptance = item.get('acceptance_history')
        formal = 'Pending'
        if acceptance:
            formal = ('<a href="' + esc(acceptance['url'], quote=True) + '">Accepted by administrator '
                      + esc(acceptance['administrator']) + ' on ' + esc(acceptance['accepted_on']) + '</a>'
                      + '<br>Historical acceptance: source <code>' + esc(acceptance['source_commit'][:12])
                      + '</code>, verifier <code>' + esc(acceptance['verifier_sha'][:12]) + '</code>')
        rows.append('<tr><td>' + esc(item['id']) + '</td><td>' + esc(item['title']) +
                    '</td><td><a href="' + esc(source_url, quote=True) + '">' + esc(source['commit'][:12]) +
                    '</a></td><td>' + esc(item['status']) + '</td><td>' + evidence + '</td><td>' + formal + '</td></tr>')
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Registered candidates</title>'
            '<meta name="viewport" content="width=device-width"><style>body{font:16px system-ui;max-width:1200px;'
            'margin:2rem auto;padding:1rem}table{border-collapse:collapse;width:100%}td,th{padding:.7rem;'
            'border:1px solid #ddd;text-align:left}code{overflow-wrap:anywhere}</style>'
            '<h1>Registered candidates</h1><p>Protected ' + esc(catalog['branch']) + ': <code>' + esc(catalog['verifier_sha']) +
            '</code>. Updated: ' + esc(catalog['generated_at']) + '</p>'
            '<p>Verification checks the registered statement and proof. Formal acceptance and award decisions '
            'remain separate. A historical pass does not describe changed inputs.</p>'
            '<table><thead><tr><th>Candidate ID</th><th>Title</th><th>Fixed source</th><th>Current verification</th>'
            '<th>Evidence</th><th>Published formal acceptance</th></tr></thead><tbody>' + ''.join(rows) +
            '</tbody></table><p><a href="candidates.json">Machine-readable catalog and historical run links</a>. '
            'Blocked preparation is not_run; open the linked CI plan for the reason. Evidence artifacts expire '
            'after 90 days. Published acceptance links identify separately archived historical decisions; '
            'they do not approve a changed source or verifier revision.</p></html>')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    base = revision(os.environ['GITHUB_SHA'])
    publications = read_json(safe_file(ROOT, 'docs/acceptance-publications.json'))
    value = build(GitHub(os.environ['GITHUB_REPOSITORY']), validate_registry(ROOT), base, publications)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'candidates.json').write_text(json.dumps(value, indent=2) + '\n')
    (args.output / 'index.html').write_text(render(value))


if __name__ == '__main__':
    main()
