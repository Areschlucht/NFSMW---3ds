# Original GameCube driving research checkpoint

These tools recover and verify small original systems. They do not yet implement
Most Wanted handling, and the portable helpers are deliberately not wired into
the provisional 3DS driving controller.

## Source identity and verification

* Speed.dol SHA256:
  `33c5eae699f871beac059b6932475cad5e9f610bb2b2298e046d043757b94166`
* ATTRIBUTES.BIN (694976 bytes) SHA256:
  `5b69c44ffcfc7013a3f24900b33617002b1f68f2484a9108daa5bfe5d72ad20c`

Original files are supplied separately and are not embedded in these helpers.
`vehicle_dol.py` maps every address from actual DOL section headers. Initialized
small data does not use the code section's file/address delta.

Run synthetic validation with:

```
python -m unittest discover -s tests -p 'test_mw_physics*.py' -v
```

Reproduce original-code comparisons (requires Unicorn 2.1.4 and a host C compiler):

```
python tools/vehicle_verify_original.py --dol /local/Speed.dol --attributes /local/ATTRIBUTES.BIN
```

The reference helper pins the executable checksum, restricts executed addresses
and writes, and caps instructions and runtime. The original engine function uses
six Gekko paired-single callee-save spills/reloads unsupported by Unicorn. Only
those six instructions, each checked against its exact original word, are
replaced with NOP in emulator memory. Arithmetic and return-value instructions
execute unchanged. This validates the named scalar stages, not whole-game physics
or hardware timing. Host compilation uses no fast-math and explicit `fmaf`;
3DS execution still needs separate compiler/target validation.

## Attribute database

`vehicle_attributes.py` parses the observed mixed-endian VPAK variant: the outer
header is little-endian, the embedded BIN/VLT streams are big-endian. It validates
all 10706 relocations into copies of the streams, 56 class definitions and 2301
collections. It preserves raw bytes and file/stream offsets for every field and
records which ancestor supplied inherited optional values. Externally supplied
names are hash candidates, not proof of units.

GC class definitions end in a big-endian 32-bit required-searchable-field count.
GC optional entries store a byte flag and zero padding. Treating these fields as
PC legacy halfwords silently corrupts interpretation. Typed-array header, stride,
alignment, count/capacity and required-layout span are validated. Unsupported
structs remain raw bytes; strict scalar decoding may reject noncanonical values
in unrelated audio classes, so this is not a claim to decode every class type.

Schema layout was cross-checked against the MIT-licensed NFSTools/VaultLib commit
`c1c9e94044ef0eae9ebc43c5a2b3a70ef5369d86`; this is an independent parser,
including the observed GC ABI differences. Candidate field labels were checked
against NFSTools/VaultBoy commit
`0fcf66cf3de9bb66379c9c2546c4d8e4e0f5ee9f`; actual hash identity is verified by
executing this game's original Attrib hash wrapper at `0x801956E8`.
The unrelated runtime bStringHash is a different algorithm.

## Verified scalar systems

`mw_physics_engine_curve_raw` mirrors `0x802240AC..0x80224264`:

1. Read engine IDLE (+92), MAX_RPM (+84), RED_LINE (+88), and TORQUE typed array.
2. Clamp requested RPM to [IDLE, RED_LINE].
3. Place array samples uniformly across [IDLE, MAX_RPM], preserving each original
   single-precision subtraction, multiplication and division boundary.
4. Truncate the sample coordinate, then interpolate with one fused single FMA.
5. Return zero for array count <=1. Invalid metadata is rejected safely instead
   of reproducing original out-of-range memory access.

The distinction between MAX_RPM and RED_LINE matters: BMWM3GTRE46 has IDLE800,
MAX_RPM9500, RED_LINE8500, so its last stored torque sample is not returned at
redline. Its raw value is approximately372.988525. Do not label torque Newton
metres: another original accessor multiplies torque*RPM by approximately1/5252,
suggesting a horsepower convention, but actual applied-force conversion is still
being traced.

