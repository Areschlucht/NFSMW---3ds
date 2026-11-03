# Original GameCube camera recovery

This work supplies verified numerical camera components. It does not replace the
current provisional `chase_camera.c`, and is not a complete original chase camera.
Root main/build/shaders remain untouched.

## Verified components

`mw_original_camera_profile.[ch]` mirrors profile selection/cache plus ordinary
projection arguments. `mw_original_camera_direction.[ch]` mirrors the initial
velocity/body-direction target stage and links the independent `mw_gekko_math.c`.
`mw_original_camera_cubic.[ch]` implements one original 44-byte persistent cubic
interpolation channel, including target, rebuild, optional limits and step order.
`mw_original_camera_tuning.[ch]` preserves the authored sample blend and source
speed-to-tuning parameter; its input data is exported separately from the DOL.
There is no runtime emulator or original executable dependency in these C files.

- Preserved checkpoint: 66 source camera collections, 3,234 exact original-PPC
  profile-cache cases and seven original mode selector results. Not rerun merely
  because the cloud workspace was restored.
- New projection argument path: 315 exact float-bit comparisons against unmodified
  original `801000EC..80100210` and its ordinary full-height getter.
- New direction target: 960 exact float-bit comparisons against original
  `80073028..80073100`, the original scalar normalize/vector helpers and curve
  reader. Only the hardware `frsqrte` estimate is supplied by the existing pinned
  host-only Dolphin reference; original arithmetic and branch code are unchanged.
- New cubic channel: 2,074 exact full-state (44-byte) comparisons against
  original `80208128` and its coefficient/evaluation/limit helpers. The verifier
  models 18 scalar PSQ stack ABI saves/loads; it patches no guest bytes and
  executes no paired arithmetic.
- New authored tuning: 761 exact whole176-byte sample comparisons, including
  unchanged padding, and 510 exact speed-to-parameter comparisons. All14 original
  mode samples are exported with address/file-offset/hash provenance in
  `tuning-verification.json`; source assets are not embedded in runtime C.
- Focused native tests pass strict host compilation and ASan/UBSan. Root also
  compiled profile and direction for ARMv6K with strict pinned SDK flags; their
  text sizes are 908 and 760 bytes. The new cubic and tuning modules await that target check.

Reports and disassembly evidence live in `/workspace/port-research/camera-fidelity`.
Source identity remains Speed.dol SHA256
`33c5eae699f871beac059b6932475cad5e9f610bb2b2298e046d043757b94166` and
ATTRIBUTES SHA256
`5b69c44ffcfc7013a3f24900b33617002b1f68f2484a9108daa5bfe5d72ad20c`.

## Profiles and projection

Original `800687C8` selects ecar camera references:
0 bumper, 1 hood, 2 close, 3 far, 4 superfar, 5 drift and 6 pursuit. BMW resolves
the original close/far collections and its vehicle-specific hood collection.
`camera_recovery_export.py` emits all seven references with inherited field byte
provenance. Unknown modes take a distinct original default branch; they must not
be silently treated as a far-profile lookup.

Two-element camerainfo arrays are selected with **index=(view_state==3)**. They
are not low/high speed samples. The original cache stores ANGLE in whole-turn
uint16 units, LAG divided by positive cameraScale, HEIGHT, LATOFFSET, scaled FOV
in whole-turn units, STIFFNESS and TILTING. Nonpositive cameraScale falls back to1;
the controller constructor initializes it to1. Source FOV values include close78
and far90; those values do not by themselves establish a ready 3DS projection.

Original `801001A4..80100210` converts rawFOV by360/65536 and multiplies a viewport
Y factor before passing it to SDK `80329CC0`. That function writes cot/aspect to
matrix00 and cot to matrix11, proving its FOV argument is vertical at that point.
The ordinary viewport path computes:

```
yFactor=(viewportHeight/fullHeight)*globalFovScale
verticalFov=(rawFov*360/65536)*yFactor
aspect=((viewportWidth*aspectCorrection)/viewportHeight)*globalAspectScale
```

Original aspectCorrection defaults to .8 or .86 on a flag-controlled alternative;
other view classes use another override. Global scale defaults are1. The portable
adapter therefore requires every factor explicitly. Do not blindly carry the GC
anamorphic correction to a400x240 display or assume raw78/90 is horizontal FOV.
Actual runtime viewport/aspect producer semantics remain an integration gate.

