# BMW geometry, compressed textures and static 3DS body scene

## Newly supplied assets

- BMWM3GTRE46-GEOMETRY.BIN: 407,680 bytes; 73 objects including alternate detail levels and damage parts.
- BMWM3GTRE46-TEXTURES.BIN: 73,152 bytes; 8 images (4 HUFF, 4 JDLZ).
- CARS-TEXTURES.BIN: 424,832 bytes; 465 images (353 HUFF, 112 JDLZ).
- WHEELS-TEXTURES.BIN: 344,704 bytes; 82 images (all HUFF).

The texture files use compressed-record chunk 0x33310003 rather than the uncompressed 0x33310004/5 pair. Each compressed record is 24 bytes: key, package-relative packet offset, packed size, unpacked size and two additional words. Each unpacked packet ends with the 124-byte generic texture record and 60-byte platform record. Its preceding bytes contain image/palette data. Offsets in the reconstructed generic record refer to the original uncompressed allocation, so extraction rebases them per packet. Record/hash-table/reconstructed-key agreement and image/palette bounds are checked.

JDLZ packets reserve up to two trailing flag bytes which may be nonzero; these are not decoded output. The reader now handles that encoder behavior while retaining declared compressed/uncompressed sizes and backreference bounds. A regression test covers valid flag tails and rejects excessive nonzero trailing data. The original GLOBALB LZC-to-BUN exact comparison remains valid.

## HUFF conversion aid

The optional HUFF reader uses bounded Unicorn x86 emulation of Luigi Auriemma's QuickBMS EA HUFF reference routine. Its downloaded reference C file is SHA-256 pinned (`ea1529ff9db11d982868252256e8d848ea878b92210992338b66f8dd40d16f6d`) and kept outside the repository at `/workspace/toolchains/references/ea_huff.c`. It is not run natively or shipped in the 3DS build. Memory mappings, input/output limits, instruction/time limits and intercepted memset/cookie calls isolate the conversion. The portable C scene loader and 3DS runtime do not depend on this emulator.

Successful decoding is supported by all reconstructed record hashes, dimensions, valid image/palette bounds and recognizable image output. There is no independently supplied uncompressed HUFF pair, so an independent full HUFF algorithm comparison remains unperformed.

## Geometry

The executable's draw handlers establish mixed index widths: descriptor low bits 0x10/0x08/0x04/0x02 select 16-bit position/normal/color/UV indices. Compiled strips duplicate the color attribute. The BMW uses flags 0, 12, 28 and 30, optionally ORed with 0x80 for compiled lists. All use engine vertex format 0x16.

The reader now supports those widths and explicit LOD selection. All 25 B-level objects decode with matching stored triangle counts. The all-LOD read still rejects INTERIOR_D: its count remains 97 after removing repeated-index triangles versus 98 declared. That failure is preserved, rather than treating an unverified LOD as supported. The body scene explicitly selects B-level parts.

Object names start at header payload offset 160, not 159. The old brake labels accidentally included the final byte of a preceding field (such as the stray E prefix). Reader names are corrected without changing the brake geometry.

The static scene includes 15 B-level parts, excluding alternate damage, driver, tires and brake instances whose placement has not been established. It draws 5,248 nonzero-area triangles. Source X-length/Y-width/Z-up axes are converted to a Y-up display basis and normalized once for the whole scene.

An initial attempt to apply header matrices moved some lights away from the car, visible in the emulator. All selected raw positions already fit their stored part bounds. The exporter therefore retains those baked positions and does not apply those matrices again. Their complete runtime semantics remain unresolved.

## Texture/material limits

Sixteen texture references are used in the static body scene. Nine resolve to recovered images; seven are explicit solid-gray placeholders. The main missing paint key is DE3AD3C6, matching BMWM3GTRE46_SKIN1. No familiar blue/white skin has been fabricated. The original paint/vinyl generation path and several light references remain unresolved. Material behavior, lighting and transparency are approximate inspection rendering.

Wheels are not assembled; the tire mesh is local to its attachment frame and wheel placement has not been established. The model preview is not a complete drivable car or a game port.

## Build and checks

The separate `source_bmw` application builds with `tools/build_bmw.sh` using libctru, Citro3D and Citro2D's Tex3DS import support. Decoded PNGs are converted to T3X using the pinned devkitPro tex3ds tool. The app loads the converted NFM scene and hash-named texture sidecars from its own SD folder, leaving the brake viewer separate.

- Strict shader/GCC build passes.
- Fifteen Python texture/JDLZ tests pass.
- Native ASan/UBSan tests pass for the NFM loader and the existing brake decoder/render/buffer preparation.
- NFM runtime checks cover header/count/length agreement, CRC, batch coverage/ranges, texture dimensions/flags and finite normalized vertex data.
- The software reference render is `preview.png`; it is not a GPU screenshot.
- Actual Azahar screenshots are `emulator-*.png`, including `emulator-bmw.png`.
- Emulator startup, textures, pause, rotation, zoom, texture/solid toggle, exact reset-image restoration and START exit passed. The corrected build is repackaged after those checks.

The user does not need to perform another intermediate hardware test now. Emulator validation does not establish physical 3DS frame rate, Old 3DS compatibility, sleep/resume behavior or full-game performance.


## Menu prototype v0.5

Original Rockport data only, per user instruction. No generated road. Strict devkitARM build passes. Main/menu transitions, unavailable track page, garage pause/texture switch, controls, back and clean exit were checked in Azahar 2126.2; screenshots are emulator-menu-*.png. Menu and independent kinematic controller pass native ASan/UBSan checks. Controller is not connected to rendering, collision or a world. Rockport decoding remains blocked on the original samples listed in tools/extract-rockport-map.ps1 and BMW-VIEWER.md. The stream prefix may require subsequent extraction of further original ranges.


## Rockport inspection preparation

Added tools/inspect_map_samples.py: read-only sample-length/directory/hash validation, SHA-256 reporting and bounded chunk header inspection with explicit stream-prefix handling. All 1,363 supplied ZDIR records pass archive-selector, bounds, sorted-hash and combined-sector checks. Each requested map filename hash matches uniquely, confirming the existing PowerShell extraction ranges. Full BMW geometry and GLOBALB bundles plus their first 1,024-byte prefixes pass the chunk inspector. Python suite: 24 tests pass, including malformed directories, ambiguous hashes, logical-parent overruns, cut headers/payloads and sample-length mismatch. Unknown track chunks remain opaque. No actual Rockport samples are present yet; no map or playable-game progress is claimed.
