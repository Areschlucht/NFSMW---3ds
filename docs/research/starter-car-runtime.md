# Original starter-candidate cars and traffic native assets

`tools/build_starter_cars.py` converts the supplied original assets into real
native car meshes, wheel rigs and texture dependencies. It does not relabel or
recolour the BMW as another car. No original source input, shared renderer,
main-loop, build script or existing converter is edited by this subtask.

## Concrete private output

Combined usable assets:
`/workspace/port-research/starter-cars/native-v2/`.

Each uppercase car directory contains `body.nfm`, `wheels.nwa`, and
`textures/<original-alias-hash>.t3x`. The PNG/raw intermediates and `scene.json`
are analysis inputs; a runtime installation needs only the NFM/NWA/T3X files.
`catalog.nvc` is the896-byte native catalog; its SHA256 is
`ce4260ad9a561dd3ded038291fefee469d7f1d57bf20529d97218bd5921eefdd`.
The neighbouring `catalog.json` is an authored provenance summary.

| ID | Frontend key | ecar key | Triangles | Batches | Textures | Source half extent |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| COBALTSS | 5a784095 | 5a784095 | 7191 | 41 | 25 | 2.296875 |
| GTI | 79054b53 | 79054b53 | 6984 | 38 | 22 | 2.109619140625 |
| IS300 | 5bff2fb0 | 5bff2fb0 | 6806 | 42 | 26 | 2.232177734375 |
| PUNTO | a6ee7a11 | a6ee7a11 | 7456 | 44 | 28 | 2.011474609375 |
| TRAFHA | none | a0c7bb59 | 900 | 12 | 9 | 1.914306640625 |

TRAFHA is an actual original traffic model. A zero frontend key deliberately
does not make it a purchasable player car. The four starter candidates match the
separately recovered FE_ATTRIB positive-Cost/UnlockedAt16 rows (`UnlockedAt` hashes
to60F99F57, matching the actual field). Actual original purchase
eligibility and starting cash are owned by the career investigation; a car
catalog entry never grants an unlock or infers a purchase preset.

GPU texture storage per currently loaded car is748032,796160,911872,928256 and
168448 bytes respectively. This excludes vertex buffers, CPU scene copies,
renderer bookkeeping and temporary atomic-switch allocations. The four starter
NFM files are approximately0.98–1.08MB each; TRAFHA is129968bytes. Do not preload
the whole roster on stock3DS merely because the files are available.

## Source and selection

The converter selects the concrete BASE and intact KIT00 parts from the existing
strict expanded exports. Original package rejection lists must be empty; invalid
parts are not silently dropped. All five packages meet that rule. Original
positions, S8/64 normals, source UVs, texture references and triangle corner order
are retained. Header transforms are not applied a second time to baked positions.

For all97 selected source parts, the converter independently reloads the pinned
original geometry payload and decodes the arrays/packets again. Every meaningful
exported field must match. The prior original-emitter packet verification cache
is tied to each original packet's SHA; no new emitter equivalence claim is made.
It preserves the source's B LOD for the four player models and C for TRAFHA.

The static source meshes are combined with four instances of that car's own
front tire model and the matching front/rear brake models when present. The
parent can animate the existing NWA groups0–4 without a new wheel API. Degenerate
zero-area triangles are omitted as in the existing native mesh pipeline.

The exact original `ecar.TireOffsets` supply each art mount and rolling radius,
with full original byte provenance. The axis adapter is source(X,Y,Z) to
viewer(X,Z,-Y); the left/right tire orientation follows the existing mirrored
wheel adapter. The complete original hub, chassis height, tire scaling, kit
offset, FE-compression and render-transform chain remains unproved. This is a
documented native art-mount adapter, not a complete1:1 wheel assembly. Physical
chassis/axle/CG parameters must not be substituted for these artwork values.

## Texture behavior and explicit remaining adapters

All110 generated T3X textures have their actual source RGBA compared against the
pinned Tex3DS tiled native payload, including image orientation and channels.
Source car-local textures and shared GLOBAL/CAR/WHEEL pixels are used directly.
Intact lamp aliases use the recovered original default-prefix selector with
enable/suppression flags0 and actual per-car headlight/brakelight images. No
unknown gray texture is silently emitted; unresolved references fail conversion.

