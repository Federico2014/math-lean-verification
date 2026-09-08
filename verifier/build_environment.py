"""Build reusable images exclusively from reviewed local environment inputs."""
import argparse
import json
import re
from pathlib import Path
import shutil
import subprocess
import tempfile

from .environments import load_environments
from .registry import ROOT, require, safe_file


def build(identifier, *, allow_pending=False):
    environments = load_environments(ROOT)
    require(identifier in environments, 'Unknown environment')
    env = environments[identifier]
    require(env['status'] == 'approved' or allow_pending, 'Environment onboarding is pending')
    # This tag is populated by the trusted base Docker build in the same job.
    base_id = subprocess.check_output(['docker', 'image', 'inspect', 'lean-gate-tools', '--format', '{{.Id}}'], text=True).strip()
    require(re.fullmatch(r'sha256:[0-9a-f]{64}', base_id), 'Invalid trusted base image identity')
    base_tag = 'lean-gate-base:' + base_id.removeprefix('sha256:')
    subprocess.run(['docker', 'tag', base_id, base_tag], check=True)
    with tempfile.TemporaryDirectory(prefix='lean-environment-') as temp:
        root = Path(temp)
        (root / 'project').mkdir()
        (root / 'environment.json').write_text(json.dumps(env))
        for file in env['files']:
            target = root / 'project' / file['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(safe_file(ROOT / 'environments' / identifier, file['path']), target)
        for name in ('environment.Dockerfile', 'prepare-environment.py'):
            shutil.copyfile(ROOT / 'backend' / name, root / name)
        subprocess.run(['docker', 'build', '-f', str(root / 'environment.Dockerfile'),
                        '--build-arg', 'BASE_IMAGE=' + base_tag,
                        '--iidfile', str(root / 'image.id'), str(root)], check=True)
        return (root / 'image.id').read_text().strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('environment_id')
    parser.add_argument('--allow-pending', action='store_true', help='Diagnostic onboarding only; never grants approval')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'Image identity output already exists')
    image = build(args.environment_id, allow_pending=args.allow_pending)
    with args.output.open('x') as stream:
        json.dump({args.environment_id: image}, stream)


if __name__ == '__main__':
    main()
