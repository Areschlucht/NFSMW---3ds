# Original Rockport asset research

The initial samples and both targeted world-sector samples have been received.
The selected original Colonial road surfaces now decode and are used in the
[v0.6 driving prototype](ROCKPORT-PROTOTYPE.md). No generated replacement road is
included. The navigation/index findings below describe the earlier research stage.

| Recovered data | Result |
| --- | --- |
| Streaming index | 997 unique sections; ranges fit the 109,279,744-byte stream |
| Navigation nodes | 4,385 original positions |
| Navigation connections | 6,538 original endpoint pairs |
| Adjacency checks | All 13,076 references agree with the endpoints |
| TrackMaps images | 297 images decoded with the existing GameCube texture reader |
| First 8 MiB stream prefix | 10 complete geometry packages, 54 complete texture packages, one cut texture package |

The graph is navigation data. It does not establish road widths, surface triangles,
collisions, barriers, lane behavior or the game's driving physics. The graph plot
joins stored endpoint positions; it must not be used as a substitute road mesh.
The prefix's geometry packages name shared scenery such as WestPark and Library
objects. Their format differs from the currently supported car geometry reader;
they have not been presented as decoded road surfaces.

## Reproduce the research

Run with Python 3; only the optional plot needs matplotlib:

```sh
python3 tools/inspect_map_samples.py rockport-map-samples ZDIR.BIN > inspection.json
python3 tools/nfs_rockport.py rockport-map-samples/L2RA.BUN road-network.json --plot road-network.png
python3 tools/nfs_tpk.py rockport-map-samples/TrackMaps.bin trackmap-images
python3 -m unittest discover -s tests -p 'test_*.py'
```

The current Python suite passes 29 tests. New graph checks cover corrupt pointers,
table overlap, truncated input, invalid positions/IDs/degrees/adjacency and invalid
streaming ranges. The real samples pass the sample inspector; the graph decoder
validates both endpoint references for every segment. This is host-side asset
research, not evidence that a game runs on 3DS.

## Observed layouts

The top-level `0x00034110` chunk contains 997 records of 92 bytes. In each record,
little-endian words 2, 5 and 6 give the section identifier, stream-relative byte
offset and byte length. Word 4 is 1; words 6–8 agree in all supplied records.
All section starts align to 2,048 bytes, and ranges are ordered without overlap.
Other fields are not assigned runtime meanings.

The `0x0003b800` payload contains eight alignment bytes followed by a `CARP`
directory. Its leaf descriptors use big-endian fields; each data pointer is
relative to its own 16-byte descriptor. A file-relative interpretation gives
wrong table locations. The observed `RNnd` table has 32-byte node records:
three big-endian floats at offset 0, node ID at 12, adjacency count at 16 and up
to seven big-endian 16-bit segment references at 18. The `RNsg` table has
22-byte records: endpoint node IDs at 0 and 2, segment ID at 8. Unresolved fields
and the other CARP tables are preserved as metadata, not treated as geometry.

## World-sector samples received

Both files produced by [extract-rockport-world.ps1](tools/extract-rockport-world.ps1)
have been received. No further extraction is needed for the v0.6 sample.

| Output file | Archive offset | Bytes |
| --- | ---: | ---: |
| STREAML2RA-sectors141-160.BUN | 156,141,568 | 2,679,680 |
| STREAML2RA-sectors1141-1160.BUN | 186,742,784 | 1,137,136 |

These are indexed sector ranges, including the original gaps between entries,
totaling 3,816,816 bytes. The first range starts at stream offset 24,545,280;
the second at 55,146,496. The stream itself starts at archive offset 131,596,288.
The ranges come from the received `L2RA.BUN`, SHA-256
`73d4a98efcd366e6dc1e13a3fdc1f1494e8763edac05b7f911dc66b62c2c072d`.
Selected sectors 141–148 decode to 91 TRN meshes (6,992 triangles) with 22/22
texture references recovered. All selected triangle counts and stored position
bounds match, and their matrices are identity. Later variants with count
mismatches remain rejected. The original collision tables and instance placement
are not yet reconstructed; v0.6 uses point contact on 2,930 road render triangles.
See the prototype documentation for the supported slice and remaining limits.


## Scenery placement in v0.7

The native build now includes 73 original scenery instances around the existing
Colonial spawn: seven buildings, 19 trees, six signs, 39 props and two wall/fence
objects. The scene totals 11,944 triangles and 64/64 recovered world textures.
The instance reader uses original positions, packed rotation matrices and LOD
hashes. Included transforms reproduce stored bounds within 7 mm. Unavailable
models and objects exceeding the texture budget are counted and omitted; no
guessed placement is used. The road-contact triangles are unchanged.

