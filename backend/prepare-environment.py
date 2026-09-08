"""Build a maintainer-reviewed dependency image; never receives PR source."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess


def run(args, **kwargs):
    subprocess.run(args, check=True, **kwargs)


base = Path('/opt/environment')
cfg = json.loads((base / 'environment.json').read_text())
original = json.loads(Path('/opt/gate/toolchain.json').read_text())
if cfg['lean_release'] == original['lean_release']:
    assert cfg['lean_archive_sha256'] == original['lean_archive_sha256']
    (base / 'lean').symlink_to('/opt/lean')
else:
    release = cfg['lean_release']
    archive = '/tmp/project-lean.tar.zst'
    run(['curl', '--fail', '--location', '--retry', '5',
         f'https://github.com/leanprover/lean4/releases/download/{release}/lean-{release[1:]}-linux.tar.zst', '-o', archive])
    assert hashlib.file_digest(open(archive, 'rb'), 'sha256').hexdigest() == cfg['lean_archive_sha256']
    (base / 'lean').mkdir()
    run(['tar', '--zstd', '-xf', archive, '--strip-components=1', '-C', str(base / 'lean')])
    Path(archive).unlink()
os.environ['PATH'] = str(base / 'lean/bin') + ':' + os.environ['PATH']
if cfg['exporter_commit'] == original['exporter_commit'] and cfg['lean_release'] == original['lean_release']:
    (base / 'lean4export').symlink_to('/opt/bin/lean4export')
else:
    exporter = base / 'exporter'
    run(['git', 'clone', 'https://github.com/leanprover/lean4export', str(exporter)])
    run(['git', 'checkout', '--detach', cfg['exporter_commit']], cwd=exporter)
    assert (exporter / 'lean-toolchain').read_text().strip() == 'leanprover/lean4:' + cfg['lean_release']
    run(['lake', 'build', 'lean4export'], cwd=exporter)
    shutil.copyfile(exporter / '.lake/build/bin/lean4export', base / 'lean4export')
    (base / 'lean4export').chmod(0o755)
project = base / 'project'
(project / 'lean-toolchain').write_text('leanprover/lean4:' + cfg['lean_release'] + '\n')
if cfg['dependency_mode'] == 'mathlib-cache':
    lock = json.loads((project / 'lake-manifest.json').read_text())
    for dep in lock['packages']:
        target = project / '.lake/packages' / dep['name']
        target.mkdir(parents=True)
        run(['git', 'init', str(target)])
        run(['git', 'remote', 'add', 'origin', dep['url']], cwd=target)
        run(['git', 'fetch', '--depth=1', 'origin', dep['rev']], cwd=target)
        run(['git', 'checkout', '--detach', dep['rev']], cwd=target)
        if dep['name'] == 'proofwidgets':
            # Lake locates this package's release asset through Git tags. A
            # commit-only shallow fetch omits them; fetching tags never changes
            # the pinned checkout, which is verified again below.
            run(['git', 'fetch', '--depth=1', 'origin', '+refs/tags/*:refs/tags/*'], cwd=target)
    # Cache retrieval is executed only from the approved image context. It is
    # explicitly a trusted dependency cache, never a candidate build cache.
    run(['lake', 'exe', 'cache', 'get', *cfg['cache_modules']], cwd=project)
    assert json.loads((project / 'lake-manifest.json').read_text()) == lock, 'Lake changed the approved dependency lock'
    for dep in lock['packages']:
        actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=project / '.lake/packages' / dep['name'], text=True).strip()
        assert actual == dep['rev']
else:
    (project / 'lakefile.toml').write_text('name = "verification"\nversion = "0.1.0"\n')
(base / 'identity.json').write_text(json.dumps({'environment_id': cfg['environment_id'],
    'environment_digest': hashlib.sha256(json.dumps(cfg, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest(),
    'lean_release': cfg['lean_release'], 'exporter_commit': cfg['exporter_commit'],
    'dependency_mode': cfg['dependency_mode']}))