`mw_physics_tire_diameter_m` mirrors `0x80224268..0x802242BC`. The original
selector is nonzero for front AxlePair index0 and zero for rear index1. It uses
SECTION_WIDTH×0.001×2×0.01×ASPECT_RATIO, then a fused add of RIM_SIZE×0.0254.
This proves millimetres, percent and inches for these dimensions and metres for
the result. A visual-wheel consumer multiplies by0.5 for radius.

The verification script compares exact IEEE754 float32 bits across all80 valid
original engine collections (2640 cases), original tire collections with four
selector values each, and262 hash inputs of different lengths. Output records
source hashes, patched instruction words, test counts and a compact BMW trace.

## Important distinctions before integration

* BMWM3GTRE46 is distinct from the road-car `bmwm3gtr` collection.
* BMW mass1300, wheelbase2.73, physical FRONT_AXLE1.43 and physical track widths
  1.608/1.603 come from original attributes; their force/frame consumers still
  require proof before replacing current handling.
* BMW visual ecar TireOffsets are X1.6/-1.13, Y±.91, Z0, fourth component.33.
  Materials research confirms the fourth component is used as rolling radius.
  Physical255/40R19 specs instead produce approximately.3433m radius. Visual
  mounts, art pivot, CG, physical axle locations and wheel mesh origin must not
  be conflated.
* All47 simsurface collections are decoded with provenance. The collision agent
  independently joins17 of20 encountered material keys directly to those rows.
  Friction field names do not establish tire-force formulas or surface units.

## Remaining work toward faithful driving

Recover engine torque application and units; gearbox/clutch/differential dynamics;
original throttle, braking and handbrake behavior; tire lateral/longitudinal force
and slip curves; load transfer, suspension and contact resolution; steering and
assist systems; fixed-step timing and reset state. The original EngineRacer
factory/constructor are0x802545B0/0x802545F4, and SuspensionRacer are
0x80246D00/0x80246DB4. No full1:1 handling claim is justified until these systems
have original reference traces and driving comparisons.

## Brake, handbrake and drivetrain checkpoint

The additional helpers remain isolated from the provisional controller. Run
`vehicle_verify_brakes.py` and `vehicle_verify_drivetrain.py` with the same
`--dol` and `--attributes` paths as the earlier verifier.

### Wheel brake and lock stages

Original suspension constructor80246DB4 places a tires instance at+0xA0 and
brakes instance at+0xB4. Original wheel constructor80245F18 stores references to
these instances at wheel+0x100/+0x104 and axle index `(wheel_index >>1)` at+0x10C.
Thus wheel0/1 use front AxlePair slot0;2/3 use rear slot1.

The original lock stage802462D0..802463AC reads:

* Wheel+0xC4: radius; +0xC8: normal-brake input; +0xCC: handbrake input;
  +0xD0: angular wheel speed; +0x134: lock state.
* Brakes layout+8: BRAKES AxlePair; +16: EBRAKE; +0: BRAKE_LOCK AxlePair.
* Exact torque conversion1.3558000326 from803FB454; initialized tuning globals
  normal_scale4 at8041F350, handbrake_scale10 at8041F354, lock_scale1.2 at8041F358,
  angular_resistance100 at8041F35C. These writable calibration globals are explicit
  portable parameters; initialized values are not claimed to cover every game
  mode or later runtime tuning state.

Preserving original float boundaries, it compares
`lock_scale * fmaf(normal_input, BRAKE_LOCK[axle]*BRAKES[axle]*conversion*normal_scale,
handbrake_input*EBRAKE*conversion*handbrake_scale)` against
`fmaf(contact_force_argument, radius, abs(angular_speed)*angular_resistance)`.
When the former is strictly greater, it sets the lock state and zeros angular
speed. Otherwise it clears the lock. The contact-force argument is retained as a
raw named input until the complete contact-force path is reconstructed.

