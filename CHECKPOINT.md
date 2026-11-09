# v0.18 prototype source checkpoint

## Active checkpoint: unlocked exploration and two-screen destinations

The newer integration in docs/research/exploration-preview-validation.md
supersedes the historical no-build/context-zero status below. The user authorized
a preview build and screenshots, and requested inactive race arrows removed from
free roam while preserving their ability to activate in races.

The streamed app now loads one source-bound exploration.nws for both renderer
flags and collision group admission. Normal draw context is0x10; the cold Bin1
exploration plan suppresses inactive race arrows without deleting source assets.
Actual career-bin plans remain separate; this shortcut is unlocked exploration,
not a simulated career save. Four original safehouse regions pass bounded
renderer/collision admission; this does not establish every city route drivable.

free-roam.nfd supplies original destination positions and explicit actions.
D-pad Up opens race preparation, parts-shop or safehouse navigation when nearby;
Start opens pause/Jump to Safe House. Returning from those screens preserves the
car pose. Race starts, purchases, upgrades and original actor triggers remain
unfinished. frontend-top.nut adds original artwork and a live car above the
bottom navigation. This is a two-screen adaptation, not an exact DS replica.

Private preview assets and binary must travel together. Do not replace the public
main README or commit original archives, converted assets or the runtime ZIP.

## Historical checkpoints

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

All four original ZZDATA archives are now reconstructed and verified against the
user's per-piece and whole-archive SHA256 manifests: 47 pieces, 1,332,729,856 bytes.
Private canonical files: /workspace/port-research/original-archives/ZZDATA0.BIN
through ZZDATA3.BIN. All 1,363 original ZDIR record ranges fit those source files.
See docs/research/archive-receipts.json. Do not request these archives or pieces
again. Internal asset identities, format decoding and runtime integration still
need recovery; source availability is not a whole-game implementation claim.

Post-collection integration progress is in docs/research/current-integration-progress.md.
Original render flag gate is now called by stage_draws; default prototype context
stays zero until collision/event ownership is recovered (free-roam walls not fixed).
Native BMW lamp bank and complete music extraction/decoder checks are reproducible
from new tools and private originals. Car candidate geometry coverage and failures
are measured without relaxing strict decoding. Do not claim audio/lights/cars are
integrated from read-only exports. No new release ZIP was published in this pass.

Latest user steering: NO NEW BUILD. Prioritize cars, original menu/Alias flow,
races, story and cutscenes. See docs/research/frontend-race-story-source-pass.md.
App source now includes Press Start/Alias/main navigation; portable Alias save
codec and race progress scaffold have host tests. Career/races/cutscene playback
are not playable yet. No SDK build/emulator run/release in this pass. All83 car
packages have private expanded exports (74complete/9partial); all32 movies and99
FNG layouts recovered;216 ordered route arrays +source story/bin refs available.
Do not ask for these files again. Original media/meshes remain private.

Resumed after usage interruption: native event catalog/type/tutorial and Alias
fixes are described in docs/research/native-event-source-pass.md. Current private
event pack is /workspace/port-research/race-story/events-v2.nre (NRE1/version2);
older events.nre is previousversion. Host end-to-end tests cover216 source-bound
routes; event modes match the actual original string table and unknowns stay-1.
Tutorial selector480 PPC/native matches; no career/movie auto-flow is invented.
Alias codec nowwritesversion2 with monotonic IDs and v1 migration; unreadable
save handling and touch/controller precedence fixed in app source. NO SDKbuild,
emulator run or release this pass. Original trigger narrowphase mismatch remains
an open gate before playable race integration. Original media remain private.

Latest source checkpoint: docs/research/race-session-source-pass.md. Current
private localized event pack is events-v3.nre; the app expects events.nre onSD
when a future package is authorized. Do not overwrite old private pack versions.
Source Quick Race browsing now uses79 genuine localized preparation candidates,
Alias-bound MwRaceSession, and explicit unavailable start; this is NOT the original
unlock/eligibility list or playable races. All3 admission domains gate readiness.
Host tests cover82 lifecycle simulations and v2/v3 compatibility. The aligned
collision reference discrepancy is resolved as directedcontact, not symmetricSAT;
rotated actor/motion/notifications stillopen. Preserve legitimate career gates:
profile BinIndex determines original reset/apply plan. No SDKbuild/release yet.

Latest user instruction authorized a preview build and screenshots after this
checkpoint. The new nfsmw-race-menu-preview.3dsx compiled/linked and was run in
Azahar; see docs/research/race-menu-preview-validation.md. Actual public docs
captures under docs/previews/race-menu show main menu, source-named course browser
and existing free roam. Test Alias creation/saved CRC checked; race start remains
unavailable. Original region-lock plans now traced through profileBinIndex and
reset/apply. No publicbinary/releaseZIP; raworiginalassets/media stayprivate.