The user reports v0.6 runs well on New 3DS without overclocking; this does not
establish Old 3DS performance or v0.7 hardware FPS. The current build is checked
in Azahar. Wheel attachment positions, faithful road materials, scene activation
conditions, complete scenery and scenery collisions still require research.


## Vertex colours and provisional tires in v0.8

The world converter now exports original RGB colour attributes, supported by
NFM version 2 and a four-attribute PICA shader. Legacy NFM v1 defaults to white
and still passes native checks and emulator rendering. Source colour alpha
remains uninterpreted; texture alpha still handles transparency. World baked
RGB replaces the extra inspection-light multiplier. Executable GX setup confirms
RGBA8 and the existing 12-bit UV fraction; no speculative UV rescaling was used.

The BMW now includes four instances of the original front tire mesh, with
resolved TREAD, TIRE_BACK and BMWM3GTRE46_TIRE images. Placement is a **temporary
body-arch fit**, not recovered axle metadata. The car has 7,704 triangles, 19
texture references and the same seven unresolved body texture placeholders.
Tires are static. The car's road offset is derived from its lowest vertex.
The actual road-contact asset remains byte-identical to v0.7.

43 Python tests, native scene/contact ASan/UBSan checks, strict builds and
Azahar driving/menu/reset checks pass. The legacy BMW app also renders with the
extended loader/vertex stride. The user is away from their PC; no device testing
or new uploads are requested. Artifacts remain local; nothing is published.


## GPU wheel animation and rim orientation in v0.9

The four fitted tire instances now have independent GPU transforms. Actual
accepted car travel drives signed rolling angles, and only the front pair
follows steering. No extra triangles or per-frame vertex uploads were added.
Car batches are split by material and wheel group (28 batches, 7,704 triangles).
`wheels.nwa` stores four fitted pivots/radii/front flags and the batch map, tied
to the exact car scene CRC. The parser checks all bounds, flags and group
coverage before rendering. The axle settings remain provisional.

The prior black outward-facing wheels were the tire backs. The source material
surfaces identify the back at maximum local Y and the rim toward minimum Y.
The converter now faces that back inward on both sides; its regression test
also checks that alpha-cut square backface corners do not inflate the rolling
radius. Rims use the original BMWM3GTRE46_TIRE image.

Native ASan/UBSan checks pass for the real car/rig pair, forward/reverse rolling,
stationary and blocked travel, long-run wrapping, reset and invalid/corrupt
input. The Python suite passes 48 tests. Emulator checks compare independent
rolling/steering with the garage camera paused and verify exact reset images.
The world, contact asset and driver physics are unchanged from v0.8.


## Rigid road alignment in v0.10

The chassis now follows a plane fitted to original road heights under the four
provisional wheel pivots. Three/four contacts produce the fit; fewer contacts
use the actual center triangle normal. Pitch/roll are bounded, and the ground
offset follows the up vector. Surface sampling is cached while the vehicle's
position, heading and height are unchanged. Original map/car assets, movement
controller, wheel rig and point-contact edge handling are unchanged.

Native ASan/UBSan tests cover flat/hill/bank/combined slopes at four headings,
three contacts, two-contact fallback, unsupported center, limits, invalid input
and a 600-step real-map drive. At spawn the fit has four contacts and about
-1.9 degrees pitch. Existing contact tests and 48 Python tests pass. The strict
ARM build and Azahar driving/garage/reset/menu checks pass. Pixel comparisons
show the slope update changes only the car region at spawn, with exact reset
restoration. This remains rigid visual alignment, not original spring/tire
physics. No device test or asset upload was requested from the user.


## Loaded-road navigation in v0.11

A new lower-screen map projects the original loaded road contact triangles.
It adds no replacement road mesh or new asset requirements. A gold arrow shows
heading and a cyan marker shows the start. A bounded 512×512 mask is built once
(10,656 covered pixels at about 1.91 m/pixel); a scrolling crop updates with the
HUD at five Hz. Ahead/reverse ground probes warn about unsupported road before
the unchanged edge-stop logic. The warning follows current heading rather than
a planned route. The 2D map does not separate vertically overlapping roads.

Native ASan/UBSan checks cover projection, heading arrows, forward/reverse
warning, invalid inputs, RGB565 blit addressing/colour conversion and guard
bytes. The initial emulator layout caught a RGB8-versus-RGB565 mismatch, fixed
before packaging. The corrected on-screen map matches the independent native
reference within seven RGB levels (RGB565 quantization). Emulator captures show
ahead warning at 63 km/h, then the edge stop at 0; driving and garage resets
restore identical displays. Existing 48 Python tests and the strict build pass.
No physical-console test was requested.


## Colonial scenery and centerline spawn in v0.12

