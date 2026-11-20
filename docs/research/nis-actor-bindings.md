# Original opening NIS actor curves

`tools/nis_actor_bindings.py` decodes the original uploaded animation banks. It does not invent actor motion or substitute an orbit camera. The source assets and decoded coordinate arrays remain private under `/workspace/port-research/opening-nis`.

## Recovered representation

The wrapper is ELF32 little endian, machine 8, based 16 bytes into each source chunk. `.data` is already big endian, except pointer relocation addends stored little endian. `.rel.data` locations must be read as little endian offsets and converted into native pointers; swapping the entire data section corrupts its floats. The `__AnimationBank:::bank` symbol locates type 28, with count at +4, curve pointer array at +16, name pointer array at +20. Original getters: `80050060`, `8005006C`, `80050080`; original case-sensitive name search `8008A81C`.

The bank curves are type 15 composites, vtable `803D5B18`. Their child descriptor pointers are stored inline starting +12, with child count at +8. The child types in these banks are 10 (scalar channel groups, including translations and scales) and 11 (quaternion groups). Both refer at +4 to a compressed payload, with frame count at descriptor +8 and destination channel indices at +10.

The compressed payload contains BE u16 channel count, byte 2 quantization bits (4/8/16), and three BE float32 values per channel: delta bias, delta scale, initial sample. Subsequent unsigned quantized samples encode *deltas*, not absolute values. Original `8008D78C` initializes at the initial sample, then repeatedly applies `sample = f32(sample + f32(bias + scale * unsigned_quantized_delta))`. Nibble order is low then high. Translation destinations are 20/21/22, quaternion 16..19 and scale 12/13/14. These are original animation output channels, not claims that a renderer uses the same struct layout.

Translation sample function `8008BEDC` (vtable `803D57D0`) and quaternion function `8008C3B0` (`803D5728`) truncate time to an integer frame, clamp integer selection to valid frames, and use `8008DC68` for the fractional delta to the next frame. The quaternion path interpolates four scalar components here; the downstream original ROOT and quaternion consumer is now closed by [the native pose helper](nis-pose.md), with no normalization inserted.

## Verification

Running with `--verify-dol <Speed.dol>` compares first, second, midpoint and final frames against bounded execution of the original `8008D78C`, using the SHA-pinned USA executable (`33c5eae699f871beac059b6932475cad5e9f610bb2b2298e046d043757b94166`). Zero absolute error was measured for all 352 evaluated complete channel groups across the seven banks. This checks the original integer-frame decoder, not the entire scene director or console execution.

| Source chunk | Scene | Curves | Source comparison cases |
|---|---|---:|---:|
| c91e014b | GenericStart | 9 | 24 |
| 234d6fba | IntroNis04 | 8 | 16 |
| 72ac793b | IntroNis05 | 6 | 24 |
| 21118357 | IntroNis10 | 12 | 48 |
| ba42885e | IntroNisDD | 30 | 120 |
| 30185662 | EndingNis03 | 24 | 96 |
| 37d7e4b5 | IntroNisDDEnd | 6 | 24 |

Private outputs are `<chunk>-actors.json`. For example IntroNisDD Car1 translation has 676 samples from source XYZ `(1046.32947,99.03914,100.35159)` to `(2162.15503,-529.47089,116.01654)`. GenericStart, IntroNis04 and IntroNis05 have small local coordinates and must not be treated as absolute Rockport coordinates.

## Time conversion and director closure

The generic composite sample routine `8008AD74` supports an optional conversion context: virtual +24 (`8008B7B0`) reads metadata tag 1 through `8008AA28`, copies its first payload byte into the rate field, and sample multiplies incoming time by that byte. The banks contain payload `1E303030`, so this optional path uses 30. With no context, incoming values remain frame indices.

The actual car-controller path is now separately proven: `CAnimScene::CreateCarAnimationControllers` installs time scale **0.5** and `CAnimCtrl::AdvanceAnimTime` accumulates frames at `0.5 × 30 = 15` per input second. `UpdateAnimPose` passes these frame indices directly, without the optional rate-30 context. Therefore native actor playback should accumulate original frame time and use `conversion_context=0`. Original execution verifies this clock. See [actor director recovery](nis-actor-director.md).

Scene lifetime is independently sourced from the scene header's signed start/end frame fields multiplied by float32 1/30. IntroNisDD ends at 43.000003814697266 seconds even though its actor curves span up to 45 seconds. Neither actor length nor CARPX action duration may replace the scene window.

