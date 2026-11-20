# Original vehicle rigid body

`mw_original_rigid_body.c` recovers the original USA GameCube rigid-body
integrator and world-force-at-world-point application. This closes the actual
quaternion, velocity, angular velocity and inertia arithmetic; it does not by
itself establish complete original handling, scheduling, contacts or AI.

## Source and verification

The only supported executable is SHA-256
`33c5eae699f871beac059b6932475cad5e9f610bb2b2298e046d043757b94166`.
The matching private original DEBUG ELF has SHA-256
`6ee16d55d92ad1b337a9b655989c32b2976f95e7c64e148cf83f482c613f79f7`.
Its initialized sections match the DOL, so original symbols and DWARF 1 fields
confirm these interpretations. `tools/mw_debug_info.py` reads selected types
without bundling the ELF or its debug payload. The reference tool checks the DOL hash, executes unchanged original instruction
bytes, constrains writable state/stack memory, and compares all mapped state at
float-bit precision. Original bytes are read from the user's private DOL and
are not included in this repository.

Run:

```
PYTHONPATH=tools:/workspace/toolchains/python-deps python tools/vehicle_rigid_body_reference.py --dol /path/to/Speed.dol --dolphin-reference /path/to/pinned-dolphin-reference --output /tmp/rigid-body.json --cases 1024
cc -std=c11 -O2 -Wall -Wextra -Werror -fno-fast-math -ffp-contract=off -fsanitize=address,undefined -Iinclude tests/test_vehicle_rigid_body.c source_bmw/mw_original_rigid_body.c source_bmw/mw_gekko_math.c -lm -o /tmp/test-rigid-body
/tmp/test-rigid-body
```

The verified run contains **7,168 original calls with zero float-bit
mismatches**: 1,024 each of integration, force-at-point, torque, combined wrench,
vertical correction, physical parameter production and complete orientation
initialization. C tests pass under ASan/UBSan. The bounded tests use explicit synthetic caller states; they are not full-game
telemetry or an original saved-game replay. The functional Gekko paired-single
model excludes FPSCR exception/subnormal modes and rare binary64 FMA ties.
The wake flag clear is executed exactly, but the original external event
registry dispatch is observed at 80234360 rather than executed. The optional
`wake_event` output makes that caller boundary visible.

## Actual state and force receiver

Constructor 80232794 installs vtable 804012D0 for the body interface at owner+4C.
Its slot 130/134 adjusts back by -4C and calls 80235220. The owner+88 handle
points to the physical state; owner+100 stores local CG and owner+A0 stores
the previous world inverse inertia matrix.

| Physical state offset | Meaning |
| --- | --- |
| 00 | Quaternion XYZW |
| 10 | Position XYZ |
| 20 | Linear velocity XYZ |
| 2C | Mass |
| 30 | Angular velocity XYZ |
| 3C | Inverse mass |
| 40 | Diagonal inertia XYZ |
| 50 | Accumulated force XYZ |
| 5D | State: STATE_AWAKE 0, STATE_SLEEPING 1, STATE_NOMODEL 2 |
| 60 | Accumulated torque XYZ |
| 70 | Orientation, row-major 4x4 |
| 1C/1E | Current/previous 16-bit status flags |

All inputs/outputs use the original native Y-up body basis. Viewer coordinates
must be converted at the rendering boundary. `add_force` computes the world CG
from local CG and orientation, subtracts it from the world application point,
and accumulates lever-cross-force plus linear force. STATE_NOMODEL bodies reject force;
others wake and set flag 40. No dt belongs in these force records.

## Integration 802352E4

The recovered update preserves original operation order and explicit fused
instructions. Linear velocity receives force times dt times inverse mass.
Position uses this updated velocity **before** component clamps to +/-300.
Torque is multiplied by dt and by the **previous** world inverse inertia matrix
in place; it then updates angular velocity, clamped to +/-30. Nonzero angular
velocity advances and normalizes the XYZW quaternion, then rebuilds orientation.
The updated world inverse inertia is R-transpose times inverse diagonal inertia
times R. Diagonal values only invert when greater than source epsilon 1e-6.
Finally position receives old transformed CG minus new transformed CG. Sleeping
or STATE_NOMODEL state zeros both velocities and returns.