The bounded selection radius increases from 180 to 350 m and the shared scene
texture cap from 64 to 128. All 100 selected world images resolve. The result
contains 129 original scenery instances: 22 buildings, 38 trees, 11 signs,
47 props and 11 wall/fence objects, totaling 19,497 world triangles. Original
placement/bounds checks remain enforced. No new road geometry is generated.

Free drive omits 61 named TrackBarrier instances while activation rules remain
unresolved. One added building needs two unavailable images (7e2734a8/7e2734a9)
and is omitted; 122 nearby instances still lack matching source models. Nine
catalog model variants with unresolved triangle counts remain rejected.

The car starts at a supported projection onto original navigation segment 406,
with all four footprint samples on road. Comparing supported straight runs in
both segment directions chooses 118 m ahead, versus 32 m at the old start.
The 2,930 contact triangles are unchanged in absolute source coordinates.

Python passes 51 tests, including centerline projection, direction choice and
unsupported/different-deck rejection. ASan/UBSan covers the 100-texture scene,
road contact, real-map slope alignment and navigation mask. Both Rockport and
legacy BMW strict ARM builds pass. Azahar checks startup, acceleration, road-edge
stop, reverse, exact driving/garage reset restoration, wheel animation and
menu/controls/exit. No new console performance result is claimed.

Original material behavior remains unresolved: some wall images contain mostly
zero alpha and become incorrectly transparent with the provisional renderer.
Roads remain too light. Executable texture initialization at 0x8026C484 passes
texture parameters to 0x8026C2A8; it does not by itself establish per-material
alpha usage. No guessed alpha override is applied in this release.


## Original world opacity in v0.13

The user reports v0.12 runs very well on New 3DS without overclocking, matching
the earlier builds they tested. No measured FPS or Old 3DS result is claimed.

Tracing the supplied Speed.dol finds TextureInfo's byte 85 read at 0x801066EC
and byte 86 at 0x8010670C. Byte 85 enables alpha testing only for value 1.
The switch maps byte 86 = 0 to GX_BLEND_NONE and mode 1 to
GX_BLEND_BLEND/SRCALPHA/INVSRCALPHA; the call to GXSetBlendMode is at
0x80106840 (target 0x8034043C). Mode 0 also enables depth writes via
0x801064FC; blended mode disables them. Source image alpha is therefore not a
reliable substitute for the original blending state.

The converter now applies that opaque state before thumbnail resizing. It
preserves the raw decode and RGB, sets only converted alpha to 255 for mode 0
with alpha testing disabled, and records both source settings and raw RGBA
SHA-256 in the manifest. Thirty-five world images change. Eight alpha-tested textures and one blended fence retain
alpha. No selected texture uses blend modes above 1;
unimplemented world blend modes cause an explicit conversion error.

The scene still has 19,497 triangles, 100 world textures and 129 scenery
instances. Geometry/batches, original RGB vertices, spawn, road.nrd and car
assets match v0.12. Five new synthetic-package tests verify metadata reads,
solid zero-alpha walls, blended foliage, alpha-tested cutouts and unsupported
modes. All 56 Python tests and strict ARM build pass; native scene/contact
sanitizers pass. Azahar captures confirm restored building walls and asphalt
markings, with driving/garage/menu regressions checked before packaging.
Original material layering, reflections/night effects, transparent sorting,
missing models and scenery collisions remain unresolved.


## New samples and Colonial expansion in v0.14

The first24MiB prefix and sectors161–176/1161–1176 are received. Prefix bytes
0–8 MiB exactly match the earlier sample; new range lengths match L2RA's index.
The prefix yields 2,090 validated catalog models; the new high/low ranges yield
569 and 320. Unresolved catalog models remain rejected. The three extraction
ranges are recorded in `tools/extract-rockport-next.ps1`. No further upload is
needed for this build.

The scene selects 141–148,160,163–165,168–170. All selected TRN counts/bounds
validate. It has 164 TRN meshes and 294 placed scenery instances: 58 buildings,
36 trees,10 signs,76 props,114 wall/fence objects. All 128 selected images
resolve. The world totals37,359 triangles; original contact grows2930→5483.
The 350m radius,24,000 scenery-triangle budget and128-texture cap omit other
objects explicitly (157 texture budget,200 triangle budget,137 race barriers).

A multi-range selector preserves indexed offsets, omits unselected intervening
sectors and rejects incomplete/conflicting ranges. Native sanitizer checks
confirm all previous road triangles and the spawn remain within1mm after
rebasing. Forty-eight shared-edge traversals sample ground across old/new joins.
The loaded-road mask grows from10,656 to16,107 covered pixels at its new2.06m
resolution. Native contact/pose/map/scene checks and63 Python tests pass.

