"""Bounded, hash-bound source edits. Adapted Lean remains untrusted proof input."""
import hashlib
import re

from .registry import require


def lean_path(path):
    require(isinstance(path, str) and len(path) <= 256 and path.endswith('.lean'),
            'Expected a Lean source path')
    require(all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', part)
                for part in path[:-5].split('/')), 'Invalid Lean source path')
    require(path.split('/')[-1] != 'lakefile.lean', 'Lake programs cannot be adapted')
    return path


def transforms_by_path(execution):
    transforms = {}
    for item in execution.get('source_transforms', []):
        path = lean_path(item['path'])
        lean_path(item['destination'])
        require(path not in transforms, 'Duplicate source transform')
        require(bool(re.fullmatch(r'[0-9a-f]{64}', item['sha256'])), 'Invalid original source hash')
        transforms[path] = item
    return transforms


def adapt(path, data, transform, *, max_bytes):
    """Apply exact replacements, never regex, shell, Lean, or Lake evaluation."""
    if transform is None:
        return path, data
    require(hashlib.sha256(data).hexdigest() == transform['sha256'], 'Stale source transform')
    try:
        source = data.decode('utf-8')
    except UnicodeError as exc:
        raise ValueError('Adapted source must be UTF-8') from exc
    for change in transform['replacements']:
        old, new, count = change['old'], change['new'], change['count']
        require(bool(old) and type(count) is int and 1 <= count <= 1000,
                'Invalid replacement count')
        require(source.count(old) == count, 'Source replacement occurrence count changed')
        require(len(source.encode()) + count * max(0, len(new.encode()) - len(old.encode())) <= max_bytes,
                'Adapted source exceeds limit')
        source = source.replace(old, new)
    return lean_path(transform['destination']), source.encode('utf-8')