Force is retained by this function. Torque has become the angular impulse, so
callers must perform the original phase reset before accumulating another
interval. Nonfinite or unsupported native inputs fail without mutating state.

## Source mass, physical bounds and inertia

The actual PVehicle creation routine is 80212DE0. Owner+188 is the compound
collision root; signed shorts at +10/+12/+14 are physical halfextents. The
80212E50..80212EE4 slice converts them to float and multiplies source constant
0.0010000000474974513. It applies neither mesh normalization nor the generic
prop path's minimum extent clamp.

Owner+E0 is the generated pvehicle required layout: MASS at +38, TENSOR_SCALE
at +00. Original 80212F1C..80212F44 loads those exact providers and calls
80278BC0, which doubles each halfextent, squares it, sums the two perpendicular
axes, multiplies by float 1/12, then mass, then each TENSOR_SCALE component.
The intermediate order matters. The different generic object producer around
80219BA0 includes another factor of two and must not be used for vehicles.

`mw_original_rigid_body_parameters` implements these producers. The reference
executes both the original short-conversion slice and complete original inertia
helper. The caller supplies source pvehicle MASS/TENSOR_SCALE plus collision
root shorts; visual model bounds are not an acceptable substitute.

For `m3gtre46careerstart`, ATTRIBUTES.BIN SHA-256
`5b69c44ffcfc7013a3f24900b33617002b1f68f2484a9108daa5bfe5d72ad20c`:
MASS is 1300 at source file offset 212232 and TENSOR_SCALE is [1,2,1,0] at
212176. Their source offset difference is exactly the required-layout 0x38.
The BMW compound root has raw halfextents [938,621,2284]; the private
`map-collision/body-response/bmw-compound-shape.json` records its archive and
geometry provenance. Other vehicle profiles require their own physical roots.

The body constructor accepts explicit creation position, velocity, angular
velocity, orientation, mass, inertia and bounds. It computes inverse mass from
source mass and copies local CG from rigidbodyspecs required layout +90.
The source racers specification has local CG [0,0,0,0] and gravity
-9.812800407409668. This does not justify borrowing racer values for every
object/specification in the game.

## Tick phases and source scheduler

The matching ELF names 80234A44 `RigidBody::OnBeginFrame`, 802352E4
`RigidBody::DoIntegration`, 8023487C `RigidBody::OnEndFrame`, and 80231F14
`RigidBody::Primitive::Prepare`. Before integration the begin-frame method sets
status flag 400 and prepares each collision primitive in owner+120. This is
collision geometry preparation, not an extra force or constraint solver.
After integration it clears force and torque. Active bodies copy flags to
previous flags and, unless flag 2 is set, seed force.y = GRAVITY * source mass
for the **next** accumulation interval. The first interval also needs gravity.

The original scheduling and behavior sequence is now identified:

1. Startup 801FB5D8 loads DOL803F501C, **0.01666666753590107**, into
   `Scheduler::Init` 801ED864. The Scheduler constructor stores `fTimeStep` +20.
2. `SimSystem` constructor 802736A0 copies that into `mScheduleStep` +18 and
   `mTimeStep` +1C. `UpdateFrame` 80276A94 multiplies schedule step by current
   simulation speed +24; 80276A6C dispatches the resulting timestep.
3. Source `system/default` task order places **SimStart at priority 0** and
   **Physics at priority 3**. The SimSystem constructor registers SimStart at
   80273914 (handle+44). `SimTask::Link` 802733E0 sorts ascending priority.
4. SimStart dispatch at 80275D28 calls global `RigidBody::Update` 80239134.
   Its first traversal invokes every body's OnBeginFrame (802391A4..BC), then
   collision/grid work, then its final traversal invokes OnEndFrame
   (80239634..4C).
