"""Bounded preparation of single-file candidates; never execute upstream code."""
import copy
import hashlib
import re
import tempfile
from pathlib import Path

from .environments import discover, matches, relative_path
from .registry import (ID, RegistryError, canonical_digest, data_files, read_json,
                       require, safe_file, schema_validate)
from .source_adaptation import adapt, transforms_by_path


def read_candidates(root, reserved=()):
    root = Path(root)
    if not (root / 'candidates').exists():
        return {}
    result = {}
    for path in data_files(root, 'candidates'):
        require(path.parent == root / 'candidates' and ID.fullmatch(path.stem), 'Invalid candidate path')
        require(path.stem not in reserved, 'Duplicate candidate and submission ID')
        value = read_json(path)
        schema_validate('candidate', value)
        relative_path(value['source'].get('project_root', '.'), root=True)
        for pattern in value['source'].get('include', []):
            relative_path(pattern, pattern=True)
        if value.get('bridge'):
            safe_file(root, 'proofs/' + path.stem + '/' + value['bridge'])
        result[path.stem] = value
    return result


def mappings(root):
    if not (Path(root) / 'intake-mappings').exists():
        return {}
    result = {}
    for path in data_files(Path(root), 'intake-mappings'):
        value = read_json(path)
        schema_validate('intake-mapping', value)
        transforms_by_path(value)
        require(path.parent == Path(root) / 'intake-mappings' and ID.fullmatch(path.stem), 'Invalid mapping path')
        result[path.stem] = value
    return result


def _masked(text):
    """Preserve offsets/newlines while masking nested Lean comments and strings."""
    out = list(text)
    i, depth, string = 0, 0, False
    while i < len(text):
        if depth:
            if text.startswith('/-', i):
                depth += 1; out[i:i+2] = '  '; i += 2; continue
            if text.startswith('-/', i):
                depth -= 1; out[i:i+2] = '  '; i += 2; continue
        elif string:
            if text[i] == '\\' and i + 1 < len(text):
                out[i] = ' '; out[i+1] = '\n' if text[i+1] == '\n' else ' '; i += 2; continue
            if text[i] == '"': string = False
        elif text.startswith('/-', i):
            depth = 1; out[i:i+2] = '  '; i += 2; continue
        elif text.startswith('--', i):
            end = text.find('\n', i)
            end = len(text) if end < 0 else end
            out[i:end] = ' ' * (end-i); i = end; continue
        elif text[i] == '"': string = True
        else:
            i += 1; continue
        out[i] = '\n' if text[i] == '\n' else ' '
        i += 1
    require(not depth and not string, 'Unterminated source comment or string')
    return ''.join(out)


def imports(data):
    text = data.decode('utf-8')
    masked = _masked(text)
    result = []
    for match in re.finditer(r'(?m)^[ \t]*(?:(?:public|private)\s+)?import[ \t]+([^\n]+)', masked):
        names = match.group(1).split()
        require(all(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_']*(?:\.[A-Za-z_][A-Za-z0-9_']*)*", n) for n in names),
                'Nonstandard import requires adaptation')
        result.extend(names)
    return result


def _rename_import(data, old, new):
    text = data.decode('utf-8')
    masked = _masked(text)
    spans = []
    for match in re.finditer(r'(?m)^[ \t]*(?:(?:public|private)\s+)?import[ \t]+([^\n]+)', masked):
        for token in re.finditer(r'\S+', match.group(1)):
            if token.group() == old:
                spans.append((match.start(1)+token.start(), match.start(1)+token.end()))
    # Use complete original lines as exact replacements, never an executable rule.
    replacements = []
    for start, end in spans:
        lo = text.rfind('\n', 0, start) + 1
        hi = text.find('\n', end)
        hi = len(text) if hi < 0 else hi + 1
        original = text[lo:hi]
        require(text.count(original) == 1, 'Ambiguous import replacement requires adaptation')
        replacement = original[:start-lo] + new + original[end-lo:]
        require(not any(r['old'] == original for r in replacements), 'Repeated import requires adaptation')
        replacements.append({'old': original, 'new': replacement, 'count': 1})
    return replacements


