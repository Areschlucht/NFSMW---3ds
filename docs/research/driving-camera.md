# Original driving camera numerical recovery

`mw_drive_camera` now contains the original ordinary driving target and pre-world
placement stages. The live app's old spring camera has not yet been replaced by
a complete original camera. World queries, noise and camera construction are
still explicit integration gates.

The matching private debug ELF identifies the original functions and members;
it is not recovered C++ source and is not included in the repository.

## Verified routines and stages

`tools/drive_camera_reference.py` executes the unchanged uploaded USA executable
under the bounded offline PPC oracle and compares native numerical state. It
checks 14,602 cases/lookup entries in the current deterministic corpus:

| Consumer | Original address | Exact cases |
| --- | --- | ---: |
| CameraAnchor::Update | 800685D8 | 160 |
| CubicCameraMover::SetForward | 80072FCC | 2,560 |
| CubicCameraMover::MakeSpace | 80073218 | 640 |
| Ordinary CubicCameraMover::SetDesired | 8007381C | 400 |
| bSin whole-turn polynomial | 8005CE20 | 3,856 |
| Update acceleration/impact/channel stage | 80073FE8..80074378 | 512 |
| Update pre-world placement stage | 80074444..80074B34 | 512 |
| Update half-angle/lens conversion | 80074B38..80074B78 consumers | 4,681 |
| Mathematical reconstruction of atan lookup | original 80415FE4 data | 257 |
| eCreateLookAtMatrix (including degenerate inputs) | 8010AF38 | 1,024 |

The oracle uses explicit paired-single float32 operations and the pinned Dolphin
reciprocal-estimate model. It patches no original instructions. This is evidence
against an offline hardware model, not a console trace. NaN, FPSCR corner cases
and exact Gekko fused-arithmetic ties are outside that model's claim. The ordinary
target stage excludes source debug custom/highlight camera overrides; USA
HighliteMode literally returns false. Placement tests include arbitrary yaw/pitch
spaces and world translations, reverse views, gear and impact timers.

The Update tests are bounded numerical stages, not the entire Update function.
Their comparison state includes cubic values/coefficients/targets, the five-entry
acceleration ring and sum/average, impact magnitudes/deadlines, placement vectors
and source gear-change timestamp. The lens test separately invokes the real
bSin, bCos and integer atan routines. The private JSON evidence is written to
`/workspace/port-research/drive-camera/verified.json`.

## Source order and coordinate contract

The camera frame is source X forward, Y lateral, Z up. A matrix contains three
basis rows followed by translation in row 3. It is not the renderer's coordinate
frame and must not use vehicle body yaw as an additional camera spring.

At each active camera update:

1. Resolve the actual car CameraAnchor, POV/profile and source tuning sample.
   `mw_drive_camera_anchor_update` computes acceleration from the change in speed,
   projects along the car's forward basis, and rejects apparent teleport motion
   from acceleration. Its fourth original input vector is not consumed.
2. Call `mw_drive_camera_channels` before setting the new desired targets. It
   decrements the source ignore timer, runs the nonlinear acceleration curve
   (domain -30..30), updates the five-sample average, records source impacts,
   installs source durations, and steps **previous** cubic targets. Original
   order is up, FOV, eye, look, forward. Forward duration includes the actual
   Anchor collision damping and drift fields, not hand-tuned constants.
3. Call `mw_drive_camera_desired` with actual grounded/under-vehicle/NOS status
   and the actual DutchAroundCar result. It updates grounding timestamps, source
   velocity-direction lag, local acceleration offsets, speed hugging and NOS FOV.
   It returns MakeSpace and sets targets for the next interpolation step.
4. Call `mw_drive_camera_placement`. It applies source reverse view, collision
   kicks, gear-change longitudinal kick and under-vehicle vertical lift before
   transforming eye/look into world space. Up retains the original convention:
   outside uses the interpolated first two up components plus literal Z=1;
   inside uses the car's up basis.
5. `mw_drive_camera_fov_turns` applies the actual integer half-angle, original
   sine/cosine ratio and integer atan interpolation. Initialize its mathematical
   lookup once with `mw_drive_camera_lens_table`, outside the draw loop.
6. `mw_drive_camera_look_at` creates the actual source view matrix, including
   source normalization and degenerate-vector behavior. Still required:
   handheld/chopper/terrain noise, world topology/vehicle clearance, then the
   actual camera commit.

SetDesired occurs after channel stepping. Reversing those two calls changes
camera lag even when every individual cubic routine is correct. Original vector
and scalar table interpolators also use different fused-operation order; the
native code preserves both. Point transformation preserves the source paired
multiply/FMA order instead of reusing the different vector-rotation helper.

`world_timer` is the original 4,000 Hz quarter-millisecond counter. Elapsed time
uses signed wrapping subtraction followed by multiplication by
0.0002500000118743628f. It is independent of physics SimClock and should not be
replaced by a count of rendered frames.

`mw_drive_camera_source_data` returns the actual USA dynamic-initializer speed
hug samples and NOS angle. It does not substitute platform-specific tuning. The
257-entry atan lookup is recreated from round(atan(i/256)*65536/(2*pi)); every
entry equals the original table. No original lookup bytes are bundled.

## Remaining fidelity gates

- Port the original constructor/reset transitions, including conversion from an
  existing camera to initial cubic state. Zero-initialize-and-snap is a possible
  adapter but is not a verified substitute for that constructor.
- Recover actual IsUnderVehicle and DutchAroundCar query producers. A supplied
  zero vector or false status is not proof that those queries are unnecessary.
- Port the full original noise/commit chain after the verified look-at matrix.
- Recover MinGapTopology/MinGapCars and their source world/vehicle query domains,
  accumulated clearance state and temporal order. Existing ground-only eye
  clearance is not equivalent.
- Connect actual CameraAnchor provider flags, dimensions, top speed, tunings and
  original WorldTimer cadence to live gameplay; verify whole frame sequences.

These gates remain before a 1:1 camera claim or replacing the shipping camera
with this module as a supposedly complete implementation.