## Initial direction target

The actual player-chase mover constructor is `80071FB8`; its update starts at
`8007381C`. Its direction stage `80072FCC` performs more than following vehicle
heading. The verified initial numerical portion:

1. Reflect velocity when its dot with the controller's body-forward basis is
   negative, preserving forward-facing camera behavior during reverse motion.
2. Normalize using the original scalar normalize sequence. Zero-length input has
   the original +X fallback.
3. Read the source startup curve `[(8,0),(13,1)]`, installed by
   `80080F8C..80081004`, using cached controller speed.
4. Blend body forward toward velocity direction with that weight, preserving the
   original operation/FMA ordering. This output is not renormalized at this stage.

Inputs must share the original camera-controller frame. Later timer/vertical
attenuation, continuous three-channel interpolation and orientation construction
are not part of the current direction helper. Feeding this vector directly to
an arbitrary exponential chase camera would not reproduce the complete system.

## Persistent interpolation and scheduler

The cubic helper preserves source normalized-parameter derivatives, original FMA
ordering, optional endpoint derivative/second-derivative limits, and all 44 state
bytes. A target unequal to the current value sets state2. State2 rebuilds the
curve each update when mode is nonzero; mode0 changes it to state1. Reaching
progress exactly1 does not complete state1 until a subsequent step takes progress
above1. This differs from a generic exponential camera smoothing replacement.

The higher chase update `80073E50` takes caller delta in f1, retains it in f28,
and passes it unchanged into five interpolation updates at `80074324..378`.
Those updates run **before** target/orientation construction `8007381C`, called
at `80074440`. The original scheduler/timebase producer remains a separate gate.
No fixed120Hz or60Hz cadence is inferred.

Authored tuning selection uses `clamp(controllerSpeed * 0.014084506779909134,0,1)`
at `80073EF8..80073F24`. These are the mode-specific two0xB0-byte tuning samples,
not the camerainfo two-element view-state arrays. The selected tuning sample is
on the update stack starting+8. Duration assignments `80074278..80074320` are:

| Mover resource | Channels | Tuning sample offset | Additional source terms |
| --- | --- | --- | --- |
| +84 | 1 | +08 | none |
| +88 | 3 | +00 | none on reachable original path |
| +8C | 3 | +04 | none |
| +90 | 3 | +A0, +A4, +A8 | add controller+A4, then controller+A8, in that order |
| +94 | 3 | +0C | none |

The conditional multiplier at `800742E8..80074300` calls `80072988`, which is
literally `li r3,0; blr` in this DOL, so its multiply branch is unreachable here.
Controller+A4/+A8 are not the mover's same-offset flags. Their producers and all
tuning sample fields still require closure before a complete camera API is wired.

## Concrete remaining call graph

- TrackCar wrapper ingests controller pose/velocity through `800685D8`.
- `80071FB8` constructs the actual chase mover and its interpolation resources.
- `8007381C` calls `80072FCC` direction, `80073218` orientation and ultimately
  camera/world collision `80067258`.
- Camera targets use persistent three-channel interpolation state, with setters
  at `8020836C` and cubic coefficient/evaluation helpers at
  `80207EB8`, `80207F00`, `80207F20`, and updater `80208128`.
- Mode-dependent authored tuning consists of two0xB0-byte samples per mode,
  initialized from static original arrays starting80416578 with0x160-byte stride;
  descriptors are constructed at `80081008..800810E8`. The numerical sample blend is now verified against
  original `80071BB8`; semantic field names and complete consumers remain open.
- `cameraScale=1-max(wrapper+54,wrapper+70)*.4` is written at
  `8006D448..8006D464`; the semantic producers of those wrapper states are not yet
  assigned a guessed speed/impact label.
- Camera timestamp logic reads global804800C0. Its writer and relation to physics
  time8049896C remain unresolved. No120Hz or60Hz original-cadence claim is made.

Full chase integration still needs authored-tuning interpretation, interpolation
scheduler/resource orchestration, exact pose/velocity/basis producers, timers, collision, input camera
preference/mode changes and final output matrix. This checkpoint supplies source
components and evidence rather than a guessed full camera implementation.
