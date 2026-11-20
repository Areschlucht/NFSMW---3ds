# Original NIS actor clock and CARPX event director

`tools/nis_actor_director.py` exports the surviving source CARPX event scripts, including exact system/state transitions, timed and tagged event lists, original event hashes and original big-endian constructor argument bytes. It uses the uploaded USA executable's case-sensitive Jenkins lookup2 string hash (`801956E8`) and original event-name strings. It does not invent model/player bindings or implement event renderer effects by name alone.

## Actor clock closure

The matching original debug ELF (`opening-story-services/original-debug.elf`, SHA-256 `6ee16d55d92ad1b337a9b655989c32b2976f95e7c64e148cf83f482c613f79f7`) supplies names and DWARF1 layouts for initialized code independently confirmed identical to the original DOL. Relevant symbols:

| Address | Original symbol |
|---|---|
| 8004CC04 | CAnimScene::CreateCarAnimationControllers |
| 80047450 | CAnimCtrl::AdvanceAnimTime(float) |
| 800476E4 | CAnimCtrl::UpdateAnimPose(bool) |
| 8004D14C | CAnimScene::AnimatedCars_Update(float) |
| 8004CEB0 | CAnimScene::AnimatedCars_SetMainAndWheels |
| 8004C914 | CAnimScene::InitCarAnimStatesFromStartingPositions |
| 8004C9E0 | CAnimScene::InitCarAnimStatesFromNIS |

`CreateCarAnimationControllers` sets `CAnimCtrl::m_timeScale` (+0x60) to the source constant **0.5** (`803CFE0C`, store `8004CD54`). `AdvanceAnimTime` multiplies its incoming delta by `m_timeScale * 30.0` (`803CFAE0`) and accumulates `m_evalTime` (+0x68). `UpdateAnimPose` passes that accumulated **frame** directly to the original curve sampler. These curves have no conversion context installed in this path. Therefore the actual default source clock advances **15 curve frames per input second**. This differs from the optional rate-30 metadata context accepted by the independent actor sampler.

For native playback, accumulate `frame = f32(frame + f32(delta_seconds * 15.0))` with the original forward nonlooping clamp, and sample actor curves with `conversion_context=0`. Pause/scene lifetime remain controlled by CAnimScene. Original executable reference comparisons matched every accumulation step for 60 × 1/60, 30 × 1/30, 10 × 0.1, 45 × 1 and 5 × 10 second deltas. Private evidence: `opening-nis/actor-clock-reference.json`.

Actor curve length does **not** control scene lifetime. Original `CAnimScene::BindToGame` (`8004C068`) reads signed frame integers at scene header +0x28 / +0x2C, multiplies by float32 1/30 (`803CFDB0`), and stores scene start / total times at object +0x28 / +0x2C. Parent-decoded `scene-time-metadata.json` is retained exactly in native scene records. IntroNisDD ends at **43.000003814697266 seconds**, even though its 676 actor samples could run for 45 seconds. Camera normalized progress uses the actual scene window; do not stretch actor curves or replace this window with CARPX action duration.

## Source actor binding and transforms

Original table `80415794` maps animation slots 0..7 to `ZPM_Car1`..`ZPM_Car8` and 8..15 to `ZPM_Cop1`..`ZPM_Cop8`. Source registry resolution at `8004C914` / `8004C9E0` binds `car1`..`car8` and `cop1`..`cop8` to those slots. Array `80457610` has sixteen 16-byte entries: controller at +0, actual vehicle interface at +4, last-pose state at +8 and slot state at +12.

`EPlayRaceNIS` constructor (`801DFD04`) registers `car1`..`car8` by iterating `IVehicle` list enum 6, confirmed by DWARF as **VEHICLE_RACERS**. Producer calls are `801E02B8`..`801E0378`. This proves original racer-list slot order, not that `car1` universally means the local player. `NISActivity::PrepareVehicles` (`80284564`) constructs/registers police context, including `cop1` at `8028469C`..`802846D0`. The actual gameplay vehicle objects must be bound using this source ordering/context.

Original actor transforms follow `EAGL4Anim::Skeleton::PoseSQTToGlobal` (`800A37DC`), then copy the second pose matrix (`CAnimCtrl+0x2C` matrix array, +0x40) via `PSMTX44Copy`, multiply by scene rotation (+0x44) and translation (+0x84) via `bMulMatrix`, and pass through `bConvertToBond` (`8005D4B0`). Scene fields are DWARF-confirmed (`CAnimScene` DIE 0x5EF170). The independent actor API returns original SQT channels; [mw_nis_pose](nis-pose.md) now implements this exact ROOT/quaternion/scene matrix consumer, verified bit-for-bit against 408 full original poses. Its terrain-height helper additionally matches three original outer consumer hit/miss cases. This closes the former quaternion and root-matrix arithmetic gates; original registry identity and event effect implementations remain caller responsibilities.

