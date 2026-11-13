# Original wheel-force integration boundary

This pass adds `mw_vehicle_dynamics.[ch]`, a source-profile packer and host
tests. It does not replace the live provisional `driving_controller`, change
`main`, or claim a1:1 GameCube driving experience. The original per-wheel
physics is substantially recovered; missing whole-car producers must not be
silently replaced with intuitive steering/grip gains and called original.

## What is now usable

The native wheel-force stage composes existing independently compared original
components in their recovered order:

1. Derive source speed/gear/mode/effect contact scales and prepare **all four**
   wheels, preserving previous compression, slip, velocity and lock state.
2. Require the caller's mechanical/aero phase. No implicit no-op is installed.
3. Run original engine-output torque distribution using previous wheel state,
   source TORQUE_SPLIT and DIFFERENTIAL values. Inputs still supply actual engine
   output, body-local velocities, steering and assist state.
4. Require the caller's original brake/handbrake/input-assist routing phase.
5. Snapshot the four previous compressions for the original antiroll terms.
6. Build actual physical wheel mounts, query points and point velocities from
   body pose, angular/linear velocity and world CG offset.
7. Ask the caller's world query for each exact point, original relative contact
   plane and actual material's LATERAL_GRIP/DRIVE_GRIP/ROLLING_RESISTANCE.
8. Execute source spring/damper/contact or free-spin behavior, then compute the
   original adjusted force application point and moment for each wheel.

The returned four forces/moments remain separate and ordered. The wrapper does
not substitute a summed force, direct yaw change or positional speed increment
for the original chassis force accumulation, bottomout correction and body
integration. It does not infer an original scheduler from the prototype's120Hz
substeps. Missing required hooks, late query errors, nonfinite state or invalid
identity reject without committing state or output. Callbacks must not mutate
external gameplay/progression; their side effects cannot be rolled back.

The query's `present=false` selects the recovered free-wheel brake stage and
zeroes compression while accumulating airborne time as an explicit native
absent-plane policy. Original query scheduling/default-plane producers remain
outside this wrapper. A supplied plane instead follows the original compression
test, including compressed-but-steep free-spin that resets airborne time.

## Physical profiles, not visual car normalization

Private profiles are under `/workspace/port-research/driving-runtime/`:

- `m3gtre46careerstart.ndp`: canonical opening BMW physical profile39DAE0F8.
- `bmwm3gtre46.ndp`: generic physical model4E085FB3, a different profile.
- `cobaltss.ndp`, `gti.ndp`, `is300.ndp`, `punto.ndp`: explicitly selected source
  pvehicle rows, with component upgrade index0 recorded rather than inferred.

The canonical preset-to-physical-profile binding was independently recovered in
the drivetrain work. Using the renderer's visual ecar key as the opening BMW
physics key would select the wrong vehicle data. The generic and career BMW
differ in actual attributes: for example career FRONT_AXLE1.5 and WHEEL_BASE2.725
versus generic values1.43 and2.73. Keep model/preset/physical identity separate.

NDP1 stores52 float32 source parameters: MASS; original tire dimensions; both
spring/damper/valving/travel/ride-height axles; static/dynamic/grip curves' source
scales; brake/handbrake/lock values; initialized source brake calibration;
track/axle/wheelbase/swaybar; tire STEERING; torque split and three differential
values. Every field has original byte provenance in the adjacent JSON. The
JSON also retains all47 source simsurface rows; the wrapper never invents an
asphalt default or assumes all surface grip values are1.

The caller must supply actual physical body half extentY, body pose, world CG
offset and velocity state. Visual NVC half extents, source artwork TireOffsets
and wheel rig pivots are not valid replacements for physical collision/body
parameters. Likewise, contact `plane.w` must be produced with
`world_collision_ground_contact_plane` from the actual source triangle and query
point, not from a flat road-height approximation.

All vectors in this API use the original source-native Y-up world frame. Native
world is `(-sourceY,sourceZ,sourceX)`; current viewer world is
`(sourceX,sourceZ,-sourceY)`. Passing an unchanged viewer matrix, angular velocity
or moment is incorrect. The basis conversion exchanges X/Z and changes
handedness; axial quantities require the corresponding orientation treatment.
An eventual bridge must compare actual pose/force/moment transformations against
the source providers rather than guessing the sign of vehicle yaw.

## Newly recovered steering arithmetic

Original no-assist fallback80248A34..80248A78 reads tires required-layout+48,
the exact STEERING attribute. It starts with45degrees, multiplies by STEERING
unless source vehicle mode is1, multiplies by state+8C steering, then converts
to turns with the original float32 `0.0027777778450399637`.

