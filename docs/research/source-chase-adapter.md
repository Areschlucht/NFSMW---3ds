# Source direction and cubic integration in the chase camera

The new adapter replaces the provisional slip-angle/yaw exponential when source
data is bound. It integrates verified original direction-target, speed-dependent
authored tuning and persistent cubic-channel components. Final eye/target spring
placement, FOV, native vehicle pose and missing original timer/collision behavior
remain the prototype adapter. This is not a complete original chase camera.

## Source assets and identity

`build_source_camera.py` reads the pinned ATTRIBUTES and USA DOL, resolving all
seven original camerainfo references for these actual ecar collections:

| ecar | Original key |
| --- | --- |
| bmwm3gtre46 |4e085fb3|
| cobaltss |5a784095|
| gti |79054b53|
| is300 |5bff2fb0|
| punto |a6ee7a11|

These keys match the visual/model ecar identifiers in the native vehicle catalog.
The opening BMW physical pvehicle m3gtre46careerstart/39dae0f8 is a different
collection identity and is not inserted as an invented alias. Full original
vehicle/controller producer closure remains separate. Unknown car keys fail
binding instead of borrowing BMW settings.

NCP1 camera.ncp is4,792 bytes: a128-byte header, five48-byte sorted car records,
35 original56-byte profile records and14 original176-byte tuning samples.
Source profile values preserve both original view-state entries; the profile
index is(view_state==3), not a speed blend. Tuning samples instead use the
original clamped controller-speed parameter. Original static tuning arrays at
80416578 with0x160-byte mode stride are read directly from the DOL. No source
profile or tuning arrays are embedded into authored C.

The bounded native reader verifies full shape, reserved bytes, car-key order,
name termination, exact profile offsets, all finite fields, original source
digests and CRC before publishing an immutable borrowed view. CRC covers
bytes16..end. Header fields are count@16, records@20, record-stride@24,
profiles@28, tuning@32, profile-stride@36, mode-count@40 and tuning-stride@44;
reserved48..63 are zero. DOL/ATTR digests occupy64..95/96..127.

## Runtime binding and explicit adapter policy

Call mw_chase_asset_open once while keeping its bytes alive, then after each
chase_reset call use chase_bind_source(camera,asset,active_ecar_key,3,0) for the
far/ordinary-view mode. Reset intentionally clears binding, so old callers with
uninitialized camera storage remain safe. Vehicle/mode rebinding is transactional
and preserves the current visible heading; it does not snap during selection.

The source-motion adapter uses:

1. The current native controller's planar world velocity and body-forward basis,
   in one consistent viewer frame; cached speed is its planar magnitude.
2. Original80073028..80073100: reverse-velocity reflection, original normalization,
   and the authored speed8-to13 body/velocity blend.
3. Original tuning interpolation and per-axis direction-channel duration fields
   at sample+A0/A4/A8. Original constructor channel mode1 is preserved.
4. Original cubic updates before assigning the new direction target, followed
   by original three-channel setter semantics. The one-step response delay and
   persistent normalized derivatives are retained.

Current native controller duration biases corresponding to original+A4/+A8 are
explicitly absent/zero. Original post-target timestamp/vertical attenuation is
not guessed. The filtered horizontal direction becomes native chase heading;
the existing eye/target springs and FOV remain unchanged. Bound source profile
cache values are available for future placement/projection integration but are
not falsely presented as already controlling every stage.

Frame delta remains the native caller's seconds; no claim that this recovers the
original scheduler frequency is made. Original speedbreaker/pursuit input states,
camera collision, bank/tilt, full output orientation and reset movie/camera mode
policies remain integration work. Legacy unbound behavior is preserved.

## Verification

`verify_source_chase.py` compares576 complete44-byte channel states and192
direction targets against unmodified original PPC component windows. It uses
actual source tuning with varying delta/speed, steering direction, drift and
reverse. Original target setter8020836C is executed as well as the cubic step;
no original guest instructions are patched. The existing pinned Dolphin
frsqrte estimate and scalar PSQ stack ABI model retain their stated limitations.
This verifies composition for explicit inputs, not full original camera output.

`tests/test_source_chase.c` passes ASan/UBSan for all35 vehicle/mode bindings,
ordinary/special view selection, one-step ordering, settling drift and reverse,
unknown-car rejection, reset safety and malformed-sidecar behavior. The existing
legacy chase-camera test still passes its stationary/yaw/wrap/settling,
30/120Hz and invalid-input checks. SDK/emulator integration belongs to the parent.

Private asset/manifest/verification:
`/workspace/port-research/menu-reference/source-camera-v1/`.

Link mw_chase_source.c and the existing mw_original_camera_direction,
mw_original_camera_cubic, mw_original_camera_tuning, mw_original_camera_profile
and mw_gekko_math modules with the chase camera. Data generation and host
comparison require original private inputs, not additional uploads.