def _problem(candidate, registry, mapping):
    pid = (mapping or {}).get('problem_id', candidate.get('problem_id'))
    version = (mapping or {}).get('statement_version', candidate.get('statement_version'))
    if not pid:
        return None  # A description requires a protected correspondence mapping.
    values = [p for (i, v), p in registry['problems'].items()
              if i == pid and (version is None or v == version)]
    return values[0] if len(values) == 1 else None


def _targets(candidate, problem, mapping):
    targets = copy.deepcopy(candidate['targets'])
    if mapping and mapping.get('targets'):
        require([(t['module'], t['declaration']) for t in targets] ==
                [(t['module'], t['declaration']) for t in mapping['targets']], 'Mapping changes candidate targets')
        targets = copy.deepcopy(mapping['targets'])
    required = problem['required_theorems']
    for target in targets:
        if 'official_theorem' not in target:
            options = [t for t in required if t.rsplit('.', 1)[-1] == target['declaration'].rsplit('.', 1)[-1]]
            if len(required) == len(targets) == 1:
                options = required
            require(len(options) == 1, 'Ambiguous official target mapping')
            target['official_theorem'] = options[0]
    require(len(targets) == len(required) and {t['official_theorem'] for t in targets} == set(required),
            'Candidate must cover all official targets')
    return targets


def bridge_source(targets, transforms=()):
    """Alias exact constant types and universes inside the untrusted Lean sandbox.

    Lean theorem headers cannot infer `_` from their proof. Register a theorem
    using the source constant's complete type; ordinary kernel checking and all
    downstream comparison/axiom/replay checks still apply.
    """
    by_path = {t['path']: t for t in transforms}
    def source_module(target):
        path = target['module'].replace('.', '/') + '.lean'
        return by_path.get(path, {}).get('destination', path)[:-5].replace('/', '.')
    modules = sorted({source_module(t) for t in targets})
    lines = ['-- Generated bridge; checked as untrusted proof code.', 'import Lean']
    lines += ['import ' + module for module in modules]
    for target in targets:
        source = target['declaration']
        lines += ['', 'run_elab do', '  let env ← Lean.getEnv',
                  '  let some idx := env.getModuleIdxFor? `' + source,
                  '    | Lean.throwError "Candidate declaration has no defining module"',
                  '  unless env.header.moduleNames[idx]! == `' + source_module(target) + ' do',
                  '    Lean.throwError "Candidate declaration is not defined in the selected module"']
        if target['official_theorem'] == source:
            continue
        lines += ['  let info ← Lean.getConstInfo `' + source,
                  '  Lean.addDecl (.thmDecl {', '    name := `' + target['official_theorem'],
                  '    levelParams := info.levelParams', '    type := info.type',
                  '    value := Lean.mkConst `' + source + ' (info.levelParams.map Lean.Level.param)',
                  '  }) (forceExpose := true)']
    return ('\n'.join(lines) + '\n').encode()


