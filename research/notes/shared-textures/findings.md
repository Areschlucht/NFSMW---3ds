# Shared texture packages recovered

## Input and results

- GLOBAL-GLOBALA.BUN: 89,588 bytes; one texture package containing 5 images.
- GLOBAL-GLOBALB.BUN: 225,776 bytes; two texture packages containing 98 and 19 images (117 total).
- GLOBAL-GLOBALB.LZC: 83,654 bytes; JDLZ stream that decompresses to **exactly all 225,776 bytes** of the supplied GLOBAL-GLOBALB.BUN. It supplies no additional image content.

All 122 images were exported to PNG with per-image source metadata and decoded RGBA SHA-256 hashes in `globala/manifest.json` and `globalb/manifest.json`. `contact-sheet.png` shows representative shared images, including the license plate, tire tread, intercooler, window damage, and interface icons. These are native game images decoded on the host, not 3DS screenshots.

## Package layout established for these files

- Texture package container: 0xB3300000.
- Header container: 0xB3310000. It contains package identification (0x33310001), eight-byte hash records (0x33310002), 124-byte generic texture records (0x33310004), and 60-byte GameCube platform records (0x33310005).
- Pixel-data container: 0xB3320000, with pixel chunk 0x33320002. The data base aligns the payload up to 128 bytes, skipping marker padding.
- Generic texture records contain a name at offset 12, hash at 36, image/palette offsets at 48/52, byte counts at 56/60, and width/height at 68/70. Each record's hash agrees with its entry in the separate hash table.
- The platform record's final big-endian word identifies the native GX format. Observed base formats are C4 (8), C8 (9), and CMPR (14). One GLOBALA record also has a high-bit flag (0x80000009), which is preserved in the manifest; its wider runtime meaning remains unresolved.

The supported C4/C8 palette path uses RGB5A3 entries. The decoded palettes, tile arrangement and offsets yield recognizable images. The parser rejects unsupported formats and out-of-bounds image/palette ranges; it does not infer formats from filenames.

## Validation

- Fourteen unit tests pass for RGB5A3 pixels/alpha, tile order, C4/C8 palette indexing, CMPR block order/interpolation/transparency, PNG integrity, and JDLZ literals/short and long backreferences/truncation/bounds.
- The real JDLZ stream output matches the supplied BUN byte for byte. The parsed compressed and uncompressed texture records and pixels also agree.
- Every one of the 122 exported PNGs was read back with Pillow and compared against the decoder's RGBA bytes and dimensions.
- A representative contact sheet was visually inspected.

Reusable tools are `tools/gc_texture.py`, `tools/nfs_jdlz.py`, and `tools/nfs_tpk.py` in the repository. `nfs_jdlz.py` is an independent bounded reader; the algorithm was checked against NI240SX/UCGT's Java reference, which credits MWisBest/OpenNFSTools:
https://github.com/NI240SX/UCGT/blob/master/src/fr/ni240sx/ucgt/compression/JDLZDecompress.java

Initial trial interpretations of the long-reference bit layout were rejected on invalid backreferences. The final reader uses the documented layout and passes the exact-output comparison. No expected hashes, signatures, or verification settings were altered to obtain a pass.

## Brake textures and next meaningful asset

None of the requested BRAKE_STYLE00–03, BRAKE_GLOBAL or GLOBAL_SKIN1 texture hashes is present in these packages. The general shared-car package is a separate, small file, CARS\\TEXTURES.BIN. ZDIR also contains complete BMWM3GTRE46 geometry/texture entries.

The reviewed Windows helper `tools/extract-bmw-assets.ps1` extracts four files from ZZDATA1.BIN, totalling 1,250,368 bytes:

| Path | Byte offset | Length |
| --- | ---: | ---: |
| CARS\\TEXTURES.BIN | 185,245,696 | 424,832 |
| CARS\\WHEELS\\TEXTURES.BIN | 189,673,472 | 344,704 |
| CARS\\BMWM3GTRE46\\GEOMETRY.BIN | 128,100,352 | 407,680 |
| CARS\\BMWM3GTRE46\\TEXTURES.BIN | 128,518,144 | 73,152 |

All four ranges have been checked against the directory hashes, archive index, sector offsets and byte lengths. Their contents are not yet local. The helper opens the source read-only and refuses to overwrite existing destination files. PowerShell execution has not been tested here.

The next target is a textured whole-car asset, subject to its geometry/material formats being supported or decoded. This is not a promise that the current brake-specific reader will accept it. No new viewer or device test is requested for the host-side texture work.
