# Third-party components

`seccomp.json` is the unmodified Docker default profile from [moby/profiles](https://github.com/moby/profiles/blob/61eaf32614c7c71b60bd8927d3e6a4ffc8ff1f31/seccomp/default.json), licensed under Apache License 2.0; see [Apache-2.0.txt](Apache-2.0.txt).

SHA-256: `536529b665dd0972c37bfb569f5d4ac8a53592e7b00752bc39ff063ca9864c74`.

The container builds fixed upstream Comparator, lean4export, and Nanoda sources under their respective Apache 2.0 licenses. `build-comparator.py` preserves Comparator's copyright header and removes only its executable entry point to expose the export-only verification functions. Source repositories and exact commits are recorded in [toolchain.json](toolchain.json). Lean itself retains its upstream license in the pinned release distribution.
