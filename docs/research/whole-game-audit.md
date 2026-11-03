# Whole-game audit — USA GameCube, 2026-11-03

This is a research checkpoint, not a new playable build. The shipping v0.18
prototype remains unchanged. The authoritative requested scope is
[FULL-GAME-REQUIREMENTS.md](../../FULL-GAME-REQUIREMENTS.md).

## Evidence and limits

`whole-game-inventory.json` records a read-only audit of SHA-pinned USA Speed.dol,
ATTRIBUTES.BIN and ZDIR.BIN, checked converted section payloads, and production
CFILES. `tools/audit_whole_game.py` reproduces it. Path hashes are candidate
identifications until payload and consumer validation; strings can be shared or
unreachable platform code. Collection counts are not car, song or object counts.
The audit contains no original game payloads.

## System status

| System | Evidence available | Live prototype / next proof required |
| --- | --- | --- |
| Boot, title, menus, profiles | Original frontend archives, fonts/artwork; DOL PressStart.fng and MainMenu.fng references | Prototype interface only. Recover actual GameCube frontend flow, transitions and settings. |
| Career, events, unlocks, rewards | Parameter database and game-flow strings; two directory records for GLOBAL\\GAMEPLAY.BIN | No original complete career. Obtain both records, recover event ownership, routes and unlock graph. |
| Movies, story, loading | Original movie stems and .vp6 string; frontend loading references | No verified complete movie set or player. Identify media from disc listing and headers, then bounded playback and AV sync. |
| Cars and customization | BMW geometry/textures and shared car assets; physical vehicle definitions | BMW prototype only. Other cars need their geometry, textures and preset/kit binding. Parameter definitions alone do not establish the playable roster. |
| Driving and camera | Recovered parameters, original-function research and comparison helpers | Production CFILES link neither mw_physics_* nor mw_original_camera_* modules. Current driving/chase remains provisional; integrate original systems and compare trajectories. |
| City streaming and visibility | Converted complete stream inventory: 997 sections; source collision banks | Native streaming/rendering and bounded collision queries work. Full original visibility, event ownership and whole-city traversal are not validated. |
| Barriers and career gates | Six player/traffic/locked barrier models; FREE_ROAM, SCENERY_GROUP_, PLAYER_BARRIERS_ and enable/disable strings | Missing full activation rules. Recover event/group ownership, then apply identical activation to draw/collision/AI. Never hide every object containing ARROW or BARRIER. |
| Collision, breakables and AI | Ground/wall query integration, smackable/damage/pursuit/traffic definitions | Current guard is not full original compound-body response. Recover dynamic objects, damage, pursuit breakers, traffic/police state machines and navigation. |
| Materials and post-processing | Source vertex colours/normals, texture blends, original visuallook parameters and curve consumers | Basic PICA shaders exist. Optional gain-only grade is inaccurate and superseded by mandatory original treatment. Final GC pass bindings, bloom/composite and material semantics need recovery. |
| Vehicle lamps | BMW left/right headlamp, glass and brake meshes already exported; six unresolved aliases | Restore per-car/preset/kit bindings and original on/off/damage producers. Lamp geometry is not missing from this BMW export. Other vehicles require their own assets. |
| Audio and music | Engine/audio attributes, engine/shift/turbo/speech paths, music index/stream directory matches | No audio module in production CFILES. Identify headers/codecs and original bank mappings before player/DSP streaming integration. |
| HUD, save/load and platform adaptation | Original frontend resources and GPU-owned bottom HUD presentation | Complete original HUD, persistence, inputs and dual-display flows remain unfinished. Emulator captures do not certify hardware flicker resolved. |
| Multiplayer | Must establish actual USA GameCube functionality | Do not infer Xbox Live or PC features from shared code/manuals. Define feasible 3DS adaptation only after source/reference verification. |

## Barrier correctness and cost

The inventory finds 8,763 unique barrier instance occurrences across the converted
stream. This is not the simultaneously visible count. The six specific models
are only four triangles each, but neon textures include source-alpha and additive
layers; non-opaque drawing disables depth writes. Near-wall screen coverage and
overdraw are plausible costs alongside submission and duplicate activation.
Hardware timing must distinguish CPU work, submissions, GPU work and transparent
coverage. 15 FPS is about 66.7 ms/frame; 30 FPS allows 33.3 ms and 60 allows 16.7 ms.
New 3DS CPU boost is not evidence of sufficient GPU budget.

