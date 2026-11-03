# Four brake meshes: executable-supported layout

This supersedes the unresolved alignment/count assumptions in the v0.1 probe notes. Earlier output is retained for comparison; the previous 21-face mesh was a subset of the first object.

## Executable evidence

Addresses refer to the supplied Speed.dol (SHA-256 recorded in the initial inspection). Text section virtual addresses map to file offsets by subtracting 0x80003000.

- At **0x8010E9A0–0x8010EA34**, the chunk consumer compares IDs 0x134800, 0x134801 and 0x134802. It aligns the metadata and descriptor payload pointers up to 16 bytes, and the data blob up to 32 bytes. These are `align_up(chunk+8,16/16/32)`, matching the addition/mask instructions. The descriptor table begins four bytes earlier than the old interpretation.
- At **0x8010E968–0x8010E99C**, the relocation loop reads a big-endian 16-bit record count at metadata offset 4, steps the descriptor table by 16 bytes, and adds the geometry data base to each record's leading pointer/offset.
- At **0x80117740–0x80117788**, the draw path reads descriptor byte 12, tests its 0x80 bit, uses byte 13 as the vertex format, and reads the display-list length at offset 14. Compiled records call the display-list function; otherwise the code begins a GX triangle strip (primitive 0x98) using the vertex count in byte 8.
- At **0x80117854–0x801178AC**, the raw format-0x16, low-flags-zero path reads four bytes per input vertex and sends five attribute indices, duplicating the third byte. The first byte is the position index. Compiled records in this sample begin with 0x9A, a big-endian vertex count, and five indices per vertex. All observed compiled records contain one strip plus padding.
- At **0x8010E440–0x8010E454**, the graphics format setup requests position attribute 9, XYZ components, signed-16 format 3, and 11 fractional bits for GX vertex format 2. The format-selection logic maps engine format 0x16 to GX format 2. Thus integer positions divide by 2048.

Capstone 5.0.6 was used for PowerPC disassembly. It does not correctly recognize all GameCube paired-single instructions; claims above are based on ordinary integer/control instructions and argument setup, rather than its misleading modern interpretations of paired-single opcodes. No decompiled source is claimed.

## Cross-checks against the data

| Object | Referenced positions | Nondegenerate triangles | Stored triangle count |
| --- | ---: | ---: | ---: |
| EBRAKE_KIT00_B | 22 | 27 | 27 |
| EBRAKE_STYLE01_B | 26 | 29 | 29 |
| EBRAKE_STYLE02_B | 28 | 32 | 32 |
| EBRAKE_STYLE03_B | 43 | 41 | 41 |

All draw descriptors are covered, including the raw strips omitted by v0.1. Degenerate triangles are skipped. No assumption is made about unreferenced padding between the vertex array and subsequent arrays.

For every axis of every object, the stored floating-point bounding box extends beyond the decoded positions by 0.01000–0.01049 units on each side. This is consistent with a 0.01 bound margin plus less than one 1/2048 quantization step. Previously interpreting this margin as a scale mismatch was misleading.

Remaining unknowns include normals/UV conversion, material semantics, texture resolution and alpha behavior, and other engine vertex formats. The first rotor surface is a quad; filled rendering without its texture shows the quad rather than a circular textured appearance. The current material shading is generated for inspection.

## Validation and artifacts

`models.json` and four OBJ files were exported using the chunk-driven Python reader. The C decoder independently matches all positions and faces. Native tests exercised 48 shaded/wireframe render cases and malformed input under ASan/UBSan. `preview.png` contains native C renderer output, not hardware captures.

Version 0.1 was reported by the user to run well on New 3DS with extra clock/cache disabled. Version 0.2 has compiled successfully but awaits device testing. No claim about Old 3DS or full-game performance follows from either version.
