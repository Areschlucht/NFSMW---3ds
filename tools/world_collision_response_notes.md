# Original static car-body collision checkpoint

The portable solver in `mw_body_collision_response.[ch]` implements the bounded
original USA executable core at **0x80083C74..0x80084690**. It consumes an actual
contact and explicit body state. It does not yet supply the original swept
compound-shape contact generator, frame dispatch/order, penetration correction,
or the BMW VehicleParams mass/tensor binding.

## Interfaces and runtime data

`mw_body_collision_response(state, contact, out)` performs no allocation, file
I/O, or source-data lookup. It preserves inputs and leaves output untouched on
invalid input. The original static-world caller supplies 16 passes. The explicit
pass limit here is 1..64; zero passes are rejected. Vectors must share the actual
original body/world basis; do not silently feed viewer axes. The matrix is the
original row-major 4x4 orientation representation; the vector helper uses its
upper-left 3x3. Inertia inputs are the original diagonal, before reciprocal and
WORLD_MOMENT_SCALE multiplication. Mass, local CG, and half-extents are distinct.

The response includes updated linear/angular velocity, initial normal/tangent
velocity, accumulated normal impulse, first friction impulse, first friction
branch, and number of approaching iterations. The first pass observes contact
statistics but applies no velocity correction. The solver normalizes the input
normal with the original 0x80193420 estimate/Newton helper. Contact momentum is
`mass * (linearVelocity + angularVelocity cross lever)`. The original friction
stage receives this momentum. Subsequent passes scale normal/tangent impulses
by `iteration / passCount`, apply reciprocal mass and rotated inverse inertia,
and stop after separating or exhausting passes. State+0x10C is retained as the
explicit `extra_normal_accumulation` parameter; the constructor initializes it
to zero. Its broader physical label remains unproven.

Compile together with `mw_body_collision.c` and `mw_gekko_math.c`, link libm,
and disable implicit FP contraction (`-ffp-contract=off`); explicit `fmaf` calls
preserve identified fused operations. No emulator, original executable bytes,
or Dolphin source is required by runtime code.

## Compound shape source

`world_collision_response_shapes.py` strictly decodes source container 0x8003B900,
entry 0x3B901. `mw_body_collision_shapes.[ch]` reads the borrowed, unfixed,
little-endian package without allocation. Runtime-facing primitives preserve
original quaternion/center/half-extents, radius, material and unknown fields.
Original 0x8023446C dispatch produces **two boxes and six spheres** for BMW's
static-world child list. Its separate 16-vertex convex mesh follows another
member interface; do not silently substitute the container bounds for that mesh.

Actual source key is original case-sensitive VLT hash `BMWM3GTRE46` = 0xCAE3E635.
The root record's half-extents (.938, .621, 2.284) are a decoded shape property;
they have not been proven to be the BMW VehicleParams half-extents getter.
`MW_BODY_SHAPE_ROOT_PATH_REQUIRED` means the original root dispatch must run;
it does not authorize replacing it with a guessed fallback box.

Private user-supplied source and generated asset paths are kept outside the
repository under `/workspace/port-research/map-collision/body-response/`.
The 784-byte `bmwm3gtre46-collision.bnd` comes from supplied decoded
GLOBAL-GLOBALB_VM_NGC.BUN (SHA256
da02353de70dea3a8a51d6231e4efde15ab8c5c72eed6119a49bc9dad20b770b).

## Evidence

The original executable SHA256 is
33c5eae699f871beac059b6932475cad5e9f610bb2b2298e046d043757b94166.
`world_collision_response_reference.py` executes its mapped original instructions
under a bounded PPC/paired-single model with a pinned external Gekko estimate
oracle. The model is host-only and rejects escape from allowed original ranges.

Saved private reports:

- `bound-decoder-differential.json`: 83 packages, 1,034 bounds, 94 meshes,
  1,443 vertices; no endian-fixup or decoded-vector discrepancies.
- `shape-c-differential.json`: 1,034 decoded bounds and 2,068 primitive producer
  comparisons (unpadded and explicitly padded); zero float-bit/type/flag errors.
- `friction-response-differential.json`: 3,666 original friction threshold/branch
  cases. Current portable default uses the independently implemented original
  estimate/Newton helper; earlier ordinary-sqrt observations are historical.
- `response-c-differential.json`: 1,000 original core cases / 18,000 float
  components, zero float-bit, hit, or branch errors. Inputs cover different
  masses/inertias, rotations, CGs, contact offsets, angular velocities, friction,
  moment scales, pass counts, inertia thresholds, zero/nonunit normals, and
  explicit state+0x10C. These are explicit synthetic producer inputs and do not
  establish the BMW physical parameter binding.

Public synthetic tests run with:
`python -m unittest discover -s tests -p 'test_world_collision*.py'`
(18 tests at this checkpoint). New body-core and shape tests also pass host
AddressSanitizer/UndefinedBehaviorSanitizer. Target hardware execution remains
an integration check. Floating-point evidence is against the bounded executable
model, not a console trace; FPSCR exceptions/control, PS subnormal modes, and
rare exact fused ties beyond the model remain outside the verified boundary.

## Remaining contact production gate

The original body step 0x80238654 transforms child primitives using 0x80231F60,
then calls 0x802F338C against cached **40-byte** walls (not raw CARP 32-byte rows).
That function constructs a zero-thickness wall box and dispatches collision
geometry via 0x8008A630. Its exact 3x3 function table at 0x803D3F50 chooses
0x80089658 for box/box, 0x80089D50 for sphere/box, 0x8008A604 for box/sphere,
and 0x8008A4B8 for sphere/sphere. Contact orientation rejection and the full
callback packet still need executable differential recovery before runtime
body response can safely be connected to original world geometry. Original
callback 0x80238420 applies positive penetration along the packet normal before
calling the velocity response. No guessed wall impulse has been enabled.
