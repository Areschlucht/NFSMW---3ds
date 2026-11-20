# Original opening NIS director providers

The original debug ELF has the same initialized code/data as the uploaded USA
DOL. Its symbols and DWARF1 field names resolved the camera provider identities;
the runtime uses authored portable C, not the original executable or an emulator.
Original assets remain private.

## Source identities and coordinate frames

`8007059C` is `CDActionIce(CameraAI::Director*, IPlayer*)`; `80070B14` is
`CDActionIce::AquireCar`. Mode0 therefore consumes the actual local player's
car transform through `ICEAnchor`, with original source XYZ and bMatrix4 layout.
Translation lives at matrix indices12..14. Caller must supply the original car
basis, not a viewer-space matrix, arbitrary yaw frame, or Car1 alias assumption.
The selector's `ICEGetPlayerCarTransform` (`8007D69C`) explicitly calls
`IPlayer::ListableSet::First(1)`. DWARF `ePlayerList` identifies1 as PLAYER_LOCAL
(0 ALL,2 REMOTE), closing the local-player selection independently of racer-list
ordering used for NIS actor names.

`8007F478` is `ICE::FindAnimScene`. Its returned interface virtual+68/+6C is
`CAnimScene::GetSceneTransformMatrix` (`800502B4`), not an individual actor.
DWARF fields are `mSceneRotationMatrix+44`, `mSceneTranslationMatrix+84`, and
`mSceneTransformMatrix+C4`. Mode3 applies this scene transform. The previous
camera-only notes used the conservative term actor provider; the actual class
identity now supersedes that description.

`CAnimLocator::GetInitialAnimMatricies` (`8004A4A0`) initializes rotation and
translation. Scene types0/2/3 use the actual NIS origin and rotation
`uint16(heading-0x4000)`. Other scene types use the zero origin and identity
rotation. The original locator also queries world elevation at the chosen
origin before storing translation; the caller supplies that corrected origin to
`mw_nis_director_scene_frame`. World query selection remains the real map query
provider, not a guessed constant. Source rotation uses `eCreateRotationZ`
(`8010B1D0`) and `eSin` (`8010B0FC`); this polynomial has different coefficients
and range folds from the renderer LOD polynomial. The native implementation
preserves its arithmetic order, including the separate cosine phase addition.

## Actual camera dispatch

`mw_nis_director_camera` supports original modes0/1/2/3, preparing elevation
before tangent reconstruction and transforming after interpolation:

- Mode0: source player's current anchor matrix.
- Mode1: unchanged source world XYZ.
- Mode2: add current source anchor translation.
- Mode3: source scene matrix; `ICEManager::FixAnimElevation` prepares local Z.

Source ICEData byte8 is `bIgnoreOrientation`, byte9 is `bCarSpaceLag`.
Byte8 chooses the orientation captured by original SetDesired reset transitions,
with current subject position. Native context retains prior track/key identity
and reproduces original `ICE::KeysShared` end/start tests to capture that frame.
Preserve the director context between samples and clear `has_active_key` when
creating a new controller. Byte9's smoothing-only branch is not used by any of
the seven supplied opening camera tracks: their only nonzero byte9 key also
has byte8 set, taking the fixed-orientation branch first. Unsupported future
smoothing-only records are explicitly refused.

Mode3 source `GetAnimElevationFixup` returns zero when sampled world height is
not positive; otherwise it subtracts the cached scene-origin ground height.
World-query miss falls back to the point's existing source Z. Native ground
callback receives source world XYZ; false means that original query miss.
With source world queries enabled, missing callback is a refusal, not a flat
ground substitution. `scene_ground_height` must come from the actual scene-origin
query using the same miss convention. Original scene-origin/mode3 ground queries
remain caller-owned map queries; scalar elevation arithmetic is source-derived.
The native provider caches up to16 prepared points within a key, matching
SetDesired's preparation timing and avoiding repeated map queries every rendered
frame. Key/root/origin-height changes invalidate it. Call
`mw_nis_director_invalidate_ground` after explicitly changing world query
generation or provider state within a key. A host check verifies repeated camera
samples in the same key cause no further terrain queries.

`mw_nis_director_choose_track` reproduces
`ICEManager::ChooseGoodSceneCameraTrackIndex` (`8007D76C`). It selects the maximum
dot product of normalized horizontal `(eye-look)` and original player transform
row0, preserving strict comparison/order and the original endpoint selection
for a first key with bSmooth. Single-track scenes return0. GenericStart's two
tracks therefore use an actual source selection rule rather than hardcoded0.
Normalization uses the independently implemented Gekko estimate and original
two refinements in `mw_gekko_math.c`.

