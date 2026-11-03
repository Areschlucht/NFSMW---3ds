# v0.18 prototype source checkpoint

This branch preserves the recovered project and ongoing native port source.
The public main README and its history are preserved. The former project README
is available as docs/DEVELOPMENT.md on the GitHub checkpoint branch.

v0.18 integrates original source map streaming, bounded original collision-bank
queries, source normal-view LOD components, original frontend/car artwork and a
GPU-presented two-screen HUD. Handling and chase-camera motion remain provisional;
whole-car original physics and full-city traversal validation are unfinished.
See V0.18.md and ROCKPORT-PROTOTYPE.md for exact behaviour and limits.

The complete private runtime ZIP and its checksums live under dist/. Original
game archives, converted assets, builds, SDKs and emulator caches are not pushed
to Git. Keep the private recovery backups and game inputs outside the cloud
workspace as well. Authored research snapshots and component comparison reports
are preserved under research/ and tools/; they are not whole-game fidelity claims.

At completed milestones, commit and push source/tests/tools/documentation to
codex/v018-checkpoint-20261103. Do not force-push, overwrite the public main README,
or publish an environment configuration/gameplay release just to make a backup.

## Current whole-game scope (2026-11-03)

Read FULL-GAME-REQUIREMENTS.md and docs/research/whole-game-audit.md before the next
implementation pass. They supersede optional neutral/default filter preferences.
Race-barrier activation/collision, crowded-view performance, full original audio,
per-car lighting, frontend and progression are required. Research/tooling in this
checkpoint does not change the shipped v0.18 runtime or establish full fidelity.

The small whole-game metadata bundle has arrived and passed original directory
range and SHA checks. See docs/research/gameplay-packages-findings.md. Do not ask
for it again. Parallel recovery reports cover event activation, BMW lamp bindings
and music metadata; read their evidence/limits before integrating runtime changes.
A bulk Windows collection helper now splits all four remaining ZZDATA archives
into 47 uploadable 28-MiB-or-smaller pieces with per-archive/per-piece manifests.
Original oversized archive attachments exceed the workspace downloader's 32-MiB
limit. Use tools/reassemble_game_archives.py on complete received sets privately;
never commit original payloads. This is collection/recovery tooling, not a release.
