# Native playable race controller

`mw_playable_race.[ch]` connects the existing original-data catalog and ordered
race-session scaffold to a bounded movement detector. It is a native 3DS port
implementation, **not a recovered one-to-one GameCube actor/trigger predicate**.
This subtask changes no shared main loop, renderer, catalog, world activation,
source assets, build lists or SDK configuration. Parent integration supplies them.

## Retained original source data

All82 supported P2P/circuit definitions in events-v3.nre have valid Position,
Rotation and positive Dimensions at every selected checkpoint and finish. This
is749 source gate uses before repeated laps. Ordered references remain exactly
those selected by the original source arrays, including deliberately absent
checkpoint numbers. The controller never sorts checkpoint names or turns all
source child objects into route nodes.

Five opening definitions already supported by the native catalog are:

| Key | Source definition | Rule | Ordered checkpoints |
| --- | --- | --- | ---: |
| f7e4440a |16_2_1_d_day_intro| P2P,1 lap |10|
|42938ce2|16_1_0_partial_dday|P2P,1 lap|4|
|d348f2cd|16_2_2_sprint|P2P,1 lap|6|
|6ddd8383|16_2_3_sprint|P2P,1 lap|6|
|9f60a40e|16_1_1_circuit|Circuit,2 laps|7|

This table is source inventory, not a claimed chronological career sequence.
Actual story state ordering, branching and outcome conditions belong to the
separate original-career recovery. Completing a native timed route does not
award an original career win, cash, unlock, forced loss or car automatically.

The career subtask subsequently recovered the selector's source order as
partial_dday → sprint2 → sprint3 → circuit → d_day_intro. That order is supplied
by the separate opening-career pack, not inferred from the table above. It also
identified scripted endings: partial_dday has a Mia-call trigger40caf8c1, and
the final d_day_intro has sabotage triggerf73bbbcb followed by the original
engine-blown/timer/car-lot flow. **Neither should be converted into an ordinary
career win by a generic route-finish notification.** Parent must execute the
verified script policy and cancel/finish the native session as appropriate.
The public pure sweep helper can test a separately supplied special trigger
node, independently of the next ordered route checkpoint. It does not schedule
phone calls, engine sabotage, timers, movies or car-lot transitions itself.

## Coordinate and geometry contract

The API always accepts source `(X,Y,Z)` coordinates, whereZ is vertical. Original
trigger-constructor recovery establishes internal position `(-Y,Z,X)`, negative
source rotation in degrees and box half-extents `(DimensionsY/2,DimensionsZ,
DimensionsX/2)` in that internal basis. This module retains those meanings.

For actual collision between a moving car and gate, the original directed
contact generator, concrete vehicle provider and notification scheduling are
not ported here. Instead this controller intersects a straight movement segment
with the source oriented box expanded independently on all axes by a finite
nonnegative caller-selected actor radius. This is conservative around corners,
and is not exact swept sphere-versus-box or an original vehicle shape. Source
Radius, when present, takes precedence over Dimensions; that branch uses a
segment/sphere query expanded by the actor radius. Original optional plane/slab
consumers are not substituted with guessed behavior. Missing or invalid shape
data makes preparation fail. Width-only special triggers use the separately
recovered conversion below; NRE1 does not acquire a guessed extra field.

Touching counts as inside in this native policy. A movement beginning inside a
gate does not create an entry; leave and re-enter first. Sweeps catch entries
even when both endpoints are outside a thin gate. Several expected gates may be
accepted in one movement, but only in chronological entry order. Earlier entry
into an out-of-order gate is ignored. Repeated or coincident references require
a distinct later entry. There is no invented original wrong-way penalty.

The viewer adapter maps source to `(X,Z,-Y)`. With the native drive controller's
yaw0 facing viewer+Z, source forward `(cos R,sin R,0)` maps to viewer yaw
`(90 + R)` degrees. The getter normalizes this and returns radians. This binds
the port's heading convention to source Rotation; it does not claim recovery of
the original vehicle matrix constructor or start-grid slot placement. The source
startgrid position is retained, without fabricated opponent slot offsets.

## Original Width-only special triggers

The opening career/police script markers use Width without Dimensions/Radius.
Original8019ACC0..8019ACFC sets **kind1**, not kind3. It stores internal dimension
parameters `(Width,50,1)`, using actual float constants50 at803EC3B8 and1 at
803EC3A8. Its broad-phase squared-radius operand is the fused single-precision
expression `Width * (Width * .25) + .25`; this is not a sphere definition.
The later vertical doubling and kind1 narrowphase halving establish internal
half-extents `(Width/2,50,.5)`.

`mw_playable_race_width_sweep(pose,width,from,to,actorRadius,&fraction)` converts
that proven fallback into equivalent source Dimensions `(1,Width,50)` and then
uses this module's explicitly native swept actor proxy. It rejects supplied
Dimensions/Radius so it cannot accidentally change their original priority.
Keep Width separately in the source career/pursuit sidecar and pass a source
Position+Rotation pose. No `MwEventNode` disk layout or NRE1 schema is changed.

