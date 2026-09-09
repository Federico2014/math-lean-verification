# Protected intake mappings

Optional maintainer-only `<candidate-id>.json` files follow
`schemas/intake-mapping.schema.json`. Each mapping binds the complete canonical
candidate digest, problem/version, optional exact target mapping and source
transforms. `reviewed_metadata_sha256` acknowledges static metadata warnings for
that exact metadata digest; it never permits executing upstream Lake programs.

Merge preparation separately. A candidate PR cannot supply its own mapping.
Changes to candidate materials invalidate the mapping. The preparation report
contains the digests needed for review. No mapping approves an environment,
mathematical statement or proof.
