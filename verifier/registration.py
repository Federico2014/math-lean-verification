"""Generate the README registration summary from versioned registry data.

The table links current verification instead of committing volatile CI statuses.
Publication references describe historical decisions; this renderer grants none.
"""
import html
import re
from urllib.parse import quote

from .registry import canonical_digest, require, schema_validate

START = '<!-- registered-candidates:start -->'
END = '<!-- registered-candidates:end -->'


def text(value):
    escaped = html.escape(str(value), quote=True).replace('|', '&#124;').replace('\n', ' ').replace('\r', ' ')
    return re.sub(r'([\\`*_[\]])', r'\\\1', escaped)


def problem_identity(registry, identifier):
    candidate = registry['candidates'][identifier]
    mapping = registry.get('intake_mappings', {}).get(identifier)
    if mapping:
        schema_validate('intake-mapping', mapping)
        require(mapping['candidate_digest'] == canonical_digest(candidate), 'Stale protected problem mapping')
    problem = (mapping or {}).get('problem_id', candidate.get('problem_id'))
    version = (mapping or {}).get('statement_version', candidate.get('statement_version'))
    if problem and version is None:
        versions = [v for p, v in registry.get('problems', {}) if p == problem]
        if len(versions) == 1:
            version = versions[0]
    require(problem is not None and version is not None,
            'Acceptance requires an exact registered problem/version or protected correspondence mapping')
    return problem, version


def render(registry, publications, repository, *, verified=None):
    require(bool(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository)), 'Invalid repository')
    schema_validate('acceptance-publications', publications)
    history = {}
    for entry in publications['publications']:
        require(entry['candidate_id'] not in history, 'Duplicate acceptance publication')
        require(verified is not None and entry['candidate_id'] in verified and all(
            verified[entry['candidate_id']].get(k) == v for k, v in entry.items()),
            'Verify immutable acceptance publications before rendering accepted status')
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
            identity = (problem_identity(registry, identifier) if identifier in registry.get('candidates', {})
                        else (candidate['problem_id'], candidate['statement_version']))
            require(identity == (acceptance['problem_id'], acceptance['statement_version']),
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
