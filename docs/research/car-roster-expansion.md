# Original car roster expansion

The authoritative private output is `/workspace/port-research/all-native-cars/v7`.
It covers all83original USA geometry packages, with80complete native ground-
vehicle render adapters. The existing rootBMW is retained separately because its
reconstructed livery is more complete than the generic stock converter. Together
these represent81road-vehicle packages and all38source PlayerUsable models in this
inventory. COPHELI needs an aircraft renderer; COPMIDSIZEINT is a separate interior
package, not another standalone four-wheel car. This is asset coverage, not a
claim that original per-car physics, damage, sounds, ownership or unlocks work.

All80catalog/NFM/NWA readers passed ASan/UBSan validation; every indexed vertex
reconstructs its48original bytes exactly, including the renderer UV flip and
unchanged batch/wheel grouping. The converted roster totals334122triangles and
1299texture dependencies. All1299source RGBA textures were compared byte-for-byte
against Tex3DS tiled output. Native catalog size12896B, SHA256:
`f456adbf2e187151476c90eb3668d0e5bc6540eea4523d46d2ad9bd50384490e`.

`coverage.json` retains every original geometry fingerprint, selected sourceLOD,
original rejections, physical MODEL/PlayerUsable provenance and exact failure
reason. NVC1/version2 uses rowoffset20 bit0 for verified source PlayerUsable;
other bits remain zero. Pricing/frontend keys are separate. For example Carrera
GT is PlayerUsable despite the source model/pvehicle `carreragt` and frontend
`carrera_gt` names differing. No frontend key is invented to grant ownership.
Version1 remains compatible when no flags are present. Root staging preserves
custom opening-opponent paint assets and the BMW while merging new model rows.

## Actual source geometry and LOD choices

The converter rechecks chosen previously original-emitter-verified descriptors
against the supplied source package bytes. Geometry retains original positions,
normals/UVs and texture hashes; police use genuine intact DAMAGE0 exteriors.
Rejected nonempty exterior parts reject the candidate; driver-only failures are
explicitly outside this static-exterior scope. No placeholder texture, substitute
car or hidden missing window is used to report a successful model.

Most vehicles use the existing B/C offline source LOD. Three source alternatives
close the problematic packages without editing their rejected high-detail data:

- CAYMANS uses actual CLOD(3764native triangles). All24selected stock parts have
  valid original bounds and correctly located rear side windows. The outlying
  Bwindows are not hand-moved or silently removed.
- DB9 uses its actual monolithic KIT00_BODY_E(398source triangles), containing
  genuine WINDOW_MASK glazing and CARBOTTOM coverage, with independently checked
  original Btire/brake meshes(2612native triangles total). This is a deliberately
  coarse native offline body/wheel policy, not original live per-part LOD logic
  or full high-detail DB9. The inverted B/C/Dwindow records remain documented;
  Acontains decals only and is not a full-body replacement.
- TRAFDMPTR uses actual intact DLOD(666native triangles), whose body includes
  MISC,SKIN1,WINDOW_MASK and CARBOTTOM, plus original Dwindow/tire parts. That
  complete source assembly does not request the unresolved C_BADGING material.
  No Cbadging texture is fabricated or dropped from the Cbody.

`car_geometry_expanded.py --car NAME --lod C` supports explicit bounded model/LOD
exports; existing default B,C,A,D,E behavior remains unchanged. Private alternate
exports are car-model-player-lod-c, car-model-db9-lod-e and car-model-dmptr-lod-d.
Large trucks/trailers use an explicit16metre native halfextent bound; actual
maximum accepted halfextent is6.636474609375metres.

## Original traffic tire replacement

The original CarTypeInfo table lives in GLOBALB_VM_NGC chunk34600:84records of
208bytes. Matching debug metadata places UsageType at148. Source constructor
802c80f8..802c8108 checks UsageType==2(CAR_USAGE_TYPE_TRAFFIC); 802c815c..802c81c8
sets replacement slot12(TIRE) to hash("TRAFFIC_TIRE")=`896efc91`, invalidating its
cache only when the target changes. The genuine global texture is present.

`tools/car_traffic_tires.py` executed the unchanged original LoaderCarInfo,
including its actual endian-swap callees, and matched all84UsageType values. It
also ran24unchanged original constructor cases across ordinary/cop/traffic/wheel/
universal/invalid usages and changed/unchanged target caches:zero differences.
Private proof: all-native-cars/traffic-tire-reference.json. All27traffic model
bindings now use that original target where the source CAR_TIRE alias occurs,
including when a local car-specific tire image also exists. This closes eight
previously blocked traffic/trailer models. The older baseTRAFHA should be
replaced with this source-correct expanded asset; it formerly used its local
texture without the source replacement.

Only three standalone conversions remain blocked: the alternate stock BMW
material(its existing rootasset remains available), COPHELI without a ground-car
rig, and COPMIDSIZEINT separate interior material binding. No original package
or rejected data was deleted. The coarse/stock render policies remain explicit:
front tire instancing, source-palette flat paint, kit/rim assembly and complete
shader/animation/material consumers are separate from this asset expansion.

## Reproduce and validate

Use a NEW output directory. Cache reuse checks source body/rig hashes and every
texture's original RGBA hash; Tex3DS output is still checked after copying. The
original inputs and prior converted outputs remain untouched.

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps python3 tools/build_all_cars.py \
 --meshes /workspace/port-research/car-model-expansion-v2 \
 --alternate-meshes /workspace/port-research/car-model-player-lod-c \
 --alternate-meshes /workspace/port-research/car-model-dmptr-lod-d \
 --coarse-body-meshes /workspace/port-research/car-model-db9-lod-e \
 --candidates /workspace/port-research/all-car-candidates \
 --attributes /workspace/attachments/857a1856-1b3b-4be1-8a91-42f437324e6f/ATTRIBUTES.BIN \
 --carparts /workspace/port-research/v018-decoded/GLOBAL-GLOBALB_VM_NGC.BUN \
 --frontend /workspace/attachments/430e54cf-3f7e-4284-81a1-67743e30a796/GLOBAL-FE_ATTRIB.BIN \
 --shared-textures /workspace/port-research/bmw/shared \
 --shared-textures /workspace/port-research/bmw/wheels \
 --shared-textures /workspace/port-research/shared-textures/globalb \
 --output /workspace/port-research/all-native-cars/fresh-output \
 --reuse-native /workspace/port-research/all-native-cars/v7 --native-textures
bash tools/test_car_roster.sh /workspace/port-research/all-native-cars/fresh-output
```

Only authored tools/tests/notes belong in Git. Original/converted assets, decoded
mesh caches and executable/debug payloads remain private. Host geometry and pixel
checks do not establish hardware FPS or full original vehicle behavior.