Stage8024644C calls this lock test with zero contact-force argument in the
no-contact/free-spin branch. Unlocked wheels accumulate normal and handbrake
moments opposing rotation, combine them with drive torque, divide by initialized
inertia10 at8041F364 and integrate angular speed with a fused float multiply-add.
Stage802463B0 prevents a step crossing through zero relative to its prior
forward/stopped/reverse direction state and applies±1e-6 direction thresholds.
The surrounding solver resets torque accumulators separately: this helper must
not be treated as a standalone whole-vehicle brake update.

Racer input routing80249BF4..80249C40 explicitly writes the handbrake channel only
to wheel2/3, writing zero to0/1. Further conditions can increase that input;
normal braking has additional routing/assist conditions. These broader branches
are documented from instructions but have not yet been independently reproduced.

`vehicle_verify_brakes.py` checks11480 lock/free-spin cases across all82 original
brake collections, both axles, rotation signs/zero, pedal combinations and
contact-force/delta-time arguments. It checks float bits and integer states.
The free-spin emulator omits only its four verified paired-single ABI spill/load
instructions; all actual arithmetic and state transitions execute unmodified.

### Rear grip assist and handbrake

Original80249004 is called only for rear wheels by80249C50..80249C74. Its return
is blended with a time-dependent state and multiplied into a wheel grip factor.
The helper `mw_physics_rear_grip_assist_raw` retains five original floating ABI
arguments because all input-state axes/units are not proven. The caller supplies:

* f1 = input-state+0x9C multiplied by2π;
* f2 = routed handbrake input;
* f3 = input-state+0xBC;
* f4 = original tires.YAW_CONTROL curve result from802490B0;
* f5 = input-state+0x24.

It starts with `1+abs(f5)`. If handbrake>0.5 and abs(f1)<20×degree-to-radian
constant, it returns this base, omitting an assist addition. Otherwise it adds
`min(abs(f1)*f4*((f3-0)/(30-0)),0.35)` with the exact original operation order.
There is no lower clamp on the interpolation in this function. These initialized
assist coefficients come from8041F5E0..8041F5F8. Original-PPC comparison covers1028
cases, including the handbrake branch and thresholds. This is evidence that
handbrake affects a particular rear assist, not a license to replace the complete
rear tire model with a guessed constant friction multiplier.

### Requested engine RPM

Original802555CC uses both physical tire diameters to obtain an average radius,
then derives a requested RPM from speed magnitude, GEAR_RATIO[slot], FINAL_GEAR,
IDLE and RED_LINE. It includes an idle offset and range factor:

```
omega = abs(speed_mps) / average_radius
idle_w = IDLE * original_RPM_to_rad_s
redline_w = RED_LINE * original_RPM_to_rad_s
request = (idle_w + omega*(FINAL_GEAR*ratio)*(redline_w-idle_w)/redline_w)
          * original_rad_s_to_RPM
```

It clamps the result to[IDLE,RED_LINE], preserving each original float rounding
boundary. Neutral-slot output can be800.000061 rather than exactly800 because of
the original conversions; a generic wheel-RPM equation would lose this detail.
Invalid gear-index fallback uses original memory helpers and is deliberately
rejected in portable code. This is a requested-RPM stage, not the complete clutch,
actual RPM evolution or automatic-shift algorithm.

`vehicle_verify_drivetrain.py` finds77 complete engine/tires/transmission matching
collections and compares4808 original-PPC results across every valid gear slot,
positive/negative/zero speeds and varying dimensions. It omits only eight checked
paired-single ABI spill/load words from this function in emulator memory.

Engine method8025546C separately calls the raw torque curve, multiplies by the
original1.3558 constant, a `(1+state+0x9C)` term and conditionally state+0x100 based
on another interface's return. The downstream torque split, wheel-force
application, clutch state and mode semantics remain unproven. The observed
horsepower conversion plus1.3558 supports a pound-foot-to-newton-metre convention;
the helper still returns raw torque until the entire applied-force chain closes.