## Scene clock and actions

Source `ICETrack::GetParameter` (`80079CC4`), NIS context0, evaluates
`(CAnimScene.GetTimeElapsed()-GetTimeStart()) /
(GetTimeTotalLength()-GetTimeStart())`. The camera track's authored duration does
not define the NIS lifetime. `mw_nis_director_scene_camera` supplies that parameter
directly to the sampler, avoiding a multiply/divide round trip through authored
camera duration, then applies original final FOV truncation to uint16 turn units.
Source roll is turns, as separately proven in opening-nis.md.

Scene chunk80037020 contains child37030. Header+18 is scene type, +28/+2C signed
start/end frame numbers. `CAnimScene::BindToGame` (`8004C068`) multiplies both by
original binary32 `1/30`, storing `mTimeStart+28` and `mTimeTotalLength+2C`.
The actions asset preserves these exact frame numbers and resulting times.

| Scene | Type | Start/end frame |
| --- | ---: | ---: |
| GenericStart | 0 | 0/180 |
| IntroNis04 | 0 | 0/290 |
| IntroNis05 | 0 | 0/180 |
| IntroNis10 | 4 | 0/450 |
| IntroNisDD | 4 | 0/1290 |
| EndingNis03 | 4 | 0/831 |
| IntroNisDDEnd | 4 | 0/100 |

DD ends at43.0000038147 source seconds, even though some actor curves and CARPX
actions contain45 seconds. Do not stretch camera or actor resources to a guessed
common length. Actor controllers independently accumulate15 source frames per
second from actual `m_timeScale=.5` and30 multiplier. See
[actor/action timing](nis-actor-director.md) for native actions, state transitions,
timed/tagged dispatch, registry names and remaining gameplay bindings/effects.

Preserve original phase order when connecting that clock. NISActivity's
UpdatePlaying (`80285970`) calls CAnimScene::UpdateTime with current delta, then
AnimatedCars_Update with current delta. UpdateTime at `8004C5B8` adds the PRIOR
stored `mTimeStep+24` to `mTimeElapsed+20`, then stores current delta at+24.
SetTime (`8004C394`) writes elapsed and resets that previous step to zero.
Actor frame accumulation consumes current delta separately. A generic phase
timer incremented once and reused for both does not reproduce this ordering.

## Validation and native integration

`tools/opening_nis_director.py` runs unchanged SHA-pinned source functions with
explicit input providers:517 rotation matrices,1551 whole-vector transformations,
and173 original GenericStart track decisions all match native results bit for
bit. Private evidence is `opening-nis/director-frame-verification.json`. No guest
instructions were patched. This is bounded original-function reference evidence,
not a complete original NIS or hardware execution claim.

The C host test passes847 scene-clock camera samples across all seven tracks,
actual modes0/1/3, fixed-reference metadata, FOV quantization, finite matrices,
transactional provider failure and invalid clocks under ASan/UBSan.

```sh
cc -std=c11 -Wall -Wextra -Werror -pedantic -fno-fast-math -ffp-contract=off \
 -fsanitize=address,undefined -Iinclude tests/test_nis_director.c \
 source_bmw/mw_nis_director.c source_bmw/mw_nis.c \
 source_bmw/mw_gekko_math.c -lm -o /tmp/mw_nis_director_test
/tmp/mw_nis_director_test \
 /workspace/port-research/opening-nis/native-camera-v2/opening-cameras.nis
```

Actual scene-origin/player matrices, ground queries, actor render bindings and
CARPX event effects must be connected by the application. The provider module
itself performs no allocation or I/O. No main/build edits, SDK build, commit or
push were performed by this subtask.

The companion `mw_nis_pose` helper now closes source actor SQT-to-world conversion
through the actual two-bone ROOT skeleton and original scene matrix chain.
Its source/Bond output matrices match408 full original actor-pose cases. This
supersedes the earlier unproved quaternion-consumer/scene-root terminology;
render model registry binding and effect execution remain application work.

This module supplies the original camera curves and coordinate providers, not
the complete ICEMover::Update rendering pipeline. Its later world/car camera
constraints, shake/noise, overlays, near clip and simulation-speed effects remain
separate consumers. For example DD key20 has bConstrainToWorld set; presenting its
authored eye/target with these providers alone does not prove that subsequent
world clipping and every cinematic effect are also reproduced.
