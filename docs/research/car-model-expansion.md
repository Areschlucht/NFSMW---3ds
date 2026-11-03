# Expanded original car mesh export

2026-11-03. No SDK build, runtime change or shared decoder modification.
The private export now contains **3,028 source model parts and 884,200 triangles**
from all **83 matched geometry packages**. These include traffic, police and
other vehicle variants; 83 is not a verified playable-car count.

## Concrete private assets

`/workspace/port-research/car-model-expansion-v2` contains:

- A `manifest.json` with source SHA, selected offline LOD, part counts and every
  rejected part. Seventy-four packages have no rejected part at the selected LOD;
  nine retain one explicit rejection each.
- Compressed `*.mesh.json.gz` files preserving positions, source S8/64 normal
  arrays, final UV arrays, original strip groups, texture/shader hashes, source
  transforms/bounds, all five emitted index channels, and source header statistic.
- Seventy-four `body.obj` files for ordinary KIT00 body inspection. Their OBJ
  groups retain source texture/shader hashes. They do not invent material shaders,
  textures, wheel attachment or whole-car assemblies.

Offline selection is B when available, then C, A, D, E: 55 packages use B,
27 use C and one uses A. This makes original traffic geometry available without
fabricating B meshes. It is an explicit export choice, not recovered game LOD or
attachment selection. Kits, damage parts and many other separate pieces remain
separate, rather than all being drawn as one car.

## Original emitter correction

The previous raw-format22 reference incorrectly expected its four input indices
to be emitted byte-for-byte. The actual original loop reads the third input
index twice. For example raw `18 19 19 18` emits `18 19 19 19 18` at the GX FIFO.
Compiled packets already contain five indices and go directly through the
original GXCallDisplayList path.

`tools/car_geometry_expanded.py` executes the SHA-pinned original descriptor
window 8011773C..801181C0, intercepting only GXBegin/GXCallDisplayList and bounded
FIFO writes. Every accepted descriptor was compared with the original emitter;
identical descriptor/packet cases share a verified cache result. Observed unique
cases: **153,435 raw packets and 34,078 compiled packets**, 187,513 total.
Source material, vertex count and primitive constraints remain checked.
This validates these observed packets, not every hypothetical flag combination.

The third/fourth emitted channels are deliberately retained as unresolved
channels. Treating the third index as a colour-array index caused false array
bounds failures: source +20 often covers only four auxiliary bytes. The exporter
preserves those auxiliary bytes and does not invent a colour-index binding.
Full original GX attribute/channel semantics still need recovery before claiming
complete material/lighting fidelity for every vehicle.

## Header statistic and geometry safety

The original descriptor loop does not consume header +0x14; existing recovered
LOD consumers use it as a statistic. It is retained unchanged alongside emitted
index-nondegenerate triangle counts. Fifty-seven exported parts differ from this
statistic. No source bytes are rewritten to make the counts agree.

The standalone decoder still rejects unsupported formats and invalid primitive,
reference-table, descriptor/blob, attribute-array, overlap, nonfinite, inverted
bound and position-containment cases. It checks all consumed position/normal/UV
ranges. Unresolved channels remain source indices and are not claimed to have a
validated target binding. The old production `decode_brakes.py` stays unchanged.

The nine retained rejections are DB9_KIT00_FRONT_RIGHT_WINDOW_B (inverted source
bounds) and eight TAXI/traffic DRIVER parts (unsupported/bounded descriptor).
They are not silently repaired or replaced. A package with such a rejection is
explicitly incomplete, even though its other exported pieces are usable.

## Verification and reproduction

Against the strict decoder's 28 already accepted B packages, **1,389 parts match
exactly** for positions, normal values, UVs, triangle position indices and triangle
UV indices. Seven source corruption variants are rejected: format, blob size,
draw offset, material index, UV offset, nonfinite bounds and array overlap.
Changing only the advisory header statistic preserves the actual topology and
retains the changed statistic separately. Geometry and raw game assets remain
private; only authored tool/findings are in Git.

Use a fresh output directory:

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps \
python tools/car_geometry_expanded.py \
  --directory /workspace/port-research/all-car-candidates \
  --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
  --output /workspace/port-research/car-model-expansion-new
```

Then run provenance/legacy/corruption checks against that export:

```sh
PYTHONPATH=tools:/workspace/toolchains/python-deps \
python tools/car_geometry_expanded.py \
  --directory /workspace/port-research/all-car-candidates \
  --dol /workspace/attachments/b794d4be-69a9-4fd2-80cc-2be71047d056/Speed.dol \
  --output /workspace/port-research/car-model-expansion-new --verify-exports
```

Runtime conversion, actual preset/part attachment selection, generated paints,
light/window state and final material semantics remain integration work. This is
substantially broader actual mesh availability, not 83 ready-to-drive cars.