### Contact surface identity

Contact/wheel base constructor8021C31C creates an Attrib instance at wheel+0x9C,
so its required-layout pointer is wheel+0xA4. It obtains the initial collection
handle from global80496A68. Original init80278E78 selects simsurface classFB111FEF,
collection90A4D09A (original name`null`) and assigns the global instance80496A64;
its collection handle is at+4. Contact update8021C4F0 changes that instance from
the incoming contact collection and reads STICK(+244) into its persistence timer.

Later80246B14 multiplies the wheel's lateral force by this layout's
LATERAL_GRIP(+240), and longitudinal force by DRIVE_GRIP(+236). This closes the
schema-to-consumer link for these two fields. Other surface friction fields,
contact normals and collision response have their own consumers still to prove.
The collision specialist independently verifies the material-key joins and
original triangle selector; rendering and collision frames must be translated
before any driving integration.

The nine synthetic/host regression tests require no original game files and cover
parser corruption, source provenance, mapping/hash behavior and compact original
scalar reference points. None of these checkpoints establishes full1:1 driving.

## Contacted-wheel curve, saturation and reference checkpoint

`mw_physics_lateral_curve_raw` recovers original802460B0 using seven six-point
curves from8041F288..8041F330. These are original executable tuning data, not a
chosen substitute tire formula. Their BSS curve objects are not initialized just
by loading a DOL. The reference now executes startup80265868..802659A0 with the
proven live-ins r25=6 (set802653C0) and f30=0 (loaded8026578C). It checks all seven
constructed objects: count6, minimum0, maximum10, coordinate scale0.5 and pointers
to the original sample arrays. It also initializes the adjacent1mph threshold.

Original80193BB4 returns an angle in turns, using signed16-bit lookup output times
1/65536; interpreting it as radians is wrong. The lateral-force stage multiplies
absolute slip-angle turns by360 and0.5, so the seven curve families correspond to
0,2,4,6,8,10,12 degrees and plateau above the last family. Each curve's load
coordinate is `force_argument *0.001 *0.8`. Original interpolation within a curve
uses `fmaf(1-fraction, low, fraction*high)`, while interpolation between angle
families uses `fmaf(fraction, high-low, low)`. These have different float-rounding
behavior and are preserved separately. Output is multiplied by2.5 and by
`tires.GRIP_SCALE[axle] * (wheel+0x128 scale *1000)` in the original order.
`vehicle_verify_lateral.py` checks11352 exact float-bit cases across all86 tire
collections, both axles, load/angle boundaries and wheel scales, in addition to
checking every original table value and initialized object.

The combined-force limit at80246A38..80246B10 is now independently recovered as
`mw_physics_friction_limit_given_magnitude`. Its force cap is normal_load times
STATIC_GRIP[axle], wheel grip factor(+0xEC), combined factor(+0x12C), and the
preceding speed-dependent factor. When force magnitude exceeds this cap and0.001,
it scales both force components by cap/magnitude. It also scales the local slip
budget(+0x124) by the square of that ratio, then adjusts the traction factor if
absolute longitudinal slip speed exceeds the resulting budget. An alternate
branch undoes a prior torque-direction boost with the original2/3 multiplier.
The caller supplies the magnitude explicitly: the test does not pretend host
`hypot` equals Gekko's reciprocal-estimate-based square root. The independent
original instruction slice and portable C match8192 float-bit cases.

### Full original contact reference, with explicit fidelity bounds

