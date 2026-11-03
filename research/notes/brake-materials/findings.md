# Texture-coordinate and material investigation

This work extends the offline reader/exporter while viewer v0.2 is being tested. It does not change the v0.2 executable or test ZIP.

## Reference tables and name candidates

Chunk 0x134012 stores eight-byte texture-reference records; chunk 0x134013 stores separate eight-byte material/shader-reference records. The executable object loader at 0x800F7F18–0x800F7FD0 installs these tables at object offsets 0x2C and 0x3C respectively. The draw-submission code uses descriptor bytes 10 and 11 to index those tables. Descriptor byte 9 selects a draw group and is not itself a texture-table index.

The existing multiply-by-33, initial-0xFFFFFFFF hash produces these reference matches:

| Hash | Name candidate | Evidence |
| --- | --- | --- |
| C6578694 | BRAKE_STYLE00 | Constructed name matches the first mesh's texture reference |
| C6578695 | BRAKE_STYLE01 | Same pattern for the next mesh |
| C6578696 | BRAKE_STYLE02 | Same pattern for the next mesh |
| C6578697 | BRAKE_STYLE03 | Same pattern for the next mesh |
| 17F9F794 | BRAKE_GLOBAL | Constructed name matches a texture reference shared by all four meshes |
| DDA11455 | GLOBAL_SKIN1 | Name occurs in the executable and hashes to the reference |
| F0A43B67 | BRAKEDISC | Constructed name matches a material/shader reference |

Hash matches support these labels but do not independently prove uniqueness. Other shader-reference names remain unresolved. Material names and texture names are separate; finding BRAKEDISC does not locate a texture image with that name.

## UVs and normals

For each aligned metadata structure:

- Offset 0x0C is the position-array offset within the aligned geometry blob.
- Offset 0x10 is the candidate normal-array offset. Entries have three signed bytes and a zero padding byte; division by 64 gives lengths within 0.987–1.007 for this sample. Normal routing still requires independent graphics-state verification.
- Offset 0x14 is the color-array offset; this sample has a white four-byte value.
- Offset 0x18 is the texture-coordinate-array offset. Pairs are big-endian signed-16 values divided by 4096, consistent with the executable's GX texture-format setup. The first object's quad maps to the four corners of the unit square.

The initial investigation briefly tested offset 0x10 as UV data. That interpretation was rejected: it produced implausible coordinate patterns and actually matched the near-unit packed normal vectors. The exported files use offset 0x18 for UVs.

Raw format-0x16 records have four input bytes per corner. Compiled strips have five, including a duplicated attribute index. The first index selects a position, the second a candidate normal, and the last selects a UV. Strip winding reversal is applied to all corner attributes together. OBJ export now includes vt/vn entries and separate groups labeled with reference hashes.

| Mesh | Referenced UV pairs | Candidate normals |
| --- | ---: | ---: |
| EBRAKE_KIT00_B | 29 | 37 |
| EBRAKE_STYLE01_B | 10 | 46 |
| EBRAKE_STYLE02_B | 10 | 48 |
| EBRAKE_STYLE03_B | 13 | 64 |

Checks confirm all per-corner UV/normal indices fit their arrays, normal lengths are plausible, and positions/triangle lists are unchanged from the validated v0.2 exports. No actual image texture has been recovered or rendered.

## Missing image data and smallest next transfer

ZDIR maps CARS\\BRAKES\\TEXTURES.BIN to a **zero-length** entry. This does not prove the images are absent from the game; they may be in a shared resident texture package. The following three candidate shared files can be extracted from ZZDATA1.BIN in less than 400 KB total:

| Candidate source | Byte offset | Byte length |
| --- | ---: | ---: |
| GLOBAL\\GLOBALA.BUN | 82,796,544 | 89,588 |
| GLOBAL\\GLOBALB.BUN | 269,469,696 | 225,776 |
| GLOBAL\\GLOBALB.LZC | 269,697,024 | 83,654 |

These ranges have been independently checked against ZDIR. Their contents are **not yet available locally**, and their relationship to the brake textures remains a hypothesis until inspected. Archive prefixes currently on disk contain multimedia data, not these ranges. No full archive transfer is needed to investigate the candidates.

`/workspace/NFSMW---3ds/tools/extract-shared-textures.ps1` copies these ranges read-only into `shared-texture-samples`, refuses existing destination files, and validates the reported archive size first. PowerShell is unavailable in this environment, so the helper is reviewed and its ranges verified but it has not been executed on Windows.
