# NFS Most Wanted → 3DS research

## Rockport driving prototype v0.16

v0.16 targets the measured rendering/simulation costs and the handbrake feel.
The world now has a dedicated baked-colour shader (28→13 source instructions)
and a 36-byte GPU vertex layout (25% smaller). Car lighting retains its original
prototype path. Start and dense-view captures match v0.15 pixel for pixel.

A bounded road index reduces average centroid candidates from 5,483 to 80.88,
with 35,254 real-map query comparisons matching the linear path exactly.
Handbrake taps now initiate slides that persist after release; rear wheels
lock while R is held, and countersteering/gradual grip recovery straighten the
car. CPU logic time and signed slip angle are added to the HUD.

The user reports v0.15 at 18–40 FPS on stock New 3DS, versus 50–60 FPS with
804 MHz and L2 enabled together, with GPU time reaching 22 ms in a crowded view.
There is no v0.16 hardware result yet. Native sanitizer tests, 63 Python tests,
strict ARM builds and emulator checks pass. The map, road asset and textures
are unchanged from v0.15.

This remains a partial native asset-based prototype with provisional handling.
Original tire/suspension/engine simulation, scenery/camera collision, full
materials, traffic/police, races, audio and Old 3DS validation remain unfinished.
See [installation, controls and limitations](ROCKPORT-PROTOTYPE.md).

## Original Rockport map research

The supplied `L2RA.BUN`, stream prefix and `TrackMaps.bin` now validate. The
host decoder recovers 997 indexed stream sections and the original navigation
graph (4,385 nodes, 6,538 connections); all adjacency references match. The
texture reader also decodes 297 track-map images. The subsequent world-sector samples are received; selected road surfaces now decode
for v0.6. Original collision-table decoding remains unresolved. See
[ROCKPORT.md](ROCKPORT.md) for findings and commands.

## Earlier prototype: menus and BMW garage v0.5

