# Original opening opponents and bounded native racing adapter

This checkpoint adds source opponent identity/spawn recovery, a small native
packet and a practical bounded native controller. Original racing AI, complete
NIS-to-grid placement and physical handling are not claimed to be recovered.
The parent owns actual scene/collision/model admission, integration and results.

## Actual source actors

The ordered Opponents field5839FA1A and its typed references select seven actors
across the five original opening events. PresetRide names resolve through actual
GLOBALB_VM_NGC chunk30220 records, not inferred car names:

| Event | Preset | Actual model |
| --- | --- | --- |
| 42938ce2 partial | RAZORMUSTANG | MUSTANGGT |
| d348f2cd first paid | DDAYSUPRA | SUPRA |
| 6ddd8383 second paid | BL2 | SLR |
| 9f60a40e circuit | OPM_MUSTANG_BOSS | GTO |
| 9f60a40e circuit | OPM_WRX_VERSION2 | IMPREZAWRX |
| 9f60a40e circuit | OPM_RX8_Version3 | RX8 |
| f7e4440a final | RAZORMUSTANG | MUSTANGGT |

OPM_MUSTANG_BOSS is specifically **GTO**, despite its misleading preset name.
The original preset record stores model text at+8 and preset text at+40. All
six model/paint asset conversions are documented separately in
opening-opponent-assets.md, including the custom-kit/vinyl limitations.

## Exact explicit spawn consumer, and null-reference limits

Original801C2A24 reads actor fieldFB84BE75. A nonzero collection reference is
resolved, then Position9F743A0E and Rotation5A6A57C6 are consumed. The original
position mapping at801C2BE0..2C04 writes internal(-sourceY,sourceZ,sourceX), then
801C2D70..2D8C calls the controlled actor's pose interface. Eight unchanged PPC
executions, including all four actual poses and signed-zero/boundary cases,
match the portable coordinate conversion bit-for-bit.

The four explicit references are:

- Partial Razor:66171459, position(2232.653076,-526.409485,122.364197).
- First-paid Supra:1e8d0549, position(1032.814941,137.585205,99.593727).
- Circuit GTO:7be105a5, position(1522.798950,375.961792,98.803703).
- Final Razor:5723e06d, position(920.534790,-628.383606,109.965897).

The other three actors have a null FB84BE75. In particular BL2 has a child named
spawn9d529a6f, but that is not evidence that this consumer selects it. The actual
null branch801C2C50..2D1C uses road navigation802FDC90, original7-unit spacing,
and a lateral term derived from vehicle bounds. This original road-grid producer
has not been ported. The native controller explicitly uses a separate marked
7-unit/1.5-unit grid adapter from the source start pose for these null references.
Those are **not purported original spawn coordinates**. Parent can supply actual
post-NIS actor placement before start; no prior checkpoints are auto-credited.

## Native packet and API

Private packet:
`/workspace/port-research/opening-opponents/native-v1/opening-opponents.nro`

It is774bytes, SHA256
`0cf331d7c4164f099a5648b96e1210cd42083e20801166ec69e675769666e968`.
NRO1 uses a128-byte header, five16-byte event records, seven64-byte actor records
and a bounded string table. Header CRC covers all payload/source identities.
The native reader checks fixed source digests, event/count/order ranges, reserved
bytes, finite poses, literal model path safety and explicit/null spawn agreement.
Fields are borrowed immutable views; parent must retain source packet bytes.

Parent sequence:

1. `mw_race_ai_pack_open` and `mw_race_ai_begin` once outside active frames.
   Begin uses genuine source road-node adjacency and four samples per original
   road curve to build an ordered guide for every route gate and lap. Dijkstra
   and nearest-node scans occur only here, with at most8192 nodes and4096 guide
   points per actor. Output is unchanged on preparation failure.
2. Load each `actors[i].spec.model` from the genuine NPC asset catalog. Use
   `mw_race_ai_place` for authoritative post-NIS poses if available. Call
   `mw_race_ai_admit` for each actor after actual render/collision admission.
3. Call `mw_race_ai_start` alongside the player's race-start clock, after its
   countdown. Tick at30Hz through `mw_race_ai_step`, supplying a real physical
   drive/ground/collision callback, not a no-op motion provider.
4. `mw_race_ai_rank` compares actual source ordered gates/laps and interpolated
   finish times. It refuses unadmitted actors, mismatched player courses and
   failed physical ticks. A failed tick publishes no actor movement/progress and
   makes ranking unavailable until a successful tick. Do not ignore failures and
   award a player win. Exact-time ties favor the player as a native policy.

This module awards **no money, unlocks or career transitions**. The source partial
and final sabotage stages remain scripted outcomes in MwCareer, independently of
the native geometric race route. Only legitimate parent-approved first-place
middle-stage results may reach its original CashValue award bridge.

## Budget and limitations

Three actors maximum. Each tick invokes at most three physical callbacks,
96 guide checks and96 gate tests; no path searches, whole-graph scans, allocation
or disk access. Source road curves are reused without generated roads. The large
fixed path/controller state must be static or heap allocated, not placed on a
small3DS thread stack. Preparation uses temporary heap staging/planner storage.

Cruise/corner speed, tight-turn recovery, steering gains, guide arrival radii,
grid placement and distance tie-breaks are explicitly native choices. Pathfinding
uses source road connectivity but does not yet bind original event road closures
to graph edges; the parent's real collision callback remains authoritative.
Original catch-up, scripted/canned AI, skill/tactics, steering providers and
full source physics are unported. This is not evidence of a1:1 opponent system.

## Validation and reproduce

The source exporter reopens SHA-pinned original GAMEPLAY/ATTR/DOL/preset payloads,
resolves typed keys and verifies original spatial bytes. Its optional original
pose window reference executes unmodified code with an output-write guard.

The strict C11 ASan/UBSan suite passes all five course preparations, seven source
actor identities,4explicit/3native-grid poses,8,400 native physical-proxy ticks,
bounded work, pause/failure rollback, no per-frame planning, ranking/finish-time
ordering, admission guards and malformed/recomputed-CRC source/shape rejection.
After40 seconds each source course's actors advance source-curve guides and
ordered gates under the provisional host drive callback. The host callback has
no map collision and does not establish full-city course completion, hardware
FPS, true physical NPC behavior or original AI fidelity.

```sh
cc -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
 -fsanitize=address,undefined -fno-omit-frame-pointer -no-pie -Iinclude \
 tests/test_race_ai.c source_bmw/mw_race_ai.c source_bmw/mw_traffic.c \
 source_bmw/mw_event_catalog.c source_bmw/mw_race_progress.c \
 source_bmw/mw_playable_race.c source_bmw/mw_race_session.c \
 source_bmw/mw_alias.c source_bmw/mw_story_tutorial.c \
 source_bmw/driving_controller.c -lm -o /tmp/nfsmw-race-ai-test
/tmp/nfsmw-race-ai-test \
 /workspace/port-research/opening-opponents/native-v1/opening-opponents.nro \
 /workspace/port-research/race-story/events-v3.nre \
 /workspace/port-research/street-systems/native-v1/road-network.mwt
```
