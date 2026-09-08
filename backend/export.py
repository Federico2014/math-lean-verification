"""Trusted entry point; run only inside a disposable execution container."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

module = sys.argv[1]
project = Path('/work/project')
environment = Path('/opt/environment')
if environment.exists():
    shutil.copytree(environment / 'project', project, ignore=shutil.ignore_patterns('.lake', '.git'))
    # copytree preserves the image's read-only modes. Only this fresh private
    # project copy becomes writable; shared dependency packages stay read-only.
    project.chmod(project.stat().st_mode | 0o200)
    for path in project.rglob('*'):
        path.chmod(path.stat().st_mode | 0o200)
    packages = environment / 'project/.lake/packages'
    if packages.exists():
        (project / '.lake').mkdir()
        (project / '.lake/packages').symlink_to(packages)
    os.environ['PATH'] = str(environment / 'lean/bin') + ':' + os.environ['PATH']
    exporter = str(environment / 'lean4export')
else:
    project.mkdir()
    Path(project / 'lean-toolchain').write_text('leanprover/lean4:v4.34.0-rc2\n')
    Path(project / 'lakefile.toml').write_text('name = "verification"\nversion = "0.1.0"\n')
    exporter = '/opt/bin/lean4export'
# Only bounded Lean sources from the controller are overlaid. Dependencies,
# executable Lake configuration and toolchain files cannot be supplied here.
shutil.copytree('/input/source', project, dirs_exist_ok=True)
os.chdir(project)
roots = sorted({p.relative_to(project).parts[0].removesuffix('.lean')
                for p in project.rglob('*.lean') if '.lake' not in p.parts and p.name != 'lakefile.lean'})
with Path('lakefile.toml').open('a') as stream:
    for root in roots:
        stream.write('\n[[lean_lib]]\nname = ' + json.dumps(root) + '\n')
subprocess.run(['lake', 'build', '+' + module], check=True, stdout=sys.stderr)
targets = json.loads(Path('/input/targets.json').read_text())
os.execvp('lake', ['lake', 'env', exporter, module, '--', *targets])