Two explicit native adaptations remain:

- Side-window aliases use the actual shared WINDOW_FRONT pixels as an untinted
  binding. The original independent window tint/material producer is unported.
- Source SKIN1/SKIN2 aliases use the original `GLOSS_L1_COLOR01` white palette
  diffuse, read from the pinned original carpart source. This is a deliberate
  native preview colour, not the original purchase/default paint selection or
  generated indexed skin. Gloss is preserved in metadata and never used as
  diffuse opacity. Paint reflections, masks, gloss and final original lighting
  are not claimed to be reproduced by an8x8 constant diffuse image.

TRAFHA resolves all nine textures directly from original source images and needs
neither of those two fallback adapters. Dynamic lights, damaged part switching,
driver animation, original transparency/material states and whole-car handling
remain separate runtime work.

## Native catalog contract

`mw_vehicle_catalog.[ch]` validates a borrowed immutable NVC1 view. The header is
96bytes: magic/version/total/CRC, count at16, record offset96 at20, stride160 at24,
reserved0 at28, original ATTRIBUTES SHA32–63 and original carpart-source SHA64–95.
CRC covers bytes16 through the end. Both source digests are pinned to the supplied
USA originals. There are at most128 records.

Each160-byte record contains frontend key0, ecar key4, NFM payload CRC8, NWA
payload CRC12, normalization half extent16, reserved0 at20, uppercase safe ID24
(32bytes), display name56 (64bytes), original geometry SHA120 (32bytes), and eight
zero reserved bytes. Strings are terminated, zero padded and ASCII; IDs allow
only uppercase letters, digits and underscore. Records are sorted by ID; ecar
keys and nonzero frontend keys must be unique. Invalid inputs leave output views
unchanged. No decoder allocations or filesystem paths come from arbitrary text.

Use `mw_vehicle_catalog_find_frontend` for a career car choice and
`mw_vehicle_catalog_find_id` for the source traffic actor. Load
`cars/<id>/body.nfm`, `cars/<id>/wheels.nwa` and `cars/<id>/textures`, compare the
loaded body's payload CRC against `spec.body_crc`, and use `spec.half_extent`
instead of the BMW's normalization scale. Keep the catalog bytes alive. Selection
failure must retain the previous complete car rather than mix old rigs/textures
with a new mesh. The catalog intentionally supplies no invented physics tuning,
purchase price, original stock preset name or progress/unlock state.

## Validation and reproduce

Host ASan/UBSan tests pass actual `nfs_scene_decode` and `wheel_rig_decode` for all
five cars, body/rig CRC linkage, every T3X dependency, distinct car mesh identity,
wheel motion and catalog lookup. CRC/header/truncation, path-like IDs, NaN extent,
duplicate ecar keys, impossible counts and recomputed-CRC source corruption are
rejected. These tests do not establish 3DS rendering appearance or performance.

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps \
python tools/build_starter_cars.py \
 --meshes /workspace/port-research/car-model-expansion-v2 \
 --candidates /workspace/port-research/all-car-candidates \
 --attributes /workspace/attachments/857a1856-1b3b-4be1-8a91-42f437324e6f/ATTRIBUTES.BIN \
 --carparts /workspace/port-research/v018-decoded/GLOBAL-GLOBALB_VM_NGC.BUN \
 --shared-textures /workspace/port-research/bmw/shared \
 --shared-textures /workspace/port-research/bmw/wheels \
 --shared-textures /workspace/port-research/shared-textures/globalb \
 --car COBALTSS --car GTI --car IS300 --car PUNTO --car TRAFHA \
 --output /workspace/port-research/starter-cars/fresh-output --native-textures

cc -std=c11 -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined -no-pie \
 -Iinclude tests/test_starter_cars.c source_bmw/mw_vehicle_catalog.c \
 source_bmw/nfs_scene.c source_bmw/wheel_motion.c -lm -o /tmp/starter-cars-test
/tmp/starter-cars-test /workspace/port-research/starter-cars/native-v2/catalog.nvc \
 /workspace/port-research/starter-cars/native-v2
```

The SDK image is already pinned/cached and texture conversion runs with no
network. Original and converted game assets remain private; only authored tool,
codec, tests and this evidence report belong in Git.
