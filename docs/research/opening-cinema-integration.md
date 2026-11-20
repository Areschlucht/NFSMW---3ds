# Cached opening cinematic integration

`mw_opening_cinema` joins the existing original camera, actor, action and pose
modules. It loads the three private native assets once, then performs no file
access or allocation during scene admission, stepping or camera sampling. Camera
bytes are bounded at 2 MiB; the actual actor bank is about752 KiB and action asset
about16 KiB. The module stores16 source actor slots and at most16 action systems.

Use app-root `opening-nis.nni` (the camera-v2 export),
`opening-nis-actors.nna` and `opening-nis-actions.nac`. `begin` requires a source
LOCALplayer matrix, the actual ground-corrected scene locator origin/heading and
an explicit terrain provider. It chooses the original camera track rather than
hardcoding track0. Scene types, times and camera-mode transforms remain those of
`mw_nis_director`. All six recovered camera scenes are admitted; IntroNisDDEnd
has actor/timing data but **no camera bank**, and admission refuses it.

`step` preserves the original clock distinction: systems and scene elapsed time
consume the previous scene delta, while actors consume current delta multiplied
by `(0.5f*30.0f)`. Camera sampling is a separate call after the application applies
actor poses and obtains the current LOCALplayer transform. Do not feed one shared
phase timer to both actor and camera paths. Source action systems enter their
original initial state, admit original START transitions only when unfiltered,
fire start-tag/timed0 events, then dispatch original command bytes in source order.
The supplied opening systems have zero filters. Other filters are refused, not
silently ignored. Source action completion uses elapsed>=duration, follows
`System::Update`801ECC2C→`TerminateAction`801ECD18, and dispatches end tags. This
is a bounded opening-system adapter, not the complete generic EventSequencer or
an implementation of each visual/engine event effect. Callbacks must implement
those original commands; a null callback deliberately supplies no effects.

Actors retain original slots0..7 (racer registry),8..15 (police registry). Neither
`Car1` nor slot0 is hardcoded as the player. The original EPlayRaceNIS producer
801E02B8..801E0378 binds racers in VEHICLE_RACERS list order. The application must
supply its actual matching vehicle/model ordering. Outputs are the exact existing
source-world and Bond pose helper matrices; animation scale/quaternion channels
are preserved, not normalized.

## Scene origin provenance

EPlayRaceNIS constructor801DFD04 at801E03B8 tests the explicit GMarker pointer.
For a nonnull marker it reads Bond position+0x28 and direction+0x34. If null, it
uses the first VEHICLE_PLAYERS(1) vehicle, then its rigid-body transform. It
computes heading pi/2−atan2(direction.z,direction.x) and invokes
NISActivity::StartLocation. The implementation80283ABC converts Bond coordinates
`(-sourceY, sourceZ, sourceX)` to source XYZ and truncates the source fixed-turn
heading before `SetAnimOriginPosition`8004A41C. Consequently the NRE race spawn
is a correct locator only if it is that actual supplied marker. A universal
race-spawn assumption is not proven.

CAnimLocator::GetInitialAnimMatricies8004A4A0 reads this registry, queries ground
at its Bond point, replaces sourceZ on a hit, builds the translation matrix, and
uses heading−0x4000 for its source rotation. The integration API takes this
already-corrected origin explicitly. A planar adapter for the current viewer
controller has row0 `(sin(h),-cos(h),0)`, row1 `(cos(h),sin(h),0)`, row2 `(0,0,1)`
and translation `(viewerX+originX,-viewerZ-originZ,height+originY)`. This convention
conversion is not proof that the old bicycle controller is original physics.

## Why ground+5 is not a render placement rule

AnimatedCars_SetMainAndWheels8004CEB0 does perform the previously verified
rigorous terrain query and change incoming BondY to ground+5. The destination
identified at8004CF74..8004CFD0 is **INISCarControl**, with interface handle80050110.
Its concrete method is SuspensionSpline::SetNISPosition80252E74, not a renderer
matrix setter. The first-pose path resets vehicle location and stores
mNISPosition+0x110. Subsequent poses store that incoming matrix but explicitly
preserve the live rigid-body Y position and Y velocity while replacing X/Z:
8025313C..80253180 and802531A0..802531E4. It sets the constrained orientation
later at802535E0..802535F4. The separate SuspensionSpline simulation then computes
wheel/ground forces. Therefore rendering the incoming ground+5 pose directly
would bypass a genuine suspension consumer and can visibly float the car.

This module exposes unmodified source-world/Bond animation matrices and does
**not** apply the ground+5 helper to a display pose. Rendering those raw source
poses is an explicit native preview policy until the complete spline-suspension
consumer is connected; it is not represented as the final original chassis
matrix. The separate verified helper remains available for implementing the
actual INISCarControl boundary.

## Validation

`tests/test_opening_cinema.c` exercises six genuine camera scenes,32 admitted
actor slots,6451 source-clock/camera frames,211 dispatched original commands,
source DD coordinates, distinct first-step actor/camera behavior, unavailable
camera rejection, transactional scene admission and complete cache cleanup.
It passes strict warnings and AddressSanitizer/UndefinedBehaviorSanitizer. The
existing action interval/state/payload regression also still passes. These are
host integration checks; they do not establish SDK rendering/performance or
complete visual event, police-racer registry or spline-suspension fidelity.

```sh
cc -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
 -fno-fast-math -ffp-contract=off -fsanitize=address,undefined -Iinclude \
 tests/test_opening_cinema.c source_rockport/mw_opening_cinema.c \
 source_bmw/mw_nis.c source_bmw/mw_nis_director.c source_bmw/mw_nis_actor.c \
 source_bmw/mw_nis_actions.c source_bmw/mw_nis_pose.c source_bmw/mw_gekko_math.c \
 -lm -o /tmp/test_opening_cinema
/tmp/test_opening_cinema \
 /workspace/port-research/opening-nis/native-camera-v2/opening-cameras.nis \
 /workspace/port-research/opening-nis/native-actors-v1/opening-nis-actors.nna \
 /workspace/port-research/opening-nis/native-actions-v1/opening-nis-actions.nac
```