`vehicle_contact_traces.py` executes original80246580 with actual BMW tire/brake
layouts, original initialized curve objects, and original surface layouts. It
records640 synthetic contact cases across four surfaces, two axles, brake/handbrake
inputs, zero/positive/reverse longitudinal arguments and lateral arguments. A
further12-frame fixed-velocity sequence isolates handbrake lock/release. These are
original instructions acting on explicitly constructed wheel states, not captures
of a complete original-game vehicle. The per-frame sequence resets only documented
accumulators/parameters and is not claimed to reproduce all suspension/drivetrain
state producers.

The full reference correctly preserves nested scalar callee-save values. Simply
NOPing Gekko PSQ saves/restores is safe for the earlier isolated return-only leaves,
but is insufficient when the contacted-wheel routine calls the lateral-curve
function and then needs its own f29..f31 values. The full reference therefore
emulates the scalar PS0 float spill/reload lane at each checked ABI instruction;
PS1 is not consumed by this selected scalar call graph. Unexpected paired
arithmetic is rejected. Arithmetic instructions otherwise execute unchanged.

Original square-root helper80193420 uses `frsqrte`, a reciprocal estimate with
hardware-specific lookup behavior, then original single-precision refinement.
Generic PPC emulation alone does not establish Gekko estimate parity. The offline
adapter `vehicle_dolphin_frsqrte.py` checks and compiles separately supplied
Dolphin FloatUtils sources at commit
`86d554802d7560acf12b5c5a2b3acb344069b5ce`, using its actual estimate implementation.
The external files are GPL-2.0-or-later; none of their source or lookup data is
copied into the 3DS runtime. This is a pinned emulator reference model, not a
physical GameCube measurement. Source hashes are emitted into the trace report.
The original DOL entry also establishes r2=80516DC0 and r13=80506DC0 for original
math-library small-data accesses; the reference uses these actual values.

The full contact routine proves longitudinal slip speed is
`wheel_angular_speed * radius - longitudinal_velocity_argument`. It computes this
before a later lock decision, so the first locked step can differ from subsequent
steps. In the documented fixed20m/s, lateral1, load4000, rear-wheel synthetic case,
handbrake zeros wheel speed; the next locked step produces approximately−400
lateral and−7990 longitudinal force, compared with approximately−6667 lateral in
the prior rolling case. This demonstrates the original locked-slip path. It does
not establish whole-car yaw, drift trajectory, release recovery, or faithful
input/suspension coupling.

Original per-wheel inputs/vehicle frames, complete torque split, differential,
clutch/RPM state evolution and automatic shifting remain unfinished. The scalar
curve and saturation modules are useful verified components; the full contact
reference provides a stronger target for the next implementation. No live
controller replacement or1:1 driving claim is made at this checkpoint.

## Recovered suspension/contact pipeline (2026-11-03 checkpoint)

The portable contacted-wheel solver, scale producers, native frame/projection,
physical mount geometry, spring/damper/travel law and antiroll now exist as
separate `mw_physics_*` modules. The earlier statement above that the portable
contact implementation was unfinished describes the prior checkpoint. These
components are deliberately isolated from the live provisional controller.

`mw_physics_ground.[ch]` composes recovered original8024AA28..AECC in native
world coordinates: frame/projection, suspension load, contact or free-spin,
world-force composition, and persistent compression/airborne-time updates.
Its input is an actual wheel query's normal and query-relative scalar,
steered wheel direction, point velocity, body-up, mass, speed and timestep.
The caller supplies the actual current surface parameters and all assists.
This API does not install arbitrary scale1 factors or a new timestep.
The AIRTIME test follows compression rather than the contact decision:
a compressed wheel with normal·bodyUp<=.2 free-spins yet resets airborne time.
Spring contact can have zero normal force; it still executes the contact branch.

Order is material to fidelity. Original RacerUpdate80247A2C prepares all wheels,
runs mechanical stage802455E0, distributes torque with8024A00C using the previous
compression/lock/slip, then8024A568 computes steering, routes brake/handbrake
inputs, queries and updates wheels. `mw_physics_ground_antiroll` snapshots all
four prior compressions before wheel updates. Preparation must precede torque
distribution; current-frame brake/input routing follows distribution. The module
requires this orchestration explicitly instead of concealing a different order.

