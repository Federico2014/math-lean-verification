"""Content-addressed evidence packages; integrity is not proof acceptance."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from .environments import relative_path
from .registry import require

MAX_BYTES = 8 * 1024**3
MAX_FILES = 20000


def digest(stream):
    return hashlib.file_digest(stream, 'sha256').hexdigest()


def inspect_archive(path):
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        require(len(entries) <= MAX_FILES and sum(x.file_size for x in entries) <= MAX_BYTES, 'Evidence exceeds limit')
        names = [x.filename for x in entries]
        require(len(names) == len(set(names)) and 'MANIFEST.json' in names, 'Invalid evidence inventory')
        for item in entries:
            relative_path(item.filename)
            require(not item.is_dir() and (item.external_attr >> 16) & 0o170000 != 0o120000, 'Unsafe evidence entry')
        require(archive.getinfo('MANIFEST.json').file_size <= 8 * 1024**2, 'Oversized evidence manifest')
        manifest = json.loads(archive.read('MANIFEST.json'))
        require(manifest.get('schema_version') == 1 and isinstance(manifest.get('files'), dict), 'Invalid evidence manifest')
        require(set(names) == set(manifest['files']) | {'MANIFEST.json'}, 'Evidence file set differs from manifest')
        for name, expected in manifest['files'].items():
            with archive.open(name) as stream:
                require(digest(stream) == expected, 'Evidence checksum mismatch')
        return manifest


def seal(source, output):
    require(source.is_dir() and not source.is_symlink(), 'Missing evidence directory')
    require(not output.exists(), 'Evidence output already exists')
    files = {}
    total = 0
    for path in sorted(source.rglob('*')):
        require(not path.is_symlink(), 'Symlink in evidence')
        if not path.is_file():
            continue
        name = relative_path(path.relative_to(source).as_posix())
        require(name != 'MANIFEST.json', 'Reserved evidence filename')
        total += path.stat().st_size
        require(len(files) < MAX_FILES - 1 and total <= MAX_BYTES - 8 * 1024**2, 'Evidence exceeds limit')
        with path.open('rb') as stream:
            files[name] = digest(stream)
    require(bool(files), 'Empty evidence')
    manifest = {'schema_version': 1, 'meaning': 'Integrity only; inspect trusted verification and review results.', 'files': files}
    output.mkdir(parents=True)
    temporary = output / 'evidence.zip'
    with zipfile.ZipFile(temporary, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
        for name in files:
            archive.write(source / name, name)
        archive.writestr('MANIFEST.json', json.dumps(manifest, sort_keys=True, indent=2))
    require(inspect_archive(temporary) == manifest, 'Archive readback mismatch')
    with temporary.open('rb') as stream:
        checksum = digest(stream)
    archive_path = output / (checksum + '.zip')
    temporary.rename(archive_path)
    (output / 'archive.json').write_text(json.dumps({'schema_version': 1, 'archive': archive_path.name,
        'sha256': checksum, 'readback_verified': True, 'durable_storage': 'not_configured',
        'formal_status': 'pending'}, indent=2) + '\n')
    return archive_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['seal', 'verify'])
    parser.add_argument('path', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.command == 'seal':
        require(args.output is not None, 'Output directory is required')
        print(seal(args.path, args.output))
    else:
        inspect_archive(args.path)
        print('Evidence integrity verified. This does not establish proof validity or award acceptance.')


if __name__ == '__main__':
    main()