def prepare_one(identifier, candidate, registry, trusted_root, source_root, output_root, api_factory=None):
    """Resolve a candidate using protected approvals; output contains no success claim."""
    from .merge_gate import GitHub
    api_factory = api_factory or GitHub
    digest = canonical_digest(candidate)
    result = {'candidate_digest': digest, 'intake_status': 'ready', 'blockers': [],
              'machine_status': 'not_run'}
    def block(kind, reason):
        result['blockers'].append({'status': kind, 'reason': reason})
        result['intake_status'] = result['blockers'][0]['status']
    mapping = mappings(trusted_root).get(identifier)
    if mapping and mapping['candidate_digest'] != digest:
        block('needs_adaptation', 'Protected mapping is stale for these candidate materials')
        return result
    if not candidate['public_source_authorized']:
        block('needs_information', 'Public-source authorization is required')
    texts = candidate['attribution']
    if any('<required>' in str(v) or not str(v).strip() for v in texts.values()):
        block('needs_information', 'Complete attribution placeholders')
    problem = _problem(candidate, registry, mapping)
    if problem is None or 'workspace' not in problem:
        block('waiting_problem', 'A unique protected problem workspace must be prepared')
    elif problem['review']['status'] != 'approved':
        block('waiting_review', 'Exact statement approval is pending')
    if any(b['status'] == 'needs_information' for b in result['blockers']):
        return result  # Do not retrieve sources without publication authorization.
    try:
        source = candidate['source']
        api = api_factory(source['repository'].removeprefix('https://github.com/'))
        tree = api.tree(source['commit'])
        prefix = source.get('project_root', '.')
        prefix = '' if prefix == '.' else prefix + '/'
        with tempfile.TemporaryDirectory(prefix='lean-intake-') as tmp:
            project = Path(tmp)
            metadata = {}
            for name in ('lean-toolchain', 'lakefile.toml', 'lakefile.lean', 'lake-manifest.json'):
                if prefix + name in tree:
                    data = api.blob(tree[prefix + name])
                    (project / name).write_bytes(data)
                    metadata[name] = hashlib.sha256(data).hexdigest()
            inspection = discover(project, trusted_root)
            result['inspection'] = inspection
            result['metadata_digest'] = canonical_digest(metadata)
            warnings = inspection['warnings']
            if warnings:
                if not mapping or mapping.get('reviewed_metadata_sha256') != result['metadata_digest']:
                    block('needs_adaptation', 'Static metadata needs review: ' + ', '.join(warnings))
            # Match fixed identities even after an explicitly bound metadata review.
            compatible = []
            from .environments import inspect_project
            for eid, env in registry['environments'].items():
                if inspection['lean_toolchain'] != 'leanprover/lean4:' + env['lean_release']:
                    continue
                expected = inspect_project(Path(trusted_root) / 'environments' / eid)['dependencies'] if env['files'] else []
                if expected == inspection['dependencies'] and env['status'] == 'approved' and eid in registry['policy']['toolchains']:
                    compatible.append(eid)
            if not compatible:
                block('waiting_environment', 'No approved environment matches fixed compiler and dependencies')
            if problem is None or 'workspace' not in problem or not compatible:
                return result
            eid = problem['toolchain_id']
            if eid not in compatible:
                block('waiting_problem', 'Official workspace must bind a compatible approved environment')
                return result
            env = registry['environments'][eid]
            result['environment_id'] = eid
            result['problem_id'] = problem['problem_id']
            result['statement_version'] = problem['statement_version']
            if result['blockers']:
                return result
            targets = _targets(candidate, problem, mapping)
            limits = env['resources']
            selected = {}
            total = 0
            pending = [t['module'].replace('.', '/') + '.lean' for t in targets]
            def read_source(path):
                nonlocal total
                relative_path(path)
                require(path != 'lakefile.lean', 'Lake programs are not candidate modules')
                require(prefix + path in tree, 'Required source module is missing')
                if source.get('include'):
                    require(matches(path, source['include']), 'Required local import is outside source selection')
                data = api.blob(tree[prefix + path])
                total += len(data)
                require(total <= limits['max_source_mb'] * 1024**2 and len(selected) < limits['max_files'], 'Candidate source scope exceeds limits')
                return data
            while pending:
                path = pending.pop()
                if path in selected:
                    continue
                selected[path] = read_source(path)
                for module in imports(selected[path]):
                    dep = module.replace('.', '/') + '.lean'
                    if prefix + dep in tree:
                        pending.append(dep)
            protected = {f['path'] for f in problem['trusted_files']}
            transforms = []
            rename = 'Challenge.lean' in selected and 'Challenge.lean' in protected
            for path, data in sorted(selected.items()):
                destination = 'CandidateChallenge.lean' if rename and path == 'Challenge.lean' else path
                replacements = _rename_import(data, 'Challenge', 'CandidateChallenge') if rename else []
                if destination != path or replacements:
                    transforms.append({'path': path, 'destination': destination,
                        'sha256': hashlib.sha256(data).hexdigest(), 'replacements': replacements})
            if mapping and 'source_transforms' in mapping:
                transforms = copy.deepcopy(mapping['source_transforms'])
            by_path = transforms_by_path({'source_transforms': transforms})
            require(set(by_path) <= set(selected), 'Mapping transforms unselected sources')
            adapted = {}
            for path, data in selected.items():
                destination, contents = adapt(path, data, by_path.get(path), max_bytes=limits['max_source_mb'] * 1024**2)
                require(destination not in adapted and destination not in protected, 'Source conflicts with protected or generated paths')
                require(matches(destination, problem['workspace']['submission_paths']), 'Source requires approved path adaptation')
                adapted[destination] = contents
            bridge_path = problem['workspace']['solution_module'].replace('.', '/') + '.lean'
            relative_path(bridge_path)
            require(bridge_path not in adapted and bridge_path not in protected, 'Bridge path collides with a source module')
            require(matches(bridge_path, problem['workspace']['submission_paths']), 'Bridge path is not approved')
            if candidate.get('bridge'):
                bridge = safe_file(Path(source_root), 'proofs/' + identifier + '/' + candidate['bridge']).read_bytes()
            else:
                bridge = bridge_source(targets, transforms)
            # Preserve the upstream license in the archived generated overlay.
            for name in ('LICENSE', 'LICENSE.md', 'LICENSE.txt', 'COPYING'):
                location = prefix + name if prefix + name in tree else name
                if location in tree:
                    license_bytes = api.blob(tree[location])
                    require(len(license_bytes) <= 128*1024, 'License exceeds size limit')
                    license_text = license_bytes.decode('utf-8')
                    bridge += ('\n-- Upstream license: ' + source['repository'] + '\n' +
                               '\n'.join('-- ' + line for line in license_text.splitlines()) + '\n').encode()
                    result['license_sha256'] = hashlib.sha256(license_bytes).hexdigest()
                    break
            output = Path(output_root) / 'proofs' / identifier / bridge_path
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(bridge)
            submission = {'schema_version': 1, 'submission_id': identifier,
                'problem_id': problem['problem_id'], 'statement_version': problem['statement_version'],
                'repository': source['repository'], 'commit': source['commit'], 'targets': targets,
                'toolchain_id': eid, 'adapter_id': None,
                'paper_urls': candidate.get('paper_urls') or [s['url'] for s in problem['original_sources']],
                'contribution': dict(candidate['attribution'], public_source_authorized=True),
                'execution': {'project_root': source.get('project_root', '.'), 'include': sorted(selected),
                              'source_transforms': transforms,
                              'proof_files': [{'path': bridge_path, 'sha256': hashlib.sha256(bridge).hexdigest()}]}}
            submission['contribution'].setdefault('prior_results', 'Not supplied; no priority claim is inferred.')
            schema_validate('submission', submission)
            result.update({'submission': submission, 'source_hashes': {p: hashlib.sha256(v).hexdigest() for p,v in sorted(selected.items())},
                           'environment_digest': canonical_digest(env), 'workspace_digest': canonical_digest(problem),
                           'mapping_digest': canonical_digest(mapping), 'prepared_digest': canonical_digest(submission)})
    except (RegistryError, UnicodeError, ValueError) as exc:
        block('needs_adaptation', str(exc))
    except OSError:
        block('infrastructure_error', 'Source retrieval failed; retry the fixed input')
    return result


def prepare_registry(registry, trusted_root, source_root, output_root, identifiers=None, api_factory=None):
    resolved = copy.deepcopy(registry)
    resolved['intake'] = {}
    selected = registry.get('candidates', {})
    for identifier in sorted(selected):
        if identifiers is not None and identifier not in identifiers:
            continue
        value = prepare_one(identifier, selected[identifier], registry, trusted_root, source_root, output_root, api_factory)
        resolved['intake'][identifier] = value
        if value['intake_status'] == 'ready':
            resolved['submissions'][identifier] = value['submission']
    return resolved
