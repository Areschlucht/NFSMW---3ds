# Original player steering, wheel tuning, burnout and drifting

This module recovers original player steering and the complete scalar
`SuspensionRacer::TuneWheelParams` arithmetic. Original debug ELF symbols are
available from the independently verified executable whose nine initialized
sections match Speed.dol byte for byte. Complete vehicle behavior still depends
on actual runtime input producers, four-wheel forces and rigid-body integration.

## Complete player steering numerical path

`mw_player_steering_step` implements802484F8..80248A34, including the helper
802486EC and rate helper80248984. Its state carries original angle124,
previous-input138, gain-history134 and both actual rolling time-window buffers.
Constructors802473FC..80247448 select0.55seconds×60Hz and0.15seconds×60Hz;
80209674 rounds their capacities to33 and9. Reset80248098..802480D8 establishes
zero angles/input and gain-history45. The native API preserves those choices.

The exact initialized source uniform curves are recovered from constructor
80265A24..80265BC0 and the original arrays. BSS records are80489F78 (raw input),
80489FC8/80489FDC (speed gains),80489FF0 (smoothed steering gain),8048A004
(speed-dependent throttle factor),8048A018 (input-rate factor) and8048A02C
(smoothed steering rate factor). A separate four-pair curve80489F6C supplies
the original fade interpolation. No invented steering response curve is used.

The controller first derives source gain from actual signed forward speed,
throttle/brake/handbrake, prior averaged input, optional effect value and fade.
**Wheel indices2 and3 are the rear wheels.** Their118 slip-angle turns, multiplied
by360, provide corresponding signed slip floors; they are not front wheel angles
or arbitrary yaw-rate gains. If the slip-floor branch does not apply, held input
can preserve the previous gain. The output is clamped to45degrees and multiplied
by the actual tires.STEERING scalar.

Matching DWARF1 identifies ISteeringWheel::SteeringType:0=kGamePad,
1=kWheelSpeedSensitive,2=kWheelSpeedInsensitive (.debug offset25913174).
The API preserves those original values. Mode0 applies the original
raw-input curve and time-averaged rate limiter; mode1 selects its actual distinct
speed curve and bypasses that limiter; mode2 uses source45-degree gain and also
bypasses it. All modes update the original input-history window. Optional100
blend operates after the stored angle, so returned turns and stored pre-blend
degrees are intentionally different states. All float32 boundaries and fused
operations retain the original order.

`time` is the caller-supplied original game-clock float returned by802782FC;
the implementation does not pretend frame count or accumulated prototype dt is
that producer. Default calibration1.45 at8041F368 is the initialized source value;
arbitrary later runtime modifications of that writable global are not claimed.

## Four-wheel scalar input-routing prefix

`mw_player_route_wheels` implements80249910..80249D80 transactionally on the four
existing `MwPhysicsGroundWheel` records. The original history1B8 moves at20 per
second toward a0.5 floor while handbrake>=0.5, and at1 persecond toward1 when
released. These are the actual initialized calibration values, not newly chosen
drift tuning. State110 attenuates the resulting history.

The prefix retains:

- Actual front/rear normal-brake routing, including effect8 bias and the low-speed
  throttle+brake branch selected by original E4+70 state.
- Rear-only handbrake, including the original extra0.5 branch below80 signed MPH
  and above the source angular threshold. It deliberately permits values>1.
- Original rear-grip assist80249004, source tires.YAW_CONTROL producer output,
  optional controller flag2A and explicit original mode1 override.
- Front lateral grip assist, source effect4 axis scales, D0/D4 grip products and
  the actual per-wheel disable mask. It preserves source side effects and order.
- Maximum **positive** longitudinal-slip wheel selection for the later traction
  phase. This is not an absolute-slip maximum.

Common9C is the local velocity slip angle in turns: zero for local forward
speed below1, otherwise original quantized angle(local lateral,local forward).
The API calls it `slip_angle_9c`. Common94 is local angular velocity Y, common24
is body matrix[9], and commonA0/A4/A8 is `RigidBody::GetInertiaTensor`; sourceA4
is therefore inertiaY. These are runtime providers, not visual wheel pivots.

## Complete wheel tuning and source assists

`mw_player_input_route` executes the complete802498B4 arithmetic in source order:
YAW_CONTROL getter, scalar wheel prefix, burnout update/reset, C4 bit0 grip
multiplier, and `DoDrifting` yaw state/torque. The prefix consumes the old drift
ramp before the later yaw update. It never substitutes the later state early.

