# Original opening opponent model assets

`tools/build_opening_opponent_assets.py` prepares the six actual model identities
referenced by the original opening opponent presets. It does not relabel a
traffic car, replace a model with the BMW, or fabricate police/race artwork.

Private output:
`/workspace/port-research/opening-opponent-assets/v1/`.

Each uppercase model directory contains `body.nfm`, `wheels.nwa` and native
`textures/*.t3x`; `catalog.nvc` supplies source ecar keys, normalization extents,
body/wheel CRCs and path-safe identifiers. The catalog contains six NPC entries
with frontend purchase key0. Catalog presence does not imply player ownership.

| Original preset | Actual model | ecar key | Triangles | Half extent |
| --- | --- | --- | ---: | ---: |
| RAZORMUSTANG | MUSTANGGT | 9b93fd4d | 6266 | 2.37451171875 |
| DDAYSUPRA | SUPRA | 66f13434 | 6884 | 2.255615234375 |
| BL2 | SLR | e32ad9bb | 7806 | 2.3291015625 |
| OPM_MUSTANG_BOSS | GTO | aa483dc6 | 7326 | 2.411865234375 |
| OPM_WRX_VERSION2 | IMPREZAWRX | 5f3b560d | 6994 | 2.195556640625 |
| OPM_RX8_Version3 | RX8 | d6334437 | 7009 | 2.21728515625 |

The surprising GTO mapping comes from the actual preset model field, not the
text `MUSTANG` in its preset name. All six model packages are fully accepted at
their selected source B LOD. The converter independently reloads every selected
part from the original geometry and compares its source descriptor packets,
positions, S8/64 normals, UVs and source strip/material associations against the
earlier original-execution-checked expanded export.

## Paint provenance and remaining appearance differences

The original DOL's139-entry part enum table names index76 `BASE_PAINT`. Each
actual preset's key at that index selects an original car-part palette record.
The source RGB values are retained exactly:

| Model | Original base paint | RGB |
| --- | --- | --- |
| MUSTANGGT | GLOSS_L1_COLOR62 | 0,0,0 |
| SUPRA | GLOSS_L1_COLOR28 | 242,228,0 |
| SLR | GLOSS_L1_COLOR62 | 0,0,0 |
| GTO | GLOSS_L1_COLOR24 | 191,38,38 |
| IMPREZAWRX | METAL_L1_COLOR06 | 242,184,48 |
| RX8 | GLOSS_L1_COLOR76 | 11,14,46 |

Real texture-bank pixels take precedence. A missing runtime-generated SKIN1/2
receives this exact palette's RGB as an explicitly **flat native diffuse
adapter**. Source gloss is retained as metadata; it is not used as visibility.
This is not the original metallic/specular/reflection/paint shader or final
customized livery. In particular, a full-body vinyl can make the original car
look quite different from its underlying base palette color.

The complete preset record,139 part keys, actual base-paint part and geometry/
texture provenance remain in private `scene.json` files. Customized body kit,
hood, spoiler, rim and vinyl/unique-livery assembly are not recovered by this
converter. Geometry is explicitly the real model's intact KIT00 adapter. Four
tires use the exact typed source `TireOffsets`; complete hub/body-height/rim
producers remain separate. Intact default lamp selection and the common untinted
window binding inherit the documented starter converter adapters.

These limitations are retained in the native asset manifest. The output must not
be described as six exact rendered opponent presets or original race AI.

## Verification

- The six actual preset records match the unchanged original PowerPC preset
  loader's byte transformations, with actual source enum labels from the DOL.
- All145 native Tex3DS RGBA8 payloads compare byte-for-byte with the corresponding
  validated source/adapter RGBA input and independently tiled reference.
- ASan/UBSan runs actual C `nfs_scene_decode`, `wheel_rig_decode` and catalog
  readers for all six outputs. Body/rig dependencies and NPC keys are accepted.
- The vehicle-index regression reconstructs every original48-byte vertex and
  post-V-flip GPU attribute, preserving batch ranges and all five wheel groups.
  Across the six outputs it saves3,590,514 geometry bytes, without removing
  triangles or quantizing attributes. This is not a hardware FPS measurement.

The1056-byte native catalog has SHA256
`4cb81cba215459947dd66d22492a154467cb02b857aa785587c46103e420c69c`.
Private `catalog.json`, per-model `scene.json` and `verification.json` preserve
the source fingerprints, exact adapter choices and native reconstruction counts.

## Reproduce

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps \
python tools/build_opening_opponent_assets.py \
 --meshes /workspace/port-research/car-model-expansion-v2 \
 --candidates /workspace/port-research/all-car-candidates \
 --attributes /workspace/attachments/857a1856-1b3b-4be1-8a91-42f437324e6f/ATTRIBUTES.BIN \
 --carparts /workspace/port-research/v018-decoded/GLOBAL-GLOBALB_VM_NGC.BUN \
 --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
 --shared-textures /workspace/port-research/bmw/shared \
 --shared-textures /workspace/port-research/bmw/wheels \
 --shared-textures /workspace/port-research/shared-textures/globalb \
 --output /workspace/port-research/opening-opponent-assets/fresh-output \
 --native-textures --verify-original-loader --verify-host
```

Original input and prior output directories are not overwritten. Cached Tex3DS
asset conversion runs with networking disabled. Original/converted game payloads
stay private; only the authored tool and evidence documentation belong in Git.
No application SDK build, shared runtime edit, commit or push was made here.