5. `PhysicsObject` constructor registers its Physics task at 8021661C with
   source rate **1.0**, fixed-frame mode 0 and zero initial delay. Therefore
   active vehicles execute each base 1/60 frame at normal simulation speed.
6. `PhysicsObject::OnTask` 802177D0 traverses the active behavior list +A0 and
   invokes each unpaused OnTaskSimulate. `Behavior` constructor 8021CAE8 scans
   source BEHAVIOR_ORDER hash104E9D16 and records its index as priority +44.
   `PhysicsObject::Behaviors::Add` 80215EA8 sorts that priority. For these source
   racer profiles, input precedes engine, which precedes suspension.

Thus original body integration/collision/end-frame processing precedes the
current interval's engine and wheel force generation. Those generated forces
remain in the accumulator for the **next** frame. Moving integration behind
wheel generation changes this original phase relationship.

Rate 0.1 observed on other objects is not a 0.1-second physical timestep.
`SimTask::Run` 8027351C accumulates its `mRate`, dispatches when it reaches 1,
and divides incoming dt by rate for TASK_FRAME_FIXED (0). TASK_FRAME_VARIABLE
(1) instead uses its accumulated time bank. These enum and member names are
confirmed by matching DWARF. State/simulation speed, pausing and reduced-rate
non-player actors remain separate scheduling inputs.

OnEndFrame updates the collider, clears flag 4, queries world collisions if
needed, calls `DoDrag` 80234B28, evaluates `ShouldSleep`, then clears flag 400.
Source racers DRAG and DRAG_ANGULAR vectors are all zero and natural angular
damping is zero; this does not justify adding generic damping. Native contacts,
world response, sleep predicates and geometry preparation still have to be
composed for complete body behavior. `RBVehicle::ShouldSleep` at 8023C278 adds
vehicle/suspension predicates before base `RigidBody::ShouldSleep` 80238E1C.

## Orientation initialization and body commands

`mw_original_rigid_body_set_orientation` recovers the **complete** original
802337F0 setter: matrix-to-quaternion conversion 80193814 with its actual
trace/largest-diagonal branches, unchanged supplied orientation, and world
inverse inertia. It uses the already recovered `mw_gekko_sqrt_newton1` stage
for original80193420's reciprocal-square-root estimate refinement; ordinary
sqrtf is not substituted. The offline matrix tests compare with a separate
checksum-pinned Dolphin estimate reference, not the native implementation.
The constructor's auxiliary unmapped matrix-translation vector is not exposed
as a new gameplay state. The caller must still supply the actual spawn matrix.

| Concrete RBVehicle body slot | Original target | Native endpoint |
| --- | --- | --- |
| 100/104 | 8026724C ModifyYPos | raise_position: Y += amount, no wake |
| 110/114 | 80235030 Resolve | add_wrench: force and **torque**, not a point |
| 120/124 | 802350A8 ResolveTorque | add_torque: no dt/inertia scaling yet |
| 130/134 | 80235220 ResolveForce | add_force: force and world application point |

These targets match both base body vtable804012D0 and actual RBVehicle body
vtable80400D48. Wrench/torque calls preserve the original wake/nomodel behavior.
Common chassis state A0/A4/A8 is also closed: the owner+58 interface vtable
80400BE8 E8/EC slot points to `RigidBody::GetInertiaTensor` 80266E54, returning
physical state+40. Consequently common A4 is **inertia Y**; late-yaw torque uses
it to convert angular acceleration, rather than a visual model dimension.

The optional parameter export arguments `--attributes`, `--body-bundle` and
`--parameter-output` reproduce six source profile records including physical
root extents, MASS, TENSOR_SCALE, rigidbodyspecs binding, CG, gravity, collision
padding, drag, damping and sleep threshold provenance. Private evidence lives
under `port-research/rigid-body/`; all source binaries remain outside Git.