`mw_player_yaw_control` follows802490B0 and actual tires.YAW_CONTROL samples.
With an engine interface it interpolates at abs(speed)/GetMaxSpeed, clamped1;
nonpositive maximum speed gives0. Without that interface it uses the first
sample. An absent attribute's unknown fallback provider is rejected explicitly.
Nonmonotonic source curves, including GTI's final0.1 entry, are preserved.

The source debug name for80248B5C is `SuspensionRacer::Burnout::Update`.
It enters below20 signed MPH when maximum positive longitudinal slip exceeds0.5,
maintains source stage/timer/quiet-time/scale, and resets during excessive slip
angle above5 MPH. The caller resets it when the original mode/throttle conditions
do not select it. C4 bit0 subsequently multiplies all four grips by0.25.

`DoDrifting`802492A0 preserves all four source states and ramp evolution,
source slip/steer/throttle tests, initialized pair and uniform curves, rear wheel
combined factors, and original output order. When applicable, it outputs the
controller A4 command first, then an additive world torque aligned with bodyUp
and scaled by actual inertiaY. The caller must apply these commands through the
original runtime providers. Torque is not a guessed yaw-velocity impulse.

## Comparison and integration limits

`tools/vehicle_player_input_reference.py` executes unchanged bounded original
steering instructions and real curve/rolling-average helpers. External virtual
mode/effect interfaces and time are explicitly supplied. It compares **5760
stateful steering steps** across three modes, four synthetic scales plus six
actual source tire profiles, forward/reverse speed, effects, fade, rear slip
and variable timesteps. Output turns and every field/value/time in both rolling
buffers are compared at float-bit precision.

Additional comparisons cover2048 scalar-prefix cases,768 original YAW_CONTROL
getter cases across six actual ATTR profiles, and2048 complete wheel-tuning
cases. Complete cases compare all wheel writes, burnout and drift states,
controller commands and world torques. No original callsite or arithmetic is
rewritten to force a chosen output. Private executable/attributes stay SHA-pinned.

ASan/UBSan host tests cover the actual first-step fixture,1200 persistent
updates, mode2, rear handbrake, wheel masks, source burnout and torque outputs,
nonmonotonic YAW_CONTROL and transactional rejection. No SDK/main/controller
edits are made here.

**Integration limits:** game-clock/input/interface providers and dynamic writable
calibration changes remain external; body force accumulation and fixed-step
integration belong to the original mechanical/rigid-body runtime. This module
alone is not evidence that the playable handling is1:1. Gekko FPSCR,
exceptional/subnormal semantics and arbitrary fused ties retain the shared
emulator-model caveats.

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps \
python tools/vehicle_player_input_reference.py \
 --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
 --attributes /workspace/attachments/857a1856-1b3b-4be1-8a91-42f437324e6f/ATTRIBUTES.BIN \
 --output /workspace/port-research/player-input/verification.json

cc -std=c11 -Wall -Wextra -Werror -fno-fast-math -ffp-contract=off \
 -fsanitize=address,undefined -no-pie -Iinclude \
 tests/test_vehicle_player_input.c source_bmw/mw_original_player_input.c \
 source_bmw/mw_physics_grip.c -lm -o /tmp/mw-player-input-test
