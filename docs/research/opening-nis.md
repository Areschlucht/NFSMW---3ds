# Original opening cinematic camera tracks

The six named original cameras are decoded from the supplied USA
GLOBAL/INGAMEB_VM_NGC bundle. They are not generated orbit views. The separate
compressed ELF actor-animation bank is decoded by the companion actor sampler;
camera playback alone is not full original NIS playback.

## Concrete private asset and source

`/workspace/port-research/opening-nis/native-camera-v2/opening-cameras.nis`
is19,192 bytes, SHA256
`09d631a057764c37244e8c16fedf7dbb11fd62b3060c41658fb7bd28f22d3a59`.
The app may install it as `opening-nis.nni`; its format magic is NIS1/version1.
Do not use the earlier private v1 file: a track-record padding mismatch was caught
and corrected before native decoder validation. Neither file was published.

The pinned original bank is657,088 bytes, SHA256
`4164d8be4fd215d682b803202055abc10ffcb28a56942645e6554b3e7dac57fc`.
Original camera containers are0x8003B200..203; each camera child is0x3B210.
The case-sensitive source name hash identifies these six scenes:

| Scene | Tracks | Actual track duration | Source keys |
| --- | ---: | ---: | ---: |
| GenericStart | 2 | 6s each | 4+2 |
| IntroNisDD | 1 | 43s | 48 |
| IntroNis04 | 1 | 9.6669998169s | 5 |
| IntroNis05 | 1 | 6s | 3 |
| IntroNis10 | 1 | 15s | 10 |
| EndingNis03 | 1 | 27.7000007629s | 14 |

Track choice, time producers, pauses, scene transitions and animation/director
completion are not inferred from this list or the camera duration alone.

## Actual source record and numerical consumers

Scene header is8 bytes: name hash and track count. Track header is40 bytes;
duration is+10 hex, signed key count+14, name+17. Each key is132 bytes:

- Normalized key time+10; source tangent weights+14/+18.
- Eye endpoints+1C/+28, target endpoints+34/+40.
- Roll source scalars+4C/+50.
- Focal/lens source scalars+54/+58, **not direct FOV degrees**.
- Eye/target coordinate modes are bytes+4/+5.

Original getters800798A0/80079918 establish eye/target offsets. The exporter runs
unchanged original8007E550 for all172 endpoint tangent calls. Neighbor continuity
uses raw source flags/modes, endpoint values and0.001 source tolerances, preserving
cut discontinuities. Original interval ratios and per-end weights control the
Hermite derivatives. No uniformly smoothed camera path is substituted.

Original8007A328 converts focal scalars using15.9600009918 and the actual original
atan lookup8005D1F0, then doubles its fixed-turn result.8007A3C0 converts derivatives
using the original0.01 increment and100 multiplier. Endpoints and derivatives are
stored as actual source turn values. The native sampler preserves those units;
projection aspect policy remains the renderer's responsibility. Roll is stored in
turns: consumer8007CBB0 calls roll getter8007C28C, multiplies by65536.0
(original constant803D2AF4), truncates and masks to16 bits, then passes that angle
to view builder8007A534. Its rotation helper8010B1D0 multiplies the integer angle
by original constant803DED90=0.0000958738019107841 (approximately2pi/65536),
establishing the turn unit independently of the key values. A renderer can use
`roll_source * 2pi` radians, with source fixed-turn quantization when required.

## Mode bindings and world coordinates

Original8007C95C..8007CA54 proves:

- Mode1 leaves sourceXYZ world points unchanged.
- Mode0 multiplies by the controller reference frame at stack+68.
- Mode2 adds the current reference position.
- Mode3 multiplies by the NIS scene transform returned by virtual+68/+6C.

The mode0 frame comes from the TrackCamera constructor8007A720 r5. Its actual
caller8007087C supplies parent+2C8, a94-byte frame created8007A24C and populated
8007A0D4 from the subject transform at parent+2D4.80070B14 obtains that subject's
virtual+E8/+EC transform reference. Frame+10 copies the4x4 matrix, and frame
position+0 copies matrix translation+30. The camera update subsequently smooths
reference orientation/position through fields+10C/+11C only on the car-space-lag
branch. Debug ELF symbols now prove the subject is CDActionIce's actual IPlayer
car. The supplied opening tracks use direct/captured frames, not that smoothing
branch; [native director providers](opening-nis-director.md) implement their
actual branches, scene-root binding, clock and track selection.

Mode3 additionally calls8007D480 in the endpoint getters before tangent creation.
It consults scene-relative world placement and ground-height providers. The
offline export explicitly supplies an identity ground/scene provider for
local-basis tangents; this is not a recorded original scene/terrain trace.

`mw_nis_camera_sample` samples that raw-basis exported curve and then invokes the
explicit resolver. `mw_nis_camera_sample_provided` invokes a separate `prepare`
callback on raw local endpoints and neighboring points, rebuilds original tangent
weights at runtime, samples the curve, then calls `resolve`. A mode3 terrain
provider must supply the original local-Z adjustment at the preparation stage;
the scene matrix belongs in the post-interpolation resolver. Both outputs are
original sourceXYZ world points; the root performs its usual viewer mapping
`(X,Z,-Y)`. Missing/refused providers fail without publishing a new camera sample.
No callback is silently assumed to be a valid original scene matrix.

## Native format and validation

NIS1 header128 bytes, CRC covers bytes16 onward, followed by64-byte scene records,
64-byte track records and212-byte keys. Keys retain all132 original source bytes,
two8-float original tangent outputs and four mapped FOV turn scalars. Original
bank and DOL hashes are retained at header48/80. The decoder validates counts,
exact nonoverlapping layouts, ASCII terminators, unique scenes, ordered finite
times, source modes, every consumed finite scalar and sensible FOV turn range.
The borrowed data stays immutable; playback allocates nothing and performs no IO.

Tests pass under strict C11 warnings and ASan/UBSan:6scenes,7tracks,86keys,
847 source samples, runtime identity-provider tangent reconstruction bit matches,
end clamping, provider refusal, NaN/negative time and malformed/recomputed-CRC
structure rejection. The independent tool compares3,440 scalar camera output
components against unchanged original coefficient/value functions800791B8 and
80079200 with bit-identical binary32 outputs. These are component comparisons,
not a claim that the entire original director, actor placement or game camera ran.
Source flags bCubicEye/bCubicLook additionally select original GetEye/GetDutch
linear branches where authored; those paths are included in the3,440 comparisons.

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps \
python tools/opening_nis_export.py \
 --global /workspace/port-research/opening-nis/raw/0e1075eb.bin \
 --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
 --output /workspace/port-research/opening-nis/native-camera-v2 --verify-host
```

No shared main/render/build file, game input, SDK application build or commit was
changed by this camera subtask. Source media and converted camera data stay private.

The separate [actor decoder](nis-actor-bindings.md) now supplies95 original
translation/quaternion/scale curves from seven banks in the private769,904-byte
`native-actors-v1/opening-nis-actors.nna` asset. Its integer and fractional decoder
comparisons pass; director clock mapping, actor identity bindings and scene root
transforms still require integration evidence before full NIS playback is claimed.