`vehicle_verify_ground.py` compares a persistent stage chain against separately
executed original PPC stages. It passed1024wheel steps over both physical BMW
profiles and four original surfaces:640contact,384free,60compressed-but-steep
free-spin,105locked states, with zero mismatches in every tire/brake/suspension
output, force component, compression and airtime. Queries, steering directions
and input/torque producers in this corpus are deliberately synthetic. This is
stronger than unrelated scalar examples but is not an uninterrupted whole-car
trace or a1:1 handling claim. Original power/sine/sqrt callbacks retain numerical
independence; defaultpowf still has the previously reported32force differences
(max0.015625N, no contact/bottomout changes) in4272suspension cases.

Wheel query-point and point-velocity producer8021C750..7D8 is also recovered.
`mw_physics_contact_point_velocity` rotates the physical mount, subtracts the
already-rotated WORLD CG OFFSET for its angular lever, computes WORLD angular
velocity cross lever, adds WORLD linear velocity, and separately adds body
position for the world query point.2048randomized original-slice cases match all
six float bits, including large world positions. Native common state+60 is
WORLD angular velocity; +90 is LOCAL. Body interface4C slot98 is HALF EXTENTS,
whereas interface58 slot80 is actual localCG. Those distinct interfaces must
not be confused.

The exporter now requires an explicit pvehicle profile, resolves actual tires,
brakes and chassis RefSpecs, and refuses ambiguous upgrade arrays without an
explicit index. It preserves target class/key, original field provenance and
upgrade index. Generic bmwm3gtre46(4E085FB3) and careerstart(39DAE0F8) are exported
separately. The drivetrain specialist independently proved the actual canonical
M3GTRCAREERSTART preset/spawn selects pvehicle/m3gtre46careerstart, not the generic
model-named profile; its report lives in port-research/drivetrain. Contact export
alone does not claim to establish the original selection or performance-upgrade
producer.

Validation:13host regressions passed; strict pinned GCC16.1 ARMv6K compilation
passed ground,suspension,contact_frame,contact_geometry. Object text sizes564,
1056,2000,236bytes respectively, excluding linked scalar/math dependencies.
Reports: portable-ground-verification.json, portable-contact-frame-verification.json,
portable-suspension-verification.json in port-research/driving-engine.

Remaining whole-car gates: original steering and full brake/input-assist routing;
mechanical/aero stage802455E0; source VehicleParams mass/inertia/halfextent binding;
material timer persistence; original force application/moment and bottomout chassis
correction; complete chassis integration and original scheduler/tick cadence.
Drivetrain owns shaft/clutch/shift/differential components and their sequencing.
The prototype's120Hz substeps are not original-timestep evidence. No live controller,
main/build, overclock/cache settings or published files were changed here.

The force application-point/moment substage8024AF4C..AFD0 is now also portable:
`mw_physics_contact_force_moment`. It adjusts local mountY by compression minus
converted ride height, transforms to a WORLD point, subtracts WORLD CG OFFSET
then body WORLD position, and crosses that lever with world force. The subtraction
order preserves original float cancellation at large world positions; substituting
an algebraically simplified local lever changes results.2048original-slice cases
match all six application-point/moment float bits. This closes that arithmetic
substage of the gate list above, while total chassis force accumulation, bottomout
position correction and integration remain separate. Reference stages include an
explicit hook stop at each selected end address so cached Unicorn translation
blocks cannot run into a neighboring separately tested slice.
Final frame object including force-moment helper is2352bytes text on ARMv6K.
Host golden regressions now include the original large-world point/moment bits
and compressed-steep versus zero-compression airtime behavior. The scalar/ground
regression binary also passes AddressSanitizer and UndefinedBehaviorSanitizer.