/tmp/mw-player-input-test
```

## Matching debug types and runtime providers

DWARF1 Chassis::State0x33D717E proves C4=flags, C8=driver_style,
CA=driver_class, CC=gear, CE=blown_tires, D0=nos_boost and D4=shift_boost.
Chassis::Flags0x33D762B gives IS_STAGING=1 and IS_DESTROYED=2;
DriverStyle gives STYLE_RACING=0 and STYLE_DRAG=1. Hence the burnout gear
comparison is the source gear2, not a fabricated driving-mode enum.

SuspensionRacer0x33E0C3C proves100=mGameBreaker; Steering0x33E135B proves
1AC=CollisionTimer,1B0=WallNoseTurn,1B4=WallSideTurn,1B8=YawControl.
Reset80247F9C..8024810C clears gamebreaker, collision timer, wall terms,
drift and burnout state; sets YawControl/history and burnout traction to1.
Generated transmission::_LayoutStruct0x3213693 proves70=TORQUE_SPLIT;
sourceE4 is SuspensionRacer's mTranyInfo layout pointer. The route input's
source_e4_70 is therefore the actual transmission attribute, never a speed gain.

VehicleBehavior mVehicle4C is IVehicle. Original PVehicle IVehicle vtable
803F8728 slot1A4 resolves80215B88 GetTunings. Optional effect0/4/8 are
Physics::Tunings.Value[STEERING/HANDLING/BRAKES]. Tunings::Default8017CFB0
clears all seven values (28bytes). GetTunings may return null or the selected
customization tuning profile; caller supplies both presence and actual values.

Behavior mIOwner38 is ISimable. Its slot4C resolves PhysicsObject::GetPlayer;
LocalPlayer IPlayer slot84 is GetSteeringDevice, slot34 GetSettings, and slotA4
is **ChargeGameBreaker**80289384. PlayerSettings2A is Handling, not an unnamed
controller flag. `settings_present` explicitly preserves the original null
GetSettings branch; IPlayer presence alone does not justify a2.5 assist boost.
The existing generic output spelling controller_a4 is kept stable for consumers,
but its proved command adds the argument to LocalPlayer::mGameBreakerCharge8C
and clamps0..1. It does not modify body velocity or steering.

## Source trigonometry and complete steering directions

`mw_player_source_sincos` uses original sinf8031DCBC/cosf8031DAD0 kernels,
source float32 constants and original argument reduction. Moderate reduction
8031E868 includes source cancellation refinements. Large reduction8031EC3C
uses the actual198 eight-bit digits of2/pi, split-pi/2 table and source fused
accumulation loops. The float reduction algorithm is adapted from Sun fdlibm's
float kernel with its permission notice preserved in the C implementation.
No host sinf/cosf approximation replaces the original. The float callback forms
serve source wheel and engine paths. The verified domain is abs(x)<=400,
covering all original wheel angles and five-second story sabotage (max377rad).
Larger/nonfinite inputs reject/return NaN; arbitrary astronomical angles are
not claimed bit exact.

`mw_player_steer_directions` closes original ComputeAckerman80244C2C through
its real sinf/cosf calls and paired-single body rotation801935A4. Output0/1
follows original F28/F29 angles; output2/3 uses body forward. The apparent
DoSteering return reversal does not reverse actual wheel assignment:
DoSteering swaps into caller stack8(F29)/stack18(F28), then DoWheelForces
8024A7FC..A844 first loads stack18 and8024A874..A8AC writes wheel0's
stack38 direction. The next block loads stack8 into wheel1's stack48.
Thus the new helper already returns the actual wheel0/1 direction order.

## Collision steering and exact tick order

`mw_player_collision_event` implements all8024812C..802484F8 arithmetic on
real Collision::Info input and explicit actual interface results. Type1/2 uses
the owning object's impulse, respecting its immobile flag, and increases the
collision timer by the source10..40 impulse mapping clamped0..1. Type3 records
the actual Sim::GetTime timestamp. Type2 wall cases preserve source normalY,
closing-velocity and objectA-velocity tests, contact position relative to body
position, forward/right dot products, body dimensionZ and signed vehicle speed.
These are original fields, never a guessed proximity-to-wall detector.

`mw_player_wall_steering` implements80248E48..80249004, including the early
return when nose correction opposes the requested steering and the reverse-gear
side condition. The outputs are ordered **SetAngularVelocityWorld** commands,
not forces/torques. Both may occur; the second uses the original common angular
snapshot and supersedes the first. Original RigidBody slotD4 resolves802342B0,
which directly copies angular velocity without wake/status effects.

The source timer decay occurs at tick start80247AC4..AE8 after common state is
built. DoWheelForces8024A5F8 calls human steering, ComputeAckerman directions,
then DoWallSteer; only afterwards does8024A604 call TuneWheelParams. Although
DoWallSteer changes body angular velocity, the already built common world/local
angular snapshot remains unchanged for that tick's remaining wheel/drift maths.
End-of-tick80247D40..D50 clears nose/side wall terms after wheel state updates,
before the general chassis suffix. `mw_player_collision_begin/end` expose those
actual distinct boundaries; clearing wall terms early would drop real effects.

Original PPC comparisons cover2048 full collision events,2048 full wall-steering
calls and256 exact tick-boundary slices, comparing every state float and ordered
setter argument by bits. Source body collision detection/resolution and actual
event emission remain the separate rigid-body/world collision integration task.
