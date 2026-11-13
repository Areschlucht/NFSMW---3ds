# Original opening police activation and bounded native chasers

This pass adds a small source-bound pursuit packet and a portable two-car
controller. It does not edit the shared main loop, renderer, player controller,
world/collision packages or SDK/build configuration. It introduces no extra
police model, generated patrol path or replacement source coordinate.

## Original events, actors and actions

The opening-career source pass decodes and traces the actual compressed Lua
handlers. Two original events activate a pair of `copmidsize` vehicles:

| Source event | Spawn trigger | Spawn1 | Spawn2 | Bail trigger | 911 trigger |
| --- | --- | --- | --- | --- | --- |
| 6DDD8383 /16_2_3_sprint | 8760F956 | 993840EA | 0A54490F | 04045A5C | C55B4CBA |
| F7E4440A /16_2_1_d_day_intro | B14F35BA | 52D38E96 | 5D691CB3 | A2568789 | none |

The original controlled-player guard encloses the corresponding source actions:

- Spawn: `SetCopsEnabled` followed by both actual
  `SpawnCop(spawn_reference, "copmidsize", false, false)` calls.
- Bail: `EBailPursuit(1,1)`, then `NoNewPursuitsOrCops()`.
- 911: `E911Call()`.

`tools/build_opening_pursuit.py` consumes the source pass's nine police records,
independently matches every Position/Rotation/Width float against its original
GAMEPLAY byte range and requires the original GAMEPLAY/ATTRIBUTES/DOL digests.
The typed pvehicle/copmidsize reference resolves the actual model `COPMIDSIZE`;
it is not a re-labelled traffic car.

All five source police triggers have Position/Rotation/Width, without Radius or
Dimensions. They must not become guessed spheres. The shared original constructor
recovery establishes the kind1 parameter tuple `(Width,50,1)`, which maps to
source Dimensions `(1,Width,50)` and internal half extents `(Width/2,50,.5)`.
`mw_pursuit_motion` uses `mw_playable_race_width_sweep` for the native controlled
actor proxy and processes intersected triggers by their swept entry fraction.
The proxy is explicitly a port adaptation, not the original rotating actor OBB.

## Private native packet

`/workspace/port-research/opening-pursuit/native-v1/opening-pursuit.npp` is512 bytes,
SHA256
6a51e876bf2bd404ac938b7a9cdcac9d8cf865fba2240a3b4fc600daddd679b2.

NPP1/version1 uses a160-byte header with exact counts/offsets, CRC over16..end,
source model key, separately retained source AI scalars and three source digests.
The two32B event records select their exact two32B spawn records and two/three
32B trigger records. Spawns retain original source Position/Rotation. Triggers
retain original source Position/Rotation/Width and the source-bound action.

The borrowed decoder validates shape/counts, finite/bounded world positions,
record ranges, event ordering, source model consistency, unique action roles per
event, positive Width and reserved bytes before publishing the view. Keep the
source bytes alive and immutable. No allocation is performed by the decoder.

The source `aivehicle/copmidsize` has exact label-bound TopSpeedMultiplier1.6 and
AccelerationMultiplier1.05. Those values are retained separately. Unknown field
7CA3D0A5 is280 and remains unresolved; no speed unit or conversion is invented.
These source values are not falsely presented as the native chase controller's
steering/tactics implementation.

## Native lifecycle and driving policy

`mw_pursuit_begin` binds the current source event, controlled actor identity,
source player position and the existing viewer origin. Other events produce an
inactive pursuit state. No cops spawn until an authoritative matching player
trigger entry. Duplicate entries and other actors do not create another pair.

The two cops spawn at their exact source poses with the original model key.
Source forward maps to viewer yaw `(90+Rotation)` degrees. Their `DriveState`
and height use the same local viewer basis as the player:

```
viewer local = (sourceX,sourceZ,-sourceY) - road.origin
```

The controller is an explicit native policy using the current provisional
`DriveState`/`DriveInput` physics, not recovered original police AI. It follows
the controlled player's actual motion history with a32-point bounded trail,
targets permitted recent trail points, steers toward that target, accelerates
to close distance and brakes around sharper turns or when close behind. It
performs no whole-graph nearest search or per-frame route construction.

