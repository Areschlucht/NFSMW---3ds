# Original COPMIDSIZE exterior for the opening police encounter

`tools/build_opening_police_car.py` creates a separate native police asset from
the already supplied original files. It does not relabel TRAFHA, generate police
paint, change the starter-car roster or implement police AI/sirens. The original
opening flow's SpawnCop references motivated this asset; actor placement and
encounter completion remain the parent's career runtime responsibility.

## Exact source identity

| Input | Identity |
| --- | --- |
| Source vehicle | ecar/copmidsize, collection key **bb9b2938** |
| GEOMETRY.BIN | SHA25616404230013ae6d7a1178faadef35bb6f590ccdb59fcc60be90b47346cea6818 |
| Geometry archive range | ZZDATA1,259911680 bytes,606464 bytes long |
| TEXTURES.BIN | SHA2564fa0f637769d1ef721057741b688a8f5133aa25e4b7e5ff499a3f39bb1b2f4ad |
| Texture archive range | ZZDATA1,260519936 bytes,52928 bytes long |
| Attributes | Pinned original SHA2565b69c44ffcfc7013a3f24900b33617002b1f68f2484a9108daa5bfe5d72ad20c |

The strict expanded source package is complete at offline B-LOD, with31 exported
parts across damage states. Its police exterior uses explicit
`COPMIDSIZE_KIT00_DAMAGE0_*_B` names. The generic starter-car filter deliberately
excludes all DAMAGE names, so using it unchanged would omit the actual police
body. The dedicated tool selects exactly15 Damage0 exterior parts, including
BODY, doors, hood/trunk, bumpers, headlights/brakelights, front window and the
original **COP_LIGHTS roof geometry**. DAMAGE1 parts are not substituted.

One original FRONT_TIRE_B is mounted four times at the original typed TireOffsets:
frontX1.75/rearX-1.29999995, lateral offsets +/-0.94 and +/-0.95, radius0.33000001.
Those values retain original source provenance. This shares the existing native
wheel mounting adapter; complete original hub/body height/rim transformations and
part-animation consumers are not claimed. The separate DRIVER/interior part is
explicitly omitted; this asset is the exterior police cruiser.

Every selected mesh is decoded again from the pinned original geometry using the
existing strict descriptor-parity helpers and compared against its preserved
source export. Normals, UVs and exterior geometry are retained, apart from the
documented native coordinate conversion/normalization and degenerate removal
already used for starter cars. No shared decoder was relaxed.

## Original police artwork

The police bank supplies the actual256x256 COPMIDSIZE_SKIN1 and128x128
COPMIDSIZE_BADGING artwork, plus original tire and lamp assets. No flat-palette
paint or generated8x8 police marking is emitted. All15 texture dependencies
resolve to original local/shared pixels or the existing verified intact-default
lamp selector. That selector currently uses flags1608/160C=0; flashing emergency
lights, emissive materials, damage-state lamps and siren audio remain separate.

The tool imports existing_pixels, original_texture_bank, texture_binding,
native_textures and pack_catalog from build_starter_cars.py, and uses the same
strict NFM/NWA encoders. It does not edit that shared helper. A None paint input
intentionally forbids a generated paint fallback for this source model.

## Private native output

Directory: `/workspace/port-research/opening-police-car/v1/`

- `COPMIDSIZE/body.nfm`:7938 expanded vertices,2646 triangles,24 batches,
  15 source texture bindings;381680 file bytes.
- `COPMIDSIZE/wheels.nwa`: four original mount pivots/radii, original source-bound
  batch groups0..4; wheel payload CRC **f8cc7697**.
- `COPMIDSIZE/textures/*.t3x`: all15 validated source pixel conversions.
- `COPMIDSIZE/scene.json`: original parts, texture bindings, source ecar record,
  typed wheel offsets, coordinate extent and explicit limitations.
- `catalog.nvc`: one256-byte NPC-only entry, frontend key0, ecar keybb9b2938;
  half_extent **2.605224609375**, body CRC **8043c9f2**.

Body SHA256:
`00a959c6abd6c09e312aecc8df4645d6e01c8b2704247e1923efec4853f14442`

Wheel SHA256:
`65a42449fc12443a29bc3399722123fbef41d9a82696b37d7800d8c6d40886ac`

NVC SHA256:
`7f9f85234cacbb141e621479e688e035afd82e519ae87c9b642d211a54814b30`

The readable display text “Police Cruiser” is a native label, not a recovered
localized original vehicle name. NPC presence does not imply player purchase or
career unlock.

## Checks and reproduction

All15 source RGBA images match their uncompressed Tex3DS tiled output byte for
byte and the corresponding T3X payload. The source-aware host NFM/NWA decoder and
vehicle-index sanitizer test pass:7938 expanded vertices become3340 exact unique
vertices, preserving every48-byte source/GPU vertex after V flip, all24 batch
ranges and all five wheel groups. Useful GPU vertex/index bytes drop from381024
to176196; this is not a target FPS measurement. The actual native NVC reader
accepts the NPC entry and its source key, extent and body/wheel CRCs.

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps \
python tools/build_opening_police_car.py \
 --meshes /workspace/port-research/car-model-expansion-v2 \
 --candidates /workspace/port-research/all-car-candidates \
 --attributes /workspace/attachments/857a1856-1b3b-4be1-8a91-42f437324e6f/ATTRIBUTES.BIN \
 --carparts /workspace/port-research/v018-decoded/GLOBAL-GLOBALB_VM_NGC.BUN \
 --shared-textures /workspace/port-research/bmw/shared \
 --shared-textures /workspace/port-research/bmw/wheels \
 --shared-textures /workspace/port-research/shared-textures/globalb \
 --output /workspace/port-research/opening-police-car/fresh-output \
 --native-textures
```

Conversion uses the already cached Tex3DS image with networking disabled. It
stages new outputs and refuses an existing destination; original and prior
converted assets are not overwritten. Original/converted game payloads remain
private. No application SDK build, shared runtime edit, commit or push was made
by this subtask.
