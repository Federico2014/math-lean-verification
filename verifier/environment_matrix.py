"""Discover all configured environments for non-authorizing backend regression CI."""
import json
import os

from .environments import load_environments
from .registry import ROOT, require


def matrix(root=ROOT):
    environments = load_environments(root)
    require(0 < len(environments) <= 256, 'Environment test matrix must contain 1 to 256 entries')
    return {'include': [{'environment': identifier} for identifier in sorted(environments)]}


def main():
    value = matrix()
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
            stream.write('matrix=' + json.dumps(value) + '\n')
    print(json.dumps(value))


if __name__ == '__main__':
    main()
