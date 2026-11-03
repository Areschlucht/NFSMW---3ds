# Frontend, Alias, cars, races and story source pass

The user explicitly requested no new build. No SDK compilation, emulator run,
3DSX packaging or release was performed in this pass. Host-only checks and UI
raster previews do not establish behaviour on 3DS hardware.

## Frontend and Alias source integration

The app now starts at a Press Start page, followed by Alias Manager for a new
installation or the main menu when an alias is loaded. Main entries are Career,
Challenge Series, Quick Race, My Cars, Alias Manager and Options. This is an initial
3DS navigation adaptation, not recovered exact original layout/ordering. Original
fonts/logo/background are used; FNG animation, transforms and original boot/legal
sequence are not yet implemented. See frontend-flow.md for the99 actual FNGs.

The Alias Manager source supports create/load/rename/delete, with explicit delete
confirmation defaulting to Cancel, the actual target name, case-insensitive
uniqueness and software keyboard input. Deleting a profile does not delete game
archives. My Cars still opens the existing BMW garage. The old free-roam prototype
remains reachable using Y from the main menu. Career, Challenge and Quick Race
currently show that they are unavailable; no fake unlocked career or race is
presented. Do not call this a complete menu port.

`mw_alias.[ch]` implements a separate NFA1 3DS alias save format. Its16-alias,
31-character ASCII limits and allowed character set are implementation choices,
not verified GameCube limits. Full-file CRC covers identifiers, selection, names
and reserved bytes. Rejected input leaves the destination unchanged. Stable IDs
prevent selection/deletion from relying on a shifting row index.

The app writes aliases.pending, flushes/closes it, retains the previous primary
as aliases.bak and renames the pending save into place. Failed promotion attempts
to restore the primary. On load it tries the backup if the primary is invalid.
A detected unreadable save blocks writes; a valid backup may be displayed read-only
without overwriting the damaged primary. This is not a recovered original
memory-card format, nor does it save career/race/garage progress yet. App-level SD
and software-keyboard integration has not been built or hardware tested.

## Race foundation and original story data

`mw_race_progress.[ch]` is a portable race-progress scaffold. It consumes ordered
checkpoint keys supplied by a route, rejects out-of-order gates, tracks laps,
uses caller-supplied integer microseconds and latches completion once. The caller
must issue gate-entry events (not one event per frame while remaining in a gate).
It is tested independently and is not connected to driving or production CFILES.
No trigger geometry, countdown, AI opponent, result/reward, unlock evaluation,
mode-specific rules or original timing behaviour is claimed.

`race_story_export.py` recovers216 ordered checkpoint arrays/1,990 references,
start/finish associations, original positions/rotations and all16 bin requirement
values. Six story definitions contain source IntroMovie/OutroMovie references.
This data will drive race/story integration; filename order and numeric checkpoint
sorting must not substitute for actual reference arrays or original consumers.
See race-story-progress.md for exact provenance and unresolved gating.

All32 original movies are now extracted and validated. See cutscene-recovery.md.
The private six-second story preview is an offline phone-compatible conversion,
not a 3DS player. Native VP6 decoding, audio/video synchronization, keyframe-safe
seeking, skip policy and event ordering remain to implement.

## Model expansion

See car-model-expansion.md: all83 geometry candidates yield some mesh output;
74 selected-LOD packages export fully,9 retain an explicit unsupported part each.
3,028 parts/884,200 triangles and74 standalone body OBJ files are private export
assets, not83 finished drivable cars. Source normals/UVs/material hashes and
header statistics are preserved; unresolved middle vertex channels are not
invented colours. This pass changes no production shared car decoder.

## Host validation and previews

Host ASan/UBSan Alias/race tests pass: CRUD, case-insensitive duplicates, path-like
name rejection, save roundtrip, all5,376 single-bit save corruptions rejected
without state mutation, alias capacity, out-of-order checkpoints, repeated
checkpoints, two laps, premature finish and one-shot completion. UI host checks
pass for framebuffer bounds, original art pack validation and the new title,
Alias and main pages. Only portable C was compiled for these host tests.

Private source-rendered previews (not emulator screenshots):
`/workspace/port-research/frontend-source-pass/frontend-source-preview.png`.
No user hardware test is needed yet. The next integration work is actual route
trigger semantics, original profile/menu flow details, story event ordering and
3DS movie playback, while recovering remaining car material/attachment behaviour.