New texture ARC_TOWERHAZERDLIGHTS uses original blend mode2: SRCALPHA/ONE.
NFM flag4 requires blended-pass flag1; runtime switches the blend state per
world batch and restores standard alpha before drawing the car. Synthetic
metadata tests and native unknown/inconsistent flag rejection cover this.
The full original material/lighting/collision systems remain unresolved.


## Performance, chase camera and handling in v0.15

The user reports v0.14 remains at stock New 3DS settings, with estimated
30–40 FPS looking at dense scenery. This is an estimate rather than a measured
counter result. Map expansion pauses while performance and driving feel take
priority. No additional original files are needed for this step.

The scene is losslessly partitioned into 1,046 texture/cell groups at 64 m.
The textured-triangle multiset matches v0.14 byte for byte; road.nrd and all
128 T3X textures are unchanged. Full per-group bounds are calculated once.
Six conservative view planes reject invisible groups; adjacent visible memory
ranges sharing a texture are merged to limit draw overhead. At spawn, submission
falls from 37,359 to 10,488 world triangles in 84 calls. Across 24 sampled
headings at two locations it varies from 1,842 to 32,709 triangles, averaging
11,023; merged calls range31–204. These counts do not establish a hardware FPS
improvement. Highly visible dense geometry can remain expensive.

Two Azahar top-screen comparisons, including a dense street view, are exactly
identical with culling enabled and disabled. The debug reference submits the
whole world; it is excluded from the installation ZIP. The HUD now measures
application FPS over one-second windows and displays submitted world triangles,
draw calls, GPU time and Citro3D CPU draw-processing time. That CPU timing does
not include physics/camera work outside Citro3D.

The camera uses critically damped eye/target springs, shortest-angle delayed yaw,
velocity feed-forward and gently speed-dependent distance/FOV. Reset snaps to a
known camera state; menu time does not advance the drive camera. There is no
camera-versus-scenery collision. Handling adds smoothed yaw rate and lateral
velocity/grip to speed-sensitive steering and power-limited acceleration.
Handbraking releases grip and increases yaw response. Edge stops clear residual
longitudinal/lateral/yaw motion. This is a provisional arcade approximation;
original engine/gearbox/suspension/tire/nitrous parameters remain unrecovered.

Native sanitizer tests cover visibility plane boundaries/intersections, camera
yaw lag/wrap/reset and30/120Hz settling, steering/yaw inertia, handbrake slip,
brake hold at rest, frame-step consistency, road contact/edge/reverse, pose,
wheels and map regressions. Strict Rockport/reference/legacy BMW builds and
63 Python tests pass. Emulator tests cover actual steering/braking/edge/reverse,
deterministic camera/car reset, garage rolling/reset, menus/controls/exit.


## Hardware feedback and GPU/contact/drift work in v0.16

The user reports v0.15 counter readings of 18–40 FPS without New 3DS clock/L2
features, and 50–60 FPS with 804 MHz and L2 enabled together. A crowded view
reaches 22 ms GPU time and about 200 world draw calls. The clock/cache effect is
not isolated, and no v0.16 hardware FPS result is claimed.

The world previously ran normal transformation/normalization and inspection
lighting despite lighting uniforms (1,0) selecting baked colour. A dedicated
world shader removes those calculations (28→13 source instructions). World
GPU vertices retain exact float32 XYZ/UV/RGBA and omit unused normals, reducing
stride 48 → 36 bytes. Source NFM geometry is unchanged; CPU-side bounds still
come from the full validated decode. Explicit shader, attribute and matrix
rebinding preserves car lighting. Start and dense-street top-screen captures
match v0.15 exactly.

RoadWorld gains an optional bounded uniform grid. The current asset uses
33×20 cells, 7,620 references and about 33 KB. Queries preserve original order and
tolerances, examining 80.88 average / 187 max candidates at triangle centroids
instead of 5,483. A total of 35,254 real-map comparisons match linear heights/normals
exactly, with additional synthetic deck/tie, memory-cap and cleanup checks.
Invalid/allocation-heavy indexes retain a linear fallback. Source road.nrd
remains unchanged.

Handbraking now builds a rear-grip state that recovers gradually after release.
The native example starts at 14 m/s: a 0.35 s tap with 80% steering reaches 15.9°
slip, retaining 18.4° after 0.3 s of release. Both phases stay on the original
starting road. Countersteering, grip recovery, rear-wheel phase locking,
18/20/120Hz consistency and camera response are checked. The main-loop cap
changes 50 → 100 ms so sub-20-FPS frames do not lose elapsed simulation time.
CPU logic time and signed slip angle appear in the HUD. These are provisional
arcade dynamics; original vehicle simulation and collision remain incomplete.
