"""Trusted entry point; run only inside the disposable candidate container."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

module = sys.argv[1]
shutil.copytree('/input/source', '/work/project')
os.chdir('/work/project')
Path('lean-toolchain').write_text('leanprover/lean4:v4.34.0-rc2\n')
Path('lakefile.toml').write_text(
    'name = "proof"\nversion = "0.1.0"\n[[lean_lib]]\nname = ' + json.dumps(module.split('.')[0]) + '\n')
subprocess.run(['lake', 'build', '+' + module], check=True, stdout=sys.stderr)
targets = json.loads(Path('/input/targets.json').read_text())
os.execvp('lake', ['lake', 'env', '/opt/bin/lean4export', module, '--', *targets])
