# Native motion bridge to the source engine for audio

The current playable chassis still uses its documented native planar controller.
`mw_native_engine_audio` is a deliberately native provider that lets that controller
supply the independently recovered EngineRacer core for sound. It does not invent
an RPM-from-speed curve and does not claim to reproduce original whole-car physics.

The application loads the selected car's actual stock NVR into a stable
`MwVehicleRuntimeParams`, initializes the adapter with that profile, the current
NWA rig and exact art normalization, then supplies before/after **admitted** native
movement and wheel-animation observations. Model/profile selection must be exact;
using BMW parameters for an unsupported car is not a fallback implemented here.

The adapter maps legacy side-first NWA rigs into original front-left/front-right/
rear-left/rear-right order from real front/side data. It measures wheel angular
motion, unwraps modulo rotations against the native renderer's actual accepted
position change, and respects actual rear handbrake locks. Physical wheel radius
comes from the original source tyre dimensions. Contact-point velocity comes from
the accepted visual-wheel position change, projected along the native steered
wheel direction. Signed slip uses the recovered expression
`fma(wheelOmega,physicalRadius,-longitudinalVelocity)`.

All four current visual tyre-bottom points require an admitted world query.
The callback must return actual NWC ground height and upward normal or a genuine
miss; missing sections/query errors disable the sample. A native wrapper may
query from above to satisfy the original strictly-below ground detector, then
return the actual triangle-derived height/normal. The adapter does no world IO,
allocation, collision-section admission or flat-ground fallback.

The original suspension scalar law consumes the resulting relative plane and
actual source axle parameters. Its **query point is explicitly a native visual
proxy**, not the original rigid-body suspension mount. Positive admitted contact
uses a native traction-admitted value1; a genuine miss/unsupported normal has no
loaded traction. These are not the original material/contact/constraint solver.
Previous contact/compression/velocity values are fed before the following engine
tick, preserving the engine-before-suspension data dependency within this adapter.
Source-produced wheel angular corrections are intentionally not written back into
the planar chassis or its animation.

The audio world's owner/input policy is also explicit: normal automatic mode,
no optional boost/tuning/unlimited interface, and the current native signed
throttle convention. A reverse request uses the recovered gear-commit numerical
operation, while **reverse input authorization is native policy**. A request is
not published before an actual source tick. These values are not presented as a
recovered original IPlayer/settings/gameplay implementation.

The bounded source engine driver then runs the actual recovered clutch, torque,
induction, NOS, RPM smoothing and automatic-gear logic. Audio gets its real
reported-RPM field, applied throttle and gear. Original GIN granular synthesis,
its original calibration and bank selection remain a separate sound consumer;
applied throttle is not claimed to reproduce every original audio load signal.
Pausing means no admitted observations. Unknown profiles or invalid queries mute
the provider instead of generating a fake tone or an invented RPM calibration.

A strict native C11 adapter compile passes warnings-as-errors and `-pedantic`.
The real-private-world ASan/UBSan integration test uses actual root BMW NFM/NWA,
NRD, exploration activation and NWC packages. It runs180 admitted source60Hz engine
ticks through real native motion, with720 primary actual wheel-ground queries,
plus injected missing-section and recovery/reverse checks. The run reported
730 actual NWC hits of731 total queries, source RPM842.30..8375.00, and successful
legacy-rig mapping, handbrake and transaction checks. The host test admits the
whole collision package set only for its test cache; production keeps its existing
bounded section admission. This is source-engine/native-chassis audio integration
evidence, not original driving trajectory parity or a listening test.

```
python3 tests/test_native_engine_audio.py \
  /workspace/port-research/roster-physics/native-v1/bmwm3gtre46.nvr \
  dist/career-integration-install/3ds/nfsmw-rockport
```

## Expanded source profiles

`tools/build_roster_physics.py` exports actual stock source component selections,
physical body roots and matching BND packages for all concrete source pvehicles
that fit the existing NVR schema. No guessed bounds or reused BMW scalars are
introduced. Private outputs are under
`/workspace/port-research/roster-physics/native-v1`.

The current corpus exports63 profiles,48 marked source PlayerUsable (including
challenge variants);37 other concrete profiles retain their exact rejection
reason. Two PlayerUsable challenge trucks lack the observed optional induction
field and are explicitly rejected. All38 currently converted browser models have
exact stock base-profile matches. `model_defaults` is populated only when the
source profile name exactly equals the actual MODEL string in lowercase;
challenge/career variants require explicit selection, not first-match guessing.

Every exported NVR passed the native reader and engine-driver sanitizer contract:
75,600 primary continuation comparisons across63 profiles, plus per-profile
failure/sabotage/scheduler cases. Report `native-engine-audit.json` preserves each
result. These compare composition with the separately source-compared engine
core, not new whole-car comparisons against original PPC. Source parameters,
BND packages, report data and original assets remain private; only authored
export/runtime/test code and these findings belong in Git.
