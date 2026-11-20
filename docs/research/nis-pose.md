# Original animated car pose consumer

`include/mw_nis_pose.h` / `source_bmw/mw_nis_pose.c` implement the original SQT-to-vehicle matrix consumer for the recovered opening NIS car slots. The original quaternion order is x/y/z/w and the original consumer **does not normalize it**. Fractional animation samples retain that behavior.

Original matching executable/debug symbols identify:

| Address | Original function |
|---|---|
| 80090448 | EAGL4::Transform::BuildSQT(float ×10) |
| 800A39D8 | EAGL4Anim::Skeleton::GetStillPose |
| 800A37DC | EAGL4Anim::Skeleton::PoseSQTToGlobal |
| 800A3D78 | Original EAGL matrix multiplication wrapper |
| 8005E024 | bMulMatrix |
| 8010AB28 | eMulMatrix |
| 80329EA0 | PSMTX44Concat |
| 8005D4B0 | bConvertToBond |
| 8004CEB0 | CAnimScene::AnimatedCars_SetMainAndWheels |
| 802F0FDC | WCollisionMgr::GetWorldHeightAtPointRigorous |

Global `80457604` is symbol `skel_ROOT_hash`; `CreateCarAnimationControllers` resolves it through `GetSkeletonFromList`. The first ELF in the private `0e1075eb.bin` has symbol `__Skeleton:::ROOT`, two bones, root parent -1 and animated child parent 0. The actual original `GetStillPose` produces identity SQT for **both** bones: scale `(1,1,1)`, handedness factor 1, quaternion `(0,0,0,1)`, translation `(0,0,0)`, final padding 1. Actual channel destinations 12..23 therefore animate bone 1. `AnimatedCars_SetMainAndWheels` reads the second 64-byte matrix. No arbitrary parent/bind transform is supplied by the native helper.

The native path builds that child SQT matrix, performs the original ROOT parent multiplication, then multiplies by the source scene rotation and scene translation, in that order. Matrix dot products preserve original single-precision multiplication and fused-add order with `fmaf`. The helper returns either or both stages:

- `out_source_world[16]`: original matrix after source scene rotation and translation, before Bond conversion. Translation remains source XYZ at indices 12,13,14.
- `out_original_bond[16]`: original `bConvertToBond` result. Translation becomes `(-sourceY, sourceZ, sourceX)` at indices 12,13,14. The basis rows also receive the exact source permutation/sign conversion.

`mw_nis_pose_vehicle(scale3, quaternion4, translation3, scene_rotation16, scene_translation16, out_source_world16, out_original_bond16)` performs the full matrix chain. `mw_nis_pose_sqt` and `mw_nis_pose_world` expose the stages separately. Scene rotation/translation must come from the recovered original scene provider, not a guessed player-relative anchor. The source-world output is convenient for renderers retaining source map coordinates; the Bond output matches the original vehicle interface boundary.

## Terrain stage

The original outer function constructs a WCollisionMgr query with mask 0/type 3, supplies the current **Bond translation** as the query point, and calls `GetWorldHeightAtPointRigorous(point, height, normal=NULL)`. It does not request a normal. When the query reports a hit, it overwrites Bond matrix index 13 with **returned world height + 5.0** (`803CFE14`). This is a post-query vehicle height offset, not a query start offset. When the query misses, animated Bond Y remains unchanged.

`mw_nis_pose_ground_height(bond_matrix, hit, returned_world_height)` reproduces this final arithmetic. The actual rigorous terrain query is external and must use the recovered source collision implementation. This helper does not invent an approximate ground plane or claim the real terrain query ran when it was supplied by a caller.

## Original comparison and validation

`tools/nis_pose_reference.py` runs the pinned original USA DOL through bounded PPC execution, using the actual private ROOT skeleton and decoded source actor curves from all seven banks. It executes `GetStillPose`, `PoseSQTToGlobal`, the ROOT parent multiply, both scene matrix multiplies and Bond conversion. **408 full pose cases** across original actor slots, multiple frame positions (including fractional SQT samples), and three supplied scene roots produced **bit-identical source-world and Bond 4×4 matrices** against the native C helper. No quaternion normalization was inserted.

The reference additionally executes the original entire `AnimatedCars_SetMainAndWheels` outer function for three terrain hit/miss cases, intercepting only the external terrain query and COM vehicle destination. The query point, mask/type and null normal pointer are captured; the complete vehicle output matrix matches the native helper for a miss and two distinct returned heights. This proves the consumer arithmetic and provider contract, not execution of real terrain geometry in those intercepted cases. Private evidence: `opening-nis/native-actors-v1/pose-reference.json`.

Run the reproducible original comparison with:

```sh
cc -std=c99 -O2 -ffp-contract=off -fPIC -shared -Iinclude source_bmw/mw_nis_pose.c -lm -o /tmp/libmw_nis_pose.so
PYTHONPATH=tools:/workspace/toolchains/python-deps python tools/nis_pose_reference.py --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol --root-bundle /workspace/port-research/opening-nis/raw/0e1075eb.bin --actor-inputs /workspace/port-research/opening-nis/actor-elf-inputs --library /tmp/libmw_nis_pose.so --output /workspace/port-research/opening-nis/native-actors-v1/pose-reference.json
```

Host regression:

```sh
cc -std=c99 -Wall -Wextra -Werror -ffp-contract=off -Iinclude tests/test_nis_pose.c source_bmw/mw_nis_pose.c -lm -o /tmp/test_nis_pose
/tmp/test_nis_pose
```

The native helper allocates no memory, accesses no files, uses bounded stack matrices and rejects missing/nonfinite inputs. Compile without unsafe fast-math/reassociation; explicit `fmaf` retains original fused matrix operations. No SDK application build or Git operation is performed by this child task.

## Downstream consumer clarification

Followup debug-symbol/vtable tracing identifies the original matrix destination
as **INISCarControl::SetNISPosition**, concrete
`SuspensionSpline::SetNISPosition`80252E74. This is not a renderer setter.
Subsequent poses preserve the live rigid-body Y position and Y velocity while
replacing X/Z, then the spline suspension computes wheel/ground forces. Applying
its incoming ground+5 directly to a display matrix bypasses that consumer.
[Opening integration](opening-cinema-integration.md) documents this source path
and exposes raw animation poses separately until that suspension is connected.
