# Source-derived BMW native light bank

2026-11-03. `tools/build_vehicle_light_bank.py` now produces a concrete private
integration asset set from the verified career-start BMW preset and original
source textures. It does not modify the source scene, renderer or release ZIP.

The export first reuses `vehicle_lights_recovery.py`: SHA-pinned original DOL and
preset, source PNG pixel hashes, six existing alias batches, and three selector
states compared with original PowerPC execution. The three states are explicit
consumer inputs: no brake bits, both side-brake bits, and suppressed brake bits.
They are not a recovered provider or damage state machine.

## Native asset output

Private validated output:
`/workspace/port-research/vehicle-lights-recovery/native-bank-v1`.

- `targets/`: four source-derived T3X textures, source PNGs and uncompressed native
  payloads. Headlamp ON, brake OFF and brake ON are each 128×64; the explicit
  caller-provided WINDOW_FRONT is 8×8. There is no independently recovered BMW
  headlamp OFF producer/state in this export.
- `body.nfm`: retains the six original alias keys, texture slots, flags, batches,
  vertex data and source normals. Head/brake alias dimensions change from the
  former 8×8 placeholders to actual 128×64 source dimensions. CRC is recomputed.
- `wheels.nwa`: only the header's associated body CRC changes. Wheel pivots,
  radii, front flags and group payload remain byte-identical and pass the rig
  validator against the new body CRC.
- `default-alias-textures/`: six alias-named T3X files for a static no-brake seed.
  These are overlay inputs, not a complete car scene or SD-card installation.
- `light-bank.json`: source/asset hashes, alias descriptor patches, three exact
  alias-to-target state maps and explicit integration limits.

The four unique GPU RGBA8 payloads total **98,560 bytes**, excluding texture
objects, allocation overhead and any other car textures. All **24,640 texels**
match the independently implemented 8×8 Morton/ABGR conversion byte-for-byte.
The conversion uses pinned devkitARM image
`devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5`
and `tex3ds -f rgba8 -z none`. Each T3X contains exactly its compared native
payload after the uncompressed envelope. No vertical image flip is introduced;
the existing car-loader `uv[1]=1-uv[1]` convention is retained.

## Runtime seam

Current `source_rockport/rockport_main.c` loads each car alias into a separate
`Mesh.textures[]` object, checks dimensions against NFM, and directly binds that
object in the car batch loop. Consequently replacing PNGs alone is insufficient:
actual texture dimensions and corresponding NFM descriptors must agree.

For a static binding correction, clone the existing scene and overlay the new
body/rig plus six default alias textures. Preserve every other original scene
asset and update scene.json texture dimensions/missing-state and any packaging
checksums. Do not modify the recovered source scene in place.

For changing brake states, load the four unique target textures once and maintain
an alias-slot-to-texture-handle lookup. Keep ownership in the bank; alias references
must not cause duplicate C3D_TexDelete calls. Update only the alias target when
selector input changes. No per-frame file access, allocation, texture upload,
additional geometry or extra draw call is inherently needed. Loading both all six
static copies and a duplicate four-texture dynamic bank would waste memory.

The current NFM flags are deliberately preserved. Original strip materials mix
headlamp reflector, chrome, moldings, lamp glass and brake materials; shader and
blend semantics still need independent recovery. Source PNG alpha is uniformly
255 for these four inputs, which does not establish opaque original lamp glass.
No emissive, additive, bloom, halo or projected-light override is invented here.
The live WINDOW_FRONT tint binding, damage mask producers, reverse/emergency
states and other vehicles' own per-preset bindings remain separate work.

## Reproduce

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps \
python tools/build_vehicle_light_bank.py \
  --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
  --presets /workspace/port-research/v018-decoded/GLOBAL-GLOBALB_VM_NGC.BUN \
  --scene /workspace/port-research/bmw/scene-v0.18-source-normals \
  --texture-dir /workspace/port-research/bmw/textures \
  --texture-dir /workspace/port-research/shared-textures/globalb \
  --window-front-target 7b220ddf \
  --output /workspace/port-research/vehicle-lights-recovery/native-bank-v1
```

Use a fresh output directory; existing outputs are refused. The SDK container has
network disabled and mounts only this private output. Every source input remains
read-only. Exact original-selector comparisons require the existing Unicorn
Python dependency; `--skip-original-execution` explicitly records zero executed
comparisons and must not be reported as original execution verification.
