"""Generate the README registration summary from versioned registry data.

The table links current verification instead of committing volatile CI statuses.
Publication references describe historical decisions; this renderer grants none.
"""
import html
import re
from urllib.parse import quote

from .registry import require, schema_validate

START = '<!-- registered-candidates:start -->'
END = '<!-- registered-candidates:end -->'


def text(value):
    escaped = html.escape(str(value), quote=True).replace('|', '&#124;').replace('\n', ' ').replace('\r', ' ')
    return re.sub(r'([\\`*_[\]])', r'\\\1', escaped)


def render(registry, publications, repository):
    require(bool(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository)), 'Invalid repository')
    schema_validate('acceptance-publications', publications)
    history = {}
    for entry in publications['publications']:
        require(entry['candidate_id'] not in history, 'Duplicate acceptance publication')
        history[entry['candidate_id']] = entry
    owner, name = repository.split('/')
    catalog = f'https://{owner}.github.io/{name}/'
    rows = ['| Candidate | Fixed proof source | Machine verification | Formal acceptance |',
            '| --- | --- | --- | --- |']
    entries = dict(registry['submissions'], **registry.get('candidates', {}))
    for identifier, candidate in sorted(entries.items()):
        source = candidate.get('source') or {'repository': candidate['repository'], 'commit': candidate['commit']}
        schema_validate('candidate' if identifier in registry.get('candidates', {}) else 'submission', candidate)
        path = ('candidates/' + identifier + '.json' if identifier in registry.get('candidates', {}) else
                'submissions/' + candidate['problem_id'] + '/' + identifier + '.json')
        link = source['repository'] + '/tree/' + source['commit']
        acceptance = history.get(identifier)
        formal = 'Pending'
        if acceptance:
            require(candidate.get('problem_id', acceptance['problem_id']) == acceptance['problem_id'] and
                    candidate.get('statement_version', acceptance['statement_version']) == acceptance['statement_version'],
                    'Acceptance publication refers to a different registered problem')
            formal = (f"[Administrator accepted — {acceptance['accepted_on']}]"
                      f"(https://github.com/{repository}/releases/tag/{acceptance['release_tag']})"
                      f"; historical source `{acceptance['source_commit'][:12]}`")
        rows.append(f"| [{text(candidate.get('title', identifier))}]({path}) (`{identifier}`) | "
                    f"[{source['commit'][:12]}]({link}) | [Live status and evidence]({catalog}#{quote(identifier)}) | {formal} |")
    if not entries:
        rows.append('| No registered candidates | — | No proof verified | Pending |')
    return '\n'.join(rows)


def update(readme, table):
    require(readme.count(START) == 1 and readme.count(END) == 1,
            'README requires exactly one registration marker pair')
    start = readme.index(START) + len(START)
    end = readme.index(END)
    require(start < end, 'Invalid registration marker order')
    return readme[:start] + '\n\n' + table + '\n\n' + readme[end:]