`mw_vehicle_dynamics_steer_fallback` implements that observable branch. **Normal
player steering can instead choose802484F8** through the original interface+FC.
That path uses speed/yaw/control curves, rate limits, effects and smoothing;
the no-assist function is not a substitute for that player behavior.

Original Ackermann slice80244C4C..80244CD0 uses front TRACK_WIDTH and WHEEL_BASE.
After the source turns-to-radians multiplication and wrap, it computes the inner
and outer angle with original float boundaries and FMADD order. The native
function returns left then right angle, preserving the original argument/output
mapping. These angles still need original trigonometry and body-vector rotation.
The wrapper accepts already-produced wheel directions and does not invent them
from raw Circle Pad input.

## Fresh verification and scope

`build_vehicle_dynamics.py --verify-original` executes unchanged bounded original
PowerPC slices with source values from career BMW, generic BMW and all four
starter profiles. It passes **1536 fallback cases plus1536 Ackermann cases** with
zero float-bit mismatches. The Ackermann stop is before trigonometry; this is not
a claim that arbitrary target `sinf/cosf` matches the original math library.

The host C11 ASan/UBSan test loads the real canonical336-byte pack and exercises
all-wheel phase ordering, prior-contact torque distribution, source handbrake
torque behavior, airborne rear locking, missing-hook failure, late-wheel query
rollback and recomputed-CRC corruption. Its mechanical/input/query fixtures are
explicitly synthetic, with actual source asphalt scalars. They test orchestration
and do not masquerade as recovered player input producers or a driven lap.

A perfectly straight source wheel with zero slip follows a different lock-test
path than a wheel with lateral/slip motion. The test compares identical contact
states with and without rear handbrake, checks reduced rear angular speed and
unchanged front state, then exercises actual free-wheel lock behavior. It does
not tune source brake forces merely to force a lock at one arbitrary speed.

Earlier component evidence remains relevant:1024 stateful original ground-wheel
stage comparisons,2048 physical mount/point-velocity and2048 force-moment cases,
plus original engine/clutch/automatic/distribution comparisons. Those reports are
component or stage-chain evidence, not uninterrupted whole-car telemetry.
Default runtime `powf` previously differed in32 of4272 spring-force cases, with
maximum0.015625N; original callbacks closed those offline comparisons. Exact
Gekko exceptions/control state, subnormals and arbitrary FMA ties are not claimed.

## Remaining gates before replacing the positional controller

- Original player steering802484F8, input/common-state producers and brake/assist
  routing802498B4; source phase values must replace the explicit fixtures.
- Mechanical/aero802455E0 and its complete body force/moment contributions.
- VehicleParams mass/inertia/halfextent/CG binding and original force accumulation.
- Bottomout chassis correction, rigid-body integration and source tick scheduling.
- Original gearbox input/gear commit policies and unsupported engine branches:
  positive induction, nonempty RPM limiter and active rev modulation remain
  rejected by the existing recovered supported engine step.
- Material/contact timer persistence, car-to-car/object collision impulses and
  driving comparisons against actual original whole-car trajectories.

The existing recovered engine step can supply the distribution's engine torque
after those actual source phases are sequenced. A native adapter may deliberately
bridge missing phases for playability, but must label the resulting behavior as
an approximation until these gates close. No new number in this pass is a
subjective drift, camera-glue or speed tuning constant.

## Format and reproduce

NDP1 is336bytes: a128-byte header and52 little-endian float32 scalars. Header
words contain version1, exact size, CRC(bytes16..end), physical/tires/brakes/
chassis/transmission keys, payload offset128 and count52. Bytes44..63 are zero;
the original ATTRIBUTES and DOL SHA256 digests occupy64..95 and96..127. Native
decode validates digests, identity, bounds, finite values and basic dimensions,
copies scalars and binds the existing static original lateral curves. It allocates
no memory and borrows no file buffer.

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps \
python tools/build_vehicle_dynamics.py \
 --attributes /workspace/attachments/857a1856-1b3b-4be1-8a91-42f437324e6f/ATTRIBUTES.BIN \
 --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
 --profile m3gtre46careerstart \
 --output /workspace/port-research/driving-runtime/m3gtre46careerstart.ndp \
 --verify-original
```

For ambiguous RefSpec upgrade arrays, pass explicit `--tires-level`,
`--brakes-level`, `--chassis-level` and `--transmission-level` indices. Do not
reinterpret a list's first element as a proven saved upgrade without its producer.
The C test links the module with existing ground/contact/frame/geometry/scale,
suspension/brakes/lateral/friction/tires, transmission/distribution/engine and
Gekko-math modules, with `-fno-fast-math -ffp-contract=off` and the host sanitizers.
It accepts the canonical profile path as its only argument.

No shared controller, main loop, SDK build, hardware setting or published binary
is changed by this source checkpoint.