See [BMW-VIEWER.md](BMW-VIEWER.md) for the separate textured BMW body prototype and installation/build details. It renders 15 decoded body/interior/window/light parts (5,248 triangles). Wheels, the generated paint skin and some light images remain unresolved. The main menu now opens the garage, controls and an unavailable Rockport page. No gameplay is implemented. A separate tested kinematic controller is not integrated with a track. Only original Rockport map data is in scope; see [the Windows extraction helper](tools/extract-rockport-map.ps1) and [sample instructions](BMW-VIEWER.md#original-rockport-data-required).

Azahar 2126.2 now runs in a local container with a virtual display, virtual SD and software OpenGL. The BMW build passed startup/rendering, pause, texture toggle, rotation, zoom/reset and START exit checks there. Routine intermediate checks should use this setup; further console tests should be reserved for meaningful milestones or hardware-specific issues. Emulator speed is not a device-performance measurement.

## GPU viewer v0.3 — successful New 3DS test reported

Version 0.3 replaces the live CPU rasterizer with a **Citro3D/PICA200 rendering path**. Model rotation, perspective projection and inspection lighting run in the vertex shader; triangle rasterization and depth testing run on the GPU. The CPU decodes and normalizes the models and prepares vertex buffers when the selected model or display mode changes. No geometry file is re-read during rotation.

Download `nfsmw-brake-viewer-v0.3.zip`, extract to the SD card root, and replace the viewer files. Installation paths and controls below are unchanged. The bottom screen should say **NFS MW GPU viewer v0.3**. The older v0.2 ZIP remains available for comparison or rollback.

The GPU has no native line primitive. Wireframe mode draws narrow triangle ribbons along the model's edges, so line thickness varies with zoom and view angle. Both modes use generated flat face normals for inspection lighting; they do not reproduce the game's materials. The CPU renderer is retained for native reference tests but is not the default live renderer.

Version 0.3 still has **no image textures, transparency, gameplay or New 3DS-specific acceleration settings**. Its purpose is to validate a native GPU path before attempting larger assets. No frame-rate improvement or full-game performance is claimed.

Validation: shader assembly and a complete devkitARM build pass with `-Wall -Wextra -Werror`. Native ASan/UBSan tests cover buffer capacity, all four models in both GPU preparation modes, finite bounds/unit normals, a known triangle, and invalid inputs. The existing decoder/reference-render tests also pass. The user subsequently reported that v0.3 runs as well as the prior viewers on New 3DS. Individual controls, resume behavior and measured performance were not separately logged.

User feedback confirms **v0.2 ran as well as v0.1 on the available New 3DS**. No Old 3DS test is available. The user previously reported v0.1 with the 804 MHz clock and L2 cache disabled; this app does not change those settings.

## Geometry viewer v0.2

This prototype reads all four brake meshes in the supplied 6,080-byte geometry sample. It displays shaded triangles with a depth buffer or a wireframe. It does not execute `Speed.dol` and contains no gameplay.

| Model | Referenced positions | Nondegenerate triangles |
| --- | ---: | ---: |
| EBRAKE_KIT00_B | 22 | 27 |
| EBRAKE_STYLE01_B | 26 | 29 |
| EBRAKE_STYLE02_B | 28 | 32 |
| EBRAKE_STYLE03_B | 43 | 41 |

All four triangle counts match their object headers. The reader follows chunk boundaries and the executable loader's alignment rules. It supports the observed format-0x16 raw and compiled strips. Coordinates use the signed-16, 11-fractional-bit position format configured by the executable. The camera separately auto-fits each model for display.

These are complete position/triangle sets for the four decoded objects under the supported format; materials, normals, UV conversion, transparency and textures are still missing. In shaded mode, a large surface may appear square: a flat textured quad cannot acquire a circular appearance until its texture/alpha behavior is decoded. Shading is generated by the viewer and is not the game's lighting.

## Installation

Extract `nfsmw-brake-viewer-v0.2.zip` to the SD card root and replace the previous viewer files when prompted. The installation paths remain unchanged:

```text
/3ds/nfsmw-brake-viewer/nfsmw-brake-viewer.3dsx
/3ds/nfsmw-brake-viewer/nfsmw-brake-viewer.smdh
/3ds/nfsmw-brake-viewer/brakes-geometry.bin
```

Open the viewer in Homebrew Launcher on an already configured console. The bottom screen must say **v0.2**. It starts in shaded mode with automatic rotation. A missing or unsupported asset displays an error instead of rendering.

| Control | Action |
| --- | --- |
| X / Y | Next / previous model |
| SELECT | Toggle shaded / wireframe |
| Circle Pad or D-pad | Rotate |
| A | Pause / resume rotation |
| L / R | Zoom out / in |
| B | Reset view |
| START | Return to Homebrew Launcher |

The executable targets baseline 3DS ARMv6K and does not enable New 3DS clock/cache features. User reports confirm v0.1 and v0.2 run well on New 3DS. Old 3DS compatibility remains untested. The v0.2 CPU renderer is an inspection tool, not the eventual game renderer or a full-game performance benchmark.

## Build and checks

Use the existing isolated checkout; no worktree is needed. Run:

```sh
bash tools/build.sh
```

The helper uses the digest-pinned official devkitPro Docker image already downloaded in this environment. It builds offline with two workers. The artifact is `nfsmw-brake-viewer.3dsx`.

To run native checks with the extracted sample:

```sh
cc -std=c11 -Wall -Wextra -Werror -g -fsanitize=address,undefined \
  -Iinclude source/brake_mesh.c source/brake_render.c source/brake_gpu_mesh.c tests/test_mesh.c \
  -lm -o /tmp/nfsmw-test-mesh
/tmp/nfsmw-test-mesh /path/to/brakes-geometry.bin
```

Checks performed for v0.2:

- Native decoder/renderer passed AddressSanitizer and UndefinedBehaviorSanitizer checks, including truncated/oversized files, corrupted chunks/descriptors, invalid indices, and one mutation at every byte position of the sample.
- All models rendered in shaded and wireframe modes across six views/zoom settings each (48 native render checks). These use the same renderer compiled into the 3DS executable.
- All decoded faces and coordinates match the separately implemented Python reader in `tools/decode_brakes.py`.
- devkitARM GCC 16.1.0 compilation/linking passed with `-Wall -Wextra -Werror`.
- Screenshots of native renderer output were visually inspected. These are not screenshots from a 3DS or emulator.
- The user reports v0.2 works as well as v0.1; individual controls and measured frame rate were not separately logged.

Package a tested build with the exact user-provided sample:

```sh
python3 tools/package.py /path/to/brakes-geometry.bin
```

The packaging helper verifies the sample SHA-256 and creates the local installation ZIP. No game assets are embedded in tracked source, and no files have been pushed or published remotely.

## Next milestone

Continue toward a textured whole-car asset. The offline reader exports UVs and candidate normals. The supplied shared GLOBALA/GLOBALB files now decode to 122 images, but do not contain the brake texture hashes. The new helper `tools/extract-bmw-assets.ps1` extracts the separate shared-car/wheel textures and the BMWM3GTRE46 geometry/textures, totalling about 1.2 MB. Intermediate checks should run here; request another device test only for a meaningful visible milestone or a specific hardware issue. Other geometry formats, larger models, game systems and a complete port remain substantial outstanding work.

`tools/gc_texture.py` decodes tiled GameCube RGB5A3 pixels using only Python's standard library. It successfully extracts the 96×32 image from the supplied `opening.bnr`. Pixel/alpha vectors, tile order, malformed inputs and PNG integrity have five passing tests (`python3 -m unittest discover -s tests -p test_gc_texture.py -v`). This validates one native pixel format and its tiling; it does not locate or decode NFS texture packages. No new viewer release is required for this host-side work.

The texture tools now also support indexed C4/C8 (RGB5A3 palette) and CMPR images, plus bounded JDLZ decompression. `tools/nfs_tpk.py` extracts observed GameCube texture packages to PNG and records a manifest. Fourteen Python tests pass (`python3 -m unittest discover -s tests -p 'test_*.py' -v`). The real GLOBALB LZC decompresses exactly to the supplied BUN, and all 122 PNGs pass independent pixel readback. This remains an offline asset workflow; no image textures have yet been integrated into the GPU viewer.
