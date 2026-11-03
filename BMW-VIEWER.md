# Menu and BMW garage prototype v0.5

This is a static rendering prototype using decoded NFS Most Wanted GameCube assets. It is **not a playable port**. It contains 15 BMW body/interior/window/light parts, 5,248 drawn triangles and 16 texture references. Nine references resolve to recovered images; seven use plain gray placeholders. The main BMWM3GTRE46_SKIN1 paint/vinyl image is missing.

There are no wheel instances, playable steering/physics, tracks, traffic or game audio. A separate host-tested kinematic driving controller exists, but it is not connected to this application or a world. Wheel/driver placement, the paint-generation system, material behavior and some light textures are unresolved. Several original shader effects are approximated by basic texture modulation and inspection lighting. Transparency is sorted per material batch, so it can differ from the original game's renderer.

## Original Rockport data required

**Update:** the initial three samples below have been received and inspected.
The original navigation graph and streaming index are decoded. Selected road
surfaces now run in the separate [v0.6 driving prototype](ROCKPORT-PROTOTYPE.md). See [Rockport findings and the next targeted extraction](ROCKPORT.md).

The menu opens the garage, controls and a page explaining that Rockport is unavailable. The user requires original Rockport data only; no generated road is included. This build is not a playable game.

On Windows, open `tools/extract-rockport-map.ps1` in a text editor and copy its contents. Open PowerShell in the folder containing the original `ZZDATA1.BIN` and `ZZDATA3.BIN`, paste the script and press Enter. It checks archive sizes, reads the archives without modifying them and refuses to overwrite existing outputs. Upload the three files from `rockport-map-samples`:

- `L2RA.BUN` (982,848 bytes)
- `TrackMaps.bin` (16,634,816 bytes)
- `STREAML2RA-first8MiB.BUN` (8,388,608 bytes)

These are identified archive entries plus a bounded stream prefix, totaling 26,006,272 bytes. The prefix is for initial format/index research, not a complete streamed map; further ranges may be needed. Recovering these assets does not by itself implement collisions, race logic, traffic or the original engine.

For host-side research, run:

```sh
python3 tools/inspect_map_samples.py rockport-map-samples /path/to/ZDIR.BIN > rockport-inspection.json
```

This read-only tool validates directory records against the supplied archive sizes and resolves each requested filename hash uniquely. It checks sample lengths and records SHA-256 checksums, original offsets and bounded chunk headers. It distinguishes the intentionally truncated stream prefix from declarations outside the original entry. Only container types observed in the existing car/texture assets are traversed; unknown track payloads remain opaque. Size checks and checksums do not prove that a sample contains valid roads. No map geometry or collisions are decoded by this tool.

## Install

Extract the complete ZIP to the SD card root. It installs separately from the brake viewer:

```text
/3ds/nfsmw-bmw-viewer/nfsmw-bmw-viewer.3dsx
/3ds/nfsmw-bmw-viewer/nfsmw-bmw-viewer.smdh
/3ds/nfsmw-bmw-viewer/body.nfm
/3ds/nfsmw-bmw-viewer/textures/*.t3x
```

Keep all texture sidecars and the model file together. The bottom screen reports an error if the scene fails its integrity/bounds checks, if a texture is missing, or if GPU initialization fails.

| Control | Action |
| --- | --- |
| Up/Down, A | Choose/open a main-menu item |
| Circle Pad / D-pad (garage) | Rotate |
| A | Pause/resume automatic rotation |
| L / R | Zoom out/in |
| X (garage) | Reset view |
| B / START (garage or information page) | Return to main menu |
| SELECT | Switch textures/solid shading |
| START (main menu) | Exit |

The program does not enable New 3DS-specific clock/cache settings. Console performance must not be inferred from emulator performance.

## Build and asset conversion

`bash tools/build_bmw.sh` builds the separate BMW executable using the pinned offline devkitPro container. The existing brake build remains `bash tools/build.sh`.

The conversion workflow is host-side:

1. `tools/nfs_tpk.py` parses the native GameCube texture packages. Individually compressed texture records can use JDLZ or EA HUFF. HUFF conversion currently uses an optional, checksum-pinned reference routine inside bounded Unicorn x86 emulation (`--huff-reference`), never as native host code. The reference bytes are not included in the 3DS application or repository.
2. `tools/decode_brakes.py --lod B` also supports the BMW's observed mixed 8/16-bit position/normal/color/UV indices. The selected B-level models' triangle counts match their stored headers. Other LODs are not claimed fully supported: INTERIOR_D still has an unresolved count difference.
3. `tools/build_bmw_scene.py` selects static body parts, validates their baked positions against stored part bounds and converts source X-length/Y-width/Z-up coordinates to the viewer's Y-up basis. It does not apply the header matrices again: that moved light parts away from the body in an emulator check. It records unresolved textures rather than substituting unrelated game images.
4. `tex3ds -f rgba8 -z auto -o output.t3x input.png` converts decoded images and placeholder images for the 3DS. Preserve the hash-based filenames.
5. `tools/package_bmw.py` assembles the executable, scene and texture sidecars into an installation ZIP after integrity checks.

The NFM scene format has a 32-byte header (magic/version, vertex/batch/texture counts, payload size, CRC32 and reserved word), followed by fixed-size texture/batch records and expanded position/normal/UV float32 vertices. The runtime validates sizes, counts, CRC, texture dimensions, batch ranges and finite normalized positions/normals/UVs before upload. It does not parse the original DOL or large game archives on the console.

Native ASan/UBSan checks exercise the converted-scene loader, including corrupt/truncated files, invalid dimensions/batches, NaN coordinates and cleanup. Shader assembly and strict compiler checks are also required. The host preview is a reference rendering of the same converted scene; it is not evidence of GPU execution. Emulator/device outcomes are recorded separately in the research reports.

The packaged v0.4 build has now run in **Azahar 2126.2**, using a virtual SD card and Mesa software OpenGL. Startup, textured rendering, pause, rotation, texture toggle, zoom, reset and START exit were checked. Image comparisons confirmed that toggles/rotation/zoom change output and that reset restores the identical paused view. This is emulator validation, not a physical New/Old 3DS performance test.

No further hardware test is needed merely for a host-side parser change. Prefer emulator checks for intermediate startup/rendering/control regressions, and request console tests only for meaningful visible changes or hardware-specific questions.

The v0.5 build also passed Azahar checks for the main menu, unavailable-Rockport page, garage entry, pause/texture toggle, controls page, return navigation and clean exit. Native ASan/UBSan checks pass for menu state transitions and the separate driving controller (acceleration, braking, reverse, steering, timestep consistency and invalid inputs). The controller is not yet gameplay.