`tools/race_width_reference.py` executes the unchanged original scalar window
with bounded writes/instructions. All17 numeric cases from .125 through1024,
including50/100/160, match parameter bits, kind1 and broad-phase FMA output.
Private report: `/workspace/port-research/race-triggers/width-verification.json`.
This corrects the earlier supposition that Width could require a kind3 slab;
the actual kind3 consumer is separate. It still does not prove the full original
actor detector, direction/plane predicates or script-notification scheduler.

## Lifecycle and integration

Initialize a `MwRaceSession` and `MwPlayableRace` to zero and keep both at stable
addresses. The controller borrows the session and catalog; it allocates nothing.
It must be the session's only lifecycle owner until finish or cancellation.

1. Call `mw_playable_race_prepare(r,s,c,event,aliases,actor,radius)` instead of
   separately preparing the session first. It validates all required source
   gate geometry and selected Alias before publishing state.
2. Obtain the original starting transform with `mw_playable_race_start_pose`.
   Parent converts the source position to viewer/local coordinates, admits the
   renderer/collision and applies this event's original scenery activation.
3. Call `mw_playable_race_admit` with all three actual readiness results. No
   missing admission silently succeeds. The controller does not mark a world
   ready, clear a stream error or move the car itself.
4. After required movie/NIS policy completes, begin a caller-chosen countdown
   using `mw_playable_race_countdown(duration_us,position)`. No original duration
   is guessed and no story video is automatically skipped. Freeze driving while
   phase isCOUNTDOWN. Updates emit `started` when the running phase begins.
5. Advance physical driving only inRUNNING. Once physical motion and streamed
   world admission have succeeded, pass the controlled actor's actual source
   position and integer microseconds to `mw_playable_race_update`. Do not report
   speculative movement that the parent later rolls back.
6. `mw_playable_race_next` supplies the expected original gate for navigation.
   Pause/resume freezes both countdown and running time. Successful finish is
   latched once; elapsed time stops at the interpolated finish entry within the
   movement segment. No remaining frame time is added after finish.
7. Parent shows results and applies only its verified career outcome. Cancel
   exits without finishing. Parent restores the appropriate free-roam activation
   snapshot and maintains its own car/world transition policy.

For an explicit reset/recovery, `recovery_pose` returns the last accepted gate
center/rotation, or the source start transform before a gate is accepted. The
parent must find/admit physical ground and decide whether that point is usable.
After an actual admitted teleport, call `relocate` to discard the teleport sweep
without granting checkpoints or consuming race time. It is not an original reset
scheduler and should not be used to award synthetic race completion.

The update's last event, gate key and crossing count support HUD feedback.
Session progress retains exact ordered checkpoint/lap state and integer elapsed
microseconds. Floating-point segment interpolation is native geometry; original
float bit parity and original timing producers are not claimed.

## Validation and limits

Strict C11 compilation with warnings-as-errors, pedantic checks, ASan and UBSan
passes the new test. All82 source courses, including all five opening definitions,
complete1,156 source-bound checkpoint/lap/finish entry operations across their
declared laps. Tests explicitly relocate to the outside of each expected gate to
exercise the actual source volume; this is not an autonomous physical driving
run and supplies no renderer, world collision or opponent evidence.

Independent synthetic fixtures cover axis/90-degree rotations, horizontal and
vertical boundaries, source Radius precedence, bounded proxy expansion,
start-inside suppression, high-speed entries with both endpoints outside and
four chronological gates in one movement. The latter reaches a finish at source
X39 in a0→50 movement of1,000,000us and records780,000us, rather than a full frame.
Further fixtures cover ignored out-of-order entries, duplicate references,
countdown time splitting and pause, wrong actor, explicit recovery, zero-input
motion, malformed source shape, nonfinite input, elapsed overflow, preparation
failure rollback and one-shot finish/cancel.

```sh
cc -std=c11 -Wall -Wextra -Werror -pedantic \
 -fsanitize=address,undefined -fno-omit-frame-pointer -no-pie -Iinclude \
 tests/test_playable_race.c source_bmw/mw_playable_race.c \
 source_bmw/mw_race_session.c source_bmw/mw_race_progress.c \
 source_bmw/mw_event_catalog.c source_bmw/mw_alias.c \
 source_bmw/mw_story_tutorial.c -lm -o /tmp/nfsmw-playable-race-test
/tmp/nfsmw-playable-race-test \
 /workspace/port-research/race-story/events-v3.nre
```

This subtask does not establish actual3DS race integration, frame rate, original
AI opponents, traffic, movies/NIS, starting grids, collision response, replay,
original camera, original race penalties or the career result/reward interpreter.