Default controller values are labelled platform tuning: top speed65 (the existing
controller cap), closing speed8, follow distance5, trail spacing6 and steering
gain2.5. They are not claimed as original NFS values or per-cop physics. The
caller may tune these bounded values after profiling and hardware feedback.

Each tick calls the caller's physical drive callback at most twice, once per
active cop. The callback mirrors `streamed_drive_step` and must use actual world
collision/ground; a negative load/query error rolls the entire pursuit update
back. A blocked result preserves the previous physical pose and stops motion.
This module does not add dynamic car-to-car collision, bust logic, sirens,
roadblocks, pursuit heat, rubber-banding or original police tactics.

Bail clears active pursuit and prohibits new spawns/pursuits for this event.
Existing actors remain visible but are released into coasting/braking as an
explicit native policy; they do not instantly disappear. Original release AI,
fade/despawn policy and broader pursuit-manager teardown remain separate.
The911 source action emits a signal and latches its state; actual call/radio/audio
playback remains caller-owned. Beginning a different event resets this small
native event-local state; it is not a full persistent pursuit simulation.

## Integration and work limits

Recommended integration:

1. Load/open NPP1 once beside the current career pack. Retain the bytes.
2. At admitted career race start, call `mw_pursuit_begin` with the actual event,
   `road.origin`, controlled player identity and source start position.
3. After each running player step, call `mw_pursuit_motion`. Do not advance it
   during pause/countdown/video. Dispatch its source action signals as supported.
4. Call `mw_pursuit_step` at30Hz with the player's local motion/height and the
   actual streamed collision/ground callback. Freeze when the world cannot admit
   those actors. Read `actors[2].motion`, `.height`, `.active` and `.model_key`.
5. On an explicit teleport/recovery, call `mw_pursuit_relocate` to discard its
   impossible sweep and reset the trail while retaining pursuit state.
6. Render the actual shared COPMIDSIZE mesh, cull by distance/view and keep a fixed
   two-cop budget. Do not clone static-city geometry or decode assets per tick.

The complete host state is576 bytes, with no heap allocation. At most three
unfired source trigger tests run per player-motion update. At most64 trail checks
and two drive callbacks run per controller tick. `MwPursuitWork` reports trigger
tests, controllers, navigation checks, drive calls and blocked steps. Callback
collision work and rendering remain caller budgets and must be profiled too.

## Validation

Host ASan/UBSan tests pass both source event plans and their actual Width-gate
spawning/bail/911 behavior, controlled-actor guards, duplicate suppression,
no-new-pursuit policy, callback rollback and malformed/recomputed-CRC packets.
They run1200 ticks per event at30Hz with the current native driving controller.
The first cop's closest gap to the moving test player decreases from167.1 to7.2
source units and from219.4 to13.1, respectively. Observed navigation work peaks
at three/four checks per tick; drive calls stay at two. This is a flat host
controller fixture, not proof that every actual street corner is negotiated or
that original police behavior/performance has been reproduced.

```sh
PYTHONPATH=tools python tools/build_opening_pursuit.py \
 --evidence /workspace/port-research/opening-career/native-v3/opening-evidence.json \
 --gameplay /workspace/port-research/whole-game-metadata-20261103/GLOBAL-GAMEPLAY-at267364352.BIN \
 --attributes /workspace/attachments/857a1856-1b3b-4be1-8a91-42f437324e6f/ATTRIBUTES.BIN \
 --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
 --output /workspace/port-research/opening-pursuit/native-v1

cc -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic -fno-fast-math \
 -ffp-contract=off -fsanitize=address,undefined -no-pie -Iinclude \
 tests/test_pursuit.c source_bmw/mw_pursuit.c source_bmw/mw_playable_race.c \
 source_bmw/mw_race_session.c source_bmw/mw_event_catalog.c \
 source_bmw/mw_race_progress.c source_bmw/mw_alias.c source_bmw/mw_story_tutorial.c \
 source_bmw/driving_controller.c -lm -o /tmp/nfsmw-pursuit-test
/tmp/nfsmw-pursuit-test \
 /workspace/port-research/opening-pursuit/native-v1/opening-pursuit.npp
```

No SDK build, integrated emulator police run or hardware FPS measurement is
claimed by this subtask. Original assets remain private.