## CARPX structure and original dispatch semantics

The CARPX descriptor count excludes the header. Each descriptor is 16 bytes; offsets are relative to that descriptor. Source DWARF confirms:

- `CARP::EventSeqAction`: 16-byte header with name hash, number of tags, number of times, duration; followed by tag hashes, timed float values, then event-list references for both groups.
- `CARP::EventSeqSystem`: initial state hash, default state hash and state count; followed by state hashes and references.
- `CARP::EventSeqState`: stimulus count and filter hash; followed by stimulus hashes and pairs of next-state hash / action reference.

The scripts include actual visual/vehicle events such as `ENISLights`, `ENISBrakelock`, `ENISCarPitch`, `ENISCarRoll`, `ENISDetach`, `ENISReattach`, `ENISNitro`, `ENISTimeOfDay` and `ENISPlayEffect`. Constructor argument words are preserved; the library does not apply guessed renderer meanings.

Original event scheduler symbols are `EventSequencer::System::InvokeStimulus` (`801ECE38`), `FireTimedEvents` (`801ED084`), `FireActionEventList` (`801ECF6C`), `FireEventTag` (`801ECAC8`) and `InternalReset` (`801ED244`). Timed dispatch uses **(previous, current]**, retaining source order. Starting an action sets prior elapsed time to **-1**, fires its source `start` tag, then performs the first update, admitting timed events at 0. Action duration and end-tag/state processing remain caller responsibilities. Native functions only dispatch the selected original event lists.

The helper's `--verify-source` option runs original `801ED084` and its original lower-bound search, intercepting only final event-list callbacks to collect dispatch indices. **705 original dispatcher comparisons** matched the native interval predicate, including exact event boundaries, equal-time windows, initial zero and whole timelines. Private output `actor-director.json` contains this result and complete source actions/states. All currently admitted source action time arrays have unique timestamps.

## Native asset/API and tests

Files: `include/mw_nis_actions.h`, `source_bmw/mw_nis_actions.c`, `tests/test_nis_actions.c`.

Private asset `opening-nis/native-actions-v1/opening-nis-actions.nac` is **16,584 bytes**, SHA-256 `0026f8f4949f3500229be581f8592acfba8f3d0fcef56df01c2657fdb079dc7c`. It contains seven exact scene timing/type records; forty actions; forty systems; eighty-one states; forty transitions; 204 tagged/timed event lists; and 225 original commands. Five supplied bundles include CARPX scripts. GenericStart and IntroNisDDEnd have admitted scene metadata and actor curves but no CARPX scripts in their supplied chunks; the asset does not fabricate any.

Open performs one bounded whole-asset allocation (limit 2 MiB); all lookups and callbacks thereafter use cached memory with no SD access. `mw_nis_actions_find_scene` exposes exact source type, signed start/end frame and converted start/total seconds. System/state/transition getters expose original source filters and action selection. Callers must handle nonzero filters with source semantics, rather than treating them as unconditional. Original IntroNisDD `car1` has initial state `Begin1`, stimulus `START` (`0xA6A56EA1`), action `ActionCar1`, next state `End1`; the host test checks this source chain.

Regenerate with:

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps python tools/nis_actor_director.py /workspace/port-research/opening-nis/actor-elf-inputs --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol --scene-metadata /workspace/port-research/opening-nis/scene-time-metadata.json --verify-source --output /workspace/port-research/opening-nis/actor-director.json --native /workspace/port-research/opening-nis/native-actions-v1/opening-nis-actions.nac
```

Host validation:

```sh
cc -std=c99 -Wall -Wextra -Werror -Iinclude tests/test_nis_actions.c source_bmw/mw_nis_actions.c -lm -o /tmp/test_nis_actions
/tmp/test_nis_actions /workspace/port-research/opening-nis/native-actions-v1/opening-nis-actions.nac
```

Checks cover exact source scene time/type, source state/action binding, lower-exclusive and upper-inclusive timing, source command order, preserved BE constructor payload, tagged dispatch and invalid input. No SDK build or commit is performed by this child task.