CARPX actions, system/state transitions, tagged events, timed events and original constructor argument bytes now have a native cached asset/API, with 705 original dispatcher comparisons. The original quaternion/SQT consumer, actual two-bone ROOT skeleton and full source-world/Bond matrix chain are closed by [mw_nis_pose](nis-pose.md), with 408 bit-identical original matrix comparisons and three original terrain-consumer cases. Actual vehicle identities must still follow the original racer registry order/context; renderer/gameplay implementations of each dispatched original effect remain caller work.

## Camera provider boundary

Independent parent trace establishes that camera mode 0 uses a smoothed camera-subject reference frame, not an arbitrary scene anchor. TrackCamera constructor `8007A720` is called at `8007087C` with the parent camera +`0x2C8` frame. That frame is created via `8007A24C` and populated by `8007A0D4` from the subject transform referenced at parent +`0x2D4`; `80070B14` obtains that transform through subject virtual +`0xE8`/`0xEC`. The reference frame stores the 4x4 at +16 and its translation at +0. Mode 3 uses a separate NIS actor virtual +`0x68`/`0x6C` provider and ground adjustment `8007D480`. A current player pose must not be substituted for either frame until actual subject/actor binding is established.

## Native portable actor asset and API

`include/mw_nis_actor.h` and `source_bmw/mw_nis_actor.c` provide the independent bounded native sampler. The generated private file is `/workspace/port-research/opening-nis/native-actors-v1/opening-nis-actors.nna`: 769,904 bytes, seven scene banks, 95 named curves, SHA-256 `7a41cdd97ca7813fcbc8cea377124bb1dd7d0f1c130bef8e9723e8f664fcd049`. Regenerate with:

```sh
python tools/nis_actor_bindings.py /workspace/port-research/opening-nis/actor-elf-inputs --native /workspace/port-research/opening-nis/native-actors-v1/opening-nis-actors.nna
```

`actor-elf-inputs` contains seven links to the original per-scene source bundles; the unrelated whole INGAMEMB scene bank is deliberately excluded. Native storage includes the original decoded sample **and the source decoded next-frame delta** for each frame. Subtracting rounded adjacent samples would lose the original fractional result. The sampler evaluates `fmaf(fraction, source_delta, source_sample)`, matching the source `8008DC68` path. It never normalizes quaternion output. The recovered [pose helper](nis-pose.md) supplies original source coordinate/quaternion consumption; [actor director recovery](nis-actor-director.md) documents the actual frame clock and source event timelines.

```c
MwNisActorBank bank;
MwNisActorScene scene;
MwNisActorCurve curve;
float xyz[4];
if (mw_nis_actor_open(&bank, "opening-nis-actors.nna")) {
    if (mw_nis_actor_find_scene(&bank, "IntroNisDD", &scene) &&
        mw_nis_actor_find_curve(&bank, &scene, "IntroNisDDZPM_Car1_t", &curve)) {
        /* Original car playback accumulates source_curve_frame at 15 frames
         * per input second; 0 leaves this original frame index unchanged. */
        mw_nis_actor_sample(&bank, &curve, source_curve_frame, 0, xyz, 4);
    }
    mw_nis_actor_close(&bank);
}
```

Opening the file performs one whole-file allocation, bounded at 2 MiB (the current source asset consumes about 752 KiB), then closes the file. Sampling performs no allocation or SD reads: bounded copies of up to 32 bytes and up to four float arithmetic operations. Exact case-sensitive names, actor tokens, kind, channel destinations, frame count and metadata conversion rate are retained. The token `Car1` or `Cop1` is explicitly not a gameplay identity or model binding. The API clamps requests outside its finite frame interval; nonfinite time, insufficient output space, invalid file directory/size or invalid curve payload bounds fail.

The native C fractional sampler was additionally compared against bounded execution of the original SHA-pinned `8008DC68`: quarter, half and seven-eighth positions in first, middle and last available frame segments for all seven banks. All **771 whole-channel comparisons had zero absolute error**. Private evidence summary: `native-actors-v1/native-fractional-verification.json`. This includes type-11 quaternion component output, and is independently supplemented by the subsequently recovered original quaternion/ROOT consumer and actor clock. Higher-level vehicle identities and applied visual effects require their actual runtime consumers.

Host regression command:

```sh
cc -std=c99 -Wall -Wextra -Werror -Iinclude tests/test_nis_actor.c source_bmw/mw_nis_actor.c -lm -o /tmp/test_nis_actor
/tmp/test_nis_actor /workspace/port-research/opening-nis/native-actors-v1/opening-nis-actors.nna
```

The host test checks private source positions and quaternion values, metadata time conversion, case-sensitive lookup, cache lifecycle and invalid sampler input. No application/SDK build, original-game asset commit, or Git push was performed by this child task.