Original group strings and conservative constant references establish vocabulary,
not recovered group ownership or callable visibility semantics. Unknown L2RA
chunks must not be relabelled as group tables without tracing their consumers.
Use one authoritative object-activation state for render, collision, navigation,
AI and sound. Retain real career district locks while suppressing inactive race
barriers. Profile the same route/camera before and after changes.

## BMW lights and general vehicle binding

The exported BMW includes left/right brake lamps, headlamps and headlamp glass.
Six aliases remain unresolved: 02b52399, 267d188c, a532fc46, a7e6ea53, d947f346,
f68ef19f. Existing material research traces original initializer 802DB7CC and
headlight update 802CAA44. Headlight glass resolves through WINDOW_FRONT context;
it must not be globally replaced with a guessed glass texture. Brake state and
damage suppression need their producers traced as well as the material consumer.
See `research/notes/materials-fidelity/findings.md` and
`tools/material_recovery_vehicle.py`. Integrate a per-vehicle resolver, not BMW
texture aliases applied indiscriminately to every car. Original lamps, emissive
surfaces and effects do not imply adding modern shadowed spotlights everywhere.

## Sound and visual implementation constraints

Seventy engineaudio collections are not seventy verified car banks. Preserve
original shared banks, RPM/load dimensions and acceleration/coast/shift behaviour.
Separate EA Trax from interactive pursuit scoring, police dispatch and story
speech. Identify original codec payloads first; stream asynchronously with bounded
memory rather than loading the 131 MB music stream into RAM. Recover voice
priorities, ducking, attenuation, pause/Speedbreaker effects and cutscene sync.

GameCube uses GX/TEV; translate its actual material/pass behaviour to PICA.
Original visuallook data includes tint, intensity, desaturation and bloom curves;
those parameters do not justify directly multiplying the world by a yellow tint.
Recover the pass chain and channel bindings. Preserve original treatment without
a disable toggle; avoid double grading original UI and pre-rendered movies.
Budget correctness/visibility/overdraw before additional full-screen passes.

## Original flow to recover

Boot/legal -> Press Start -> profile/frontend -> Career introduction or other
selected mode -> loading/event setup -> countdown/race/pursuit -> results,
rewards and progression -> free roam/safehouse/shop -> save and subsequent story.
Recover transitions and condition checks from original consumers and event data.
Do not implement the progression graph using guessed event counts or thresholds.

## Next required inputs

The small metadata helper requests seven names yielding eight original payloads:
two distinct GLOBAL\\GAMEPLAY.BIN records, five SOUND\\PFData music MPF indices,
and TRACKS\\PRECULLERBOOBOOSCRIPT.HOO. Total 4,294,123 bytes, all from ZZDATA1.BIN.
Preserve both gameplay records until original duplicate selection is understood.
The HOO name suggests visibility relevance; its format and use remain unproved.
The helper also lists relative media filenames and sizes, not their contents or
personal absolute paths. Full movies/music/other cars can be requested selectively
once their names, headers and actual requirements are established.

The supplied ZZDATA3 first-64-KiB sample already covers the beginning of the
candidate MW_Music.mus stream. Do not request that header again. No full audio or
video set is verified available. GAMEPLAY is distinct from ATTRIBUTES.BIN.

## References consulted and gaps

- Own supplied USA GameCube DOL, attributes, directory, frontend/car/world assets;
  private raw inputs remain outside Git.
- [2005 game overview](https://en.wikipedia.org/wiki/Need_for_Speed:_Most_Wanted_(2005_video_game)):
  shared high-level career, race and pursuit context; not exact GameCube evidence.
- [GameCube listing](https://www.gamesdatabase.org/game/nintendo-gamecube/need-for-speed-most-wanted):
  its linked manuals do not establish a GameCube manual.
- [Xbox manual](https://www.gamesdatabase.org/Media/SYSTEM/Microsoft_Xbox/manual/Formated/Need_For_Speed_-_Most_Wanted_-_2005_-_Electronic_Arts.pdf):
  shared menu/gameplay descriptions only. Platform controls and Xbox Live do not
  transfer to GameCube. Private OCR reference retained outside Git.

Exact GameCube boot/menu captures, event rules, media selection, runtime sound and
render comparisons remain necessary. No GameCube playthrough was reviewed in this
pass. This document is a system inventory and evidence boundary, not a claim that
the entire original engine has been understood or reconstructed.
