# Source checkpoints and private backups

The recovered development source is checkpointed on GitHub branch
`codex/v018-checkpoint-20261103`, based on the existing main history. The public
README is preserved; the original developer README is copied to
`docs/DEVELOPMENT.md` on that branch. Main gameplay still has provisional
physics; component reference comparisons are not whole-game fidelity claims.

At completed, reviewable milestones, commit and push incremental source,
tests, tools and documentation checkpoints. Preserve active working files and
existing remote history. Do not force-push or publish a gameplay release merely
to create a backup.

`research/` snapshots authored notes and small comparison reports, with file
hashes and explicit omissions. Asset-dependent checks still need original
inputs and generated private data.

Four complete recovered-directory ZIP backups were created and verified on
2026-11-03: project (including Git/build artifacts), research, original inputs,
and toolchains. Their manifest/checksums are in the downloadable recovery export.
Save those backups outside the cloud workspace. Game archives, converted game
assets, SDK/emulator caches and generated executables are not pushed to Git.

The images under `docs/progress/` are actual emulator captures of the recovered
prototype, not hardware benchmarks or proof that full original physics/full-city
streaming have been integrated. No v0.18 gameplay release is claimed.
