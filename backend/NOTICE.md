# Third-party components

`seccomp.json` is derived from the Docker default profile from [moby/profiles](https://github.com/moby/profiles/blob/61eaf32614c7c71b60bd8927d3e6a4ffc8ff1f31/seccomp/default.json), licensed under Apache License 2.0; see [Apache-2.0.txt](Apache-2.0.txt).

Local modification: remove all allow rules for `ptrace`, `process_vm_readv`, and `process_vm_writev`; these syscalls fall through to the default deny action. Candidate and checker processes also run in separate PID namespaces.

SHA-256: `4895b5720b8c15faf3680bfee672531a4c6f8d6938b6a50c4e65f7ae822342bd`.

The container builds fixed upstream Comparator, lean4export, and Nanoda sources under their respective Apache 2.0 licenses. `build-comparator.py` preserves Comparator's copyright header and removes only its executable entry point to expose the export-only verification functions. Source repositories and exact commits are recorded in [toolchain.json](toolchain.json). Lean itself retains its upstream license in the pinned release distribution.
