"""Fail-closed checks inside exactly the same sandbox as proof execution."""
import os
from pathlib import Path
import socket
import sys

assert os.geteuid() == 10001
assert os.getpid() == 1
memory_mb = int(sys.argv[1]) if len(sys.argv) > 1 else 4096
cpus = int(sys.argv[2]) if len(sys.argv) > 2 else 2
assert Path("/sys/fs/cgroup/memory.max").read_text().strip() == str(memory_mb * 1024**2)
assert Path("/sys/fs/cgroup/memory.swap.max").read_text().strip() == "0"
assert Path("/sys/fs/cgroup/pids.max").read_text().strip() == "128"
quota, period = map(int, Path("/sys/fs/cgroup/cpu.max").read_text().split())
assert quota == cpus * period
assert not any(k.startswith(('GITHUB_', 'ACTIONS_', 'GH_')) for k in os.environ)
assert not Path('/var/run/docker.sock').exists()
assert not Path('/input/.git').exists()
# Some kernels create dormant tunnel devices even in a fresh network namespace.
# No non-loopback interface may be UP; dropped capabilities prevent enabling one.
for _, name in socket.if_nameindex():
    if name != 'lo':
        assert int(Path('/sys/class/net', name, 'flags').read_text(), 16) & 1 == 0
assert len(Path('/proc/net/route').read_text().splitlines()) == 1
for path in ['/opt/gate/forbidden', '/input/forbidden', '/etc/forbidden']:
    try:
        Path(path).write_text('forbidden')
    except OSError:
        pass
    else:
        raise RuntimeError('Sandbox permitted protected write')
for family, target in [(socket.AF_INET, ('1.1.1.1', 443)),
                       (socket.AF_INET6, ('2606:4700:4700::1111', 443))]:
    try:
        with socket.socket(family) as stream:
            stream.settimeout(1)
            stream.connect(target)
    except OSError:
        pass
    else:
        raise RuntimeError('Sandbox permitted external network access')
status = Path('/proc/self/status').read_text()
assert 'NoNewPrivs:\t1' in status
assert 'CapEff:\t0000000000000000' in status
assert 'Seccomp:\t2' in status
print('Sandbox probes passed')
