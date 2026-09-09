"""Check restored dependency targets without allowing an implicit source rebuild."""
import subprocess


def check_cached_modules(project, modules):
    # GNU timeout bounds the whole command group, including any child processes.
    # Lake may create missing input .hash files while checking traces, but
    # --no-build rejects any target that would need rebuilding.
    command = ['timeout', '--kill-after=10s', '300s', 'lake', '--no-build', 'build',
               *['+' + module for module in (modules or ['Mathlib'])]]
    print('Checking restored dependency cache (no rebuild; 300-second limit)', flush=True)
    try:
        subprocess.run(command, cwd=project, check=True)
    except subprocess.CalledProcessError as exc:
        if exc.returncode in (124, 137):
            message = 'Dependency cache check exceeded its 300-second budget; environment preparation stopped'
        else:
            message = ('Dependency cache check failed: targets may be missing or stale; '
                       'source rebuild is disabled. Inspect the Lake errors above')
        raise RuntimeError(message) from exc
