# Original destination marker art and bounded native overlay

Five authentic original mini-map textures are available as a small RGBA native
sidecar. This provides recognizable map markers for the exported destination
positions. It does not recover the original 3D trigger particle system.

## Sources and bindings

The exporter pins the supplied USA GameCube inputs:

| Input | SHA256 |
| --- | --- |
| GLOBAL-INGAMEA.BUN | 0e3543f534cb94b113168a1b5f6b7a7224b32d12986fb18253b937f16c293d79 |
| Speed.dol | 33c5eae699f871beac059b6932475cad5e9f610bb2b2298e046d043757b94166 |

The original texture descriptors and pixels are decoded through `nfs_tpk.parse`.
Full original names independently reproduce the descriptor hashes with the
original uppercase, seed-FFFFFFFF, multiply-by-33 name hash. Descriptor names
are limited to 23 characters; the point-to-point descriptor is therefore
`MINIMAP_ICON_POINT_TO_P`, while its full hashed name appears below.

| NFD1 kind | Original race type | Original texture | Hash | Dimensions |
| --- | --- | --- | --- | --- |
| 1 safehouse | ignored | MINIMAP_ICON_SAFE_HOUSE | 2CFD5273 | 16×16 |
| 2 customshop | ignored | MINIMAP_ICON_CHOP_SHOP | 1CE551D4 | 16×16 |
| 3 carlot | ignored | MINIMAP_ICON_CAR_LOT | 12BB8395 | 16×16 |
| 4 race | 0, sprint/point-to-point | MINIMAP_ICON_POINT_TO_POINT | 571CD206 | 8×8 |
| 4 race | 1, circuit | MINIMAP_ICON_CIRCUIT | 25559384 | 16×16 |

The unchanged original location selector at 80162B14..80162BA8 directly binds
carlot to 4EAEE18B, safehouse to 0ED39F69 and customshop to 0CF07089. These are
the corresponding authentic 32×32 `WORLD_CARLOT`, `WORLD_SAFEHOUSE` and
`WORLD_CHOP_SHOP` textures in INGAMEA. The selector at 80162A78..80162B14 binds
original race mode 0 to `MODE_ICON_SPRINT` (2521E5EB) and mode 1 to
`MODE_ICON_CIRCUIT` (E9638D3E), whose 64×64 textures are in GLOBALB.

Those consumers establish the original location/race categories. The table's
assignment of corresponding authentic **mini-map** glyphs is the explicit 3DS
overlay contract. A direct mini-map-specific consumer for these five hashes
has not been recovered. Unknown race modes receive no substitute glyph.

INGAMEB also contains 32×32 `FX_WORLD_SAFEHOUSE` (86DA72E6),
`FX_WORLD_CHOP_SHOP` (84F74406), `FX_WORLD_CARLOT` (09B91E28) and `FX_MODE_*`
textures. Their names alone do not prove an emitter/animation binding. No 3D
rotation, glow, trigger emitter or original particle behaviour is claimed here.

## NFI1 native asset

`tools/build_destination_icons.py` emits `destination-icons.nfi`, five source
PNGs and `manifest.json`. The manifest includes original descriptors, decoded
RGBA hashes, alpha coverage, source hashes and original consumer-window hashes.
Pixels retain original dimensions and colors. No resampling is performed.

The file is exactly 4608 bytes; integers are little endian. Its 96-byte header is:

| Offset | Field |
| ---: | --- |
| 0 | NFI1 magic |
| 4 | version 1 |
| 8 | total byte count, 4608 |
| 12 | CRC32 of all bytes from offset 96 to EOF |
| 16 | record count, 5 |
| 20 | record offset, 96 |
| 24 | pixel offset, 256 |
| 28 | record size, 32 |
| 32 | 32-byte original DOL SHA256 |
| 64 | 32-byte original INGAMEA SHA256 |

Five contiguous 32-byte records follow, in the table's order. Each contains
eight uint32 values: NFD kind, original race type (FFFFFFFF for non-races),
original texture hash, width, height, pixel offset, pixel byte count, reserved 0.
Contiguous, tightly packed RGBA8 pixel arrays follow. The native reader checks
the exact expected records, dimensions, offsets, sizes, reserved values, source
hashes, total length and payload CRC before publishing a borrowed immutable view.

`mw_destination_icon_blit` writes standard alpha-over into a tightly packed RGB8
canvas. Its input x/y is the glyph center; clipping uses 64-bit coordinates,
including INT_MIN/MAX inputs. It allocates no memory. Invalid canvas sizes and
unknown kind/race type fail without writes. A known glyph entirely outside the
canvas succeeds without modifying pixels. The validated asset must remain alive
and immutable while the view is used.

## Reproduction and validation

```sh
PYTHONPATH=tools python tools/build_destination_icons.py \
 --ingamea /workspace/attachments/3716fced-9974-45db-bfd3-3d43e8d65ca1/GLOBAL-INGAMEA.BUN \
 --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
 --output /workspace/port-research/free-roam-destinations/icons-v1

cc -std=c11 -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined -g \
 -Iinclude source_bmw/mw_destination_icons.c tests/test_destination_icons.c \
 -o /tmp/test_destination_icons
/tmp/test_destination_icons \
 /workspace/port-research/free-roam-destinations/icons-v1/destination-icons.nfi
```

The exporter requires a fresh output directory. The current private artifact is
`/workspace/port-research/free-roam-destinations/icons-v1/destination-icons.nfi`,
SHA256 `e39ef5aa548716d93ee2c8179a0decc44613852da124e0d9bd95a7ca600ad408`.

Host ASan/UBSan checks pass for all five original glyphs, alpha coverage, 35
independent clipped alpha comparisons, guarded output buffers, unsupported
types, extreme coordinates, truncated inputs, invalid headers/source hashes,
payload corruption and all 40 record-field mutations with recomputed CRCs.
Failed decode leaves the caller's previous view unchanged. This check does not
claim emulator or 3DS rendering validation; integration owns projection and the
map refresh path.

## Safehouse return boundary

The destination catalog retains explicit original respawn position/rotation
records. Original `JumpToSafeHouse` callback 801C5F00..801C5F34 opens mode 2
`MainMenu_Sub.fng`; it contains no nearest-house selection or position copy.
The later world-return selection is not proved by this callback. Frontend entry
may therefore be implemented independently, while relocation must remain a
documented missing transition until its original consumer is recovered. No
nearest-house warp is introduced by the marker code.
