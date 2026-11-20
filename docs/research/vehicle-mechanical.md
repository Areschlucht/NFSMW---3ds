# Original ordered drag and downforce stage

`mw_original_vehicle_mechanical.[ch]` ports the complete finite-input force stage
at802455E0..80245960. It returns at most two separate world-force/world-point
records in original order: drag, then downforce. It does not mutate wheel state,
sum these records, advance a body, or turn forces directly into positional speed.
No live controller/main loop or application build is changed by this subtask.

## Proven input and output boundaries

The original obtains its rigid-body interface through owner+38, getter entry
A8/AC, then submits force/point via returned-body vtable130/134 at80245748 and
80245930. The bounded reference supplies only that external getter and captures
these actual submissions. The sibling rigid-body recovery mapped the concrete
force receiver to80235220; body accumulation/integration remains a separate stage.

Common state produced by80244F8C supplies:

- Body matrix at0, with translation at30 and forward basis at20.
- World velocity at50, speed length atBC and throttle at4C.
- Contact fraction at6C: the original contact count multiplied by.25.
- **Local** center of gravity at70.

The two mechanical arguments f3/f4 are physical front/rear mount Z, taken by
80247CF8..7D00 from wheel+74. They are not traction/grip factors. The incoming
f1/f2 are the original caller's drag/downforce scales, not an inferred timestep.
This stage does not multiply force by elapsed seconds. All matrices/vectors use
the original native Y-up coordinate system; viewer/art bounds are not substitutes.

## Original behavior preserved

Positive drag scale enables a drag submission even if the resulting force is
zero. The drag coefficient is chassis required-layout+70. Throttle adjusts its
multiplier with mutable global8041F280 (initialized2). Optional effect blob+10
adds one quarter of that value as an additional multiplier. With at least half
the wheels contacting, local CG height additionally shifts by global8041F284
(initialized-.1) times off-throttle amount. The original local-to-world transform
then supplies the force application point.

Positive downforce scale enables the aero branch. Below half contact, body-up Y
is clamped against zero; otherwise its multiplier is exactly1. Direction uses
world velocity divided by speed above the original1e-4 threshold, otherwise the
body forward basis. Its nonnegative forward dot is raised to mutable exponent
8041F278 (initialized.5), then **clamped upward** to8041F27C (initialized.4).
This is a minimum, not a maximum.

Original accessor80223ADC computes `2 * speed * AERO_COEFFICIENT * 1000`, preserving
single-precision operation order. Exactly zero contact additionally multiplies
the result by.8. The same optional effect multiplier applies. A positive result
submits the body-rotated local downward force. Any nonzero contact moves local
application Z between the physical axles according to chassis AERO_CG percent
(layout+5C); airborne application retains the source local CG Z.

Every multiply/add/transform rounding boundary follows the source single
instructions and explicit FMA order. Output failure leaves the caller's previous
result unchanged. Invalid/nonfinite inputs or nonfinite intermediate results are
rejected; original exception/control behavior for invalid physics state is not
claimed.

## Source profiles and power dependency

The tool emits six156-byte private MMP1 profiles next to the existing NDP files:
`/workspace/port-research/driving-runtime/{m3gtre46careerstart,bmwm3gtre46,cobaltss,gti,is300,punto}.mmp`.
These bind explicit pvehicle/chassis keys, actual DRAG_COEFFICIENT,
AERO_COEFFICIENT/AERO_CG fields and the four initialized mutable globals.
Actual runtime global/effect producers must still supply changes when applicable;
the source profiles do not invent those changes or saved upgrade selection.

MMP1 is header128 plus seven little-endian float32 values. Header fields identify
version1, exact156-byte length, CRC of16..end, physical/chassis keys, offset128,
count7 and zero reserved bytes. Original ATTRIBUTES/DOL digests occupy64/96.
The strict reader copies scalars and accepts no borrowed mutable file buffer.

The power call is **powf**, not binary64 pow. Native default math now uses the
verified positive special branches in `mw_original_power.c`; see vehicle-power.md.
An explicit callback can supply another recovered original branch. Unsupported
native exponents reject instead of silently calling approximate general libm.

## Validation and limits

The unchanged original mechanical function, actual vector helpers and original
power library were compared against native C on3072 cases across six source
profiles. Both source-power callback and native-default paths have zero observed
force/point float-bit mismatches. Cases cover orthogonal/tilted matrices, throttle,
contact0/.25/.5/.75/1, disabled/negative scales, effects, forward/reverse/zero
velocity, low speed, and varied mutable globals. The previous binary64-libm
choice differs in18 force calls; those counterexamples remain in the private
report as regression evidence rather than being hidden.

ASan/UBSan tests cover ordered drag/downforce, off-throttle height/force changes,
optional effects, airborne/inverted branches, overflow rollback, all156 single
byte profile corruptions and recomputed-CRC structural/source/NaN corruptions.
The source getter/receiver adapters are explicit. Existing paired-single
reference limitations (exact FMA ties, FPSCR, complete denormal policy) remain.
This closes the mechanical gate; it is not a complete original handling claim.
Player assists, rigid-body accumulation/integration, contact scheduling, complete
engine branches and actual whole-car trajectory comparisons remain separate work.

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps \
python tools/vehicle_mechanical_reference.py \
 --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
 --attributes /workspace/attachments/857a1856-1b3b-4be1-8a91-42f437324e6f/ATTRIBUTES.BIN \
 --output /workspace/port-research/driving-runtime/mechanical-verification.json
```

Host tests link `mw_original_vehicle_mechanical.c`, `mw_original_power.c` and
`-lm` with strict C11 warnings, `-fno-fast-math -ffp-contract=off` and sanitizers.
The optional test argument is the canonical m3gtre46careerstart.mmp path.
