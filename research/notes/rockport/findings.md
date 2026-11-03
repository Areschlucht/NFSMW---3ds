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


# Rockport driving prototype v0.11

This build adds a nearby-road map and advance road-edge warnings. Hill/bank
alignment, animated wheels and original scenery remain.
It is a new native 3DS application built around recovered assets, not the
original NFS engine running on ARM. It has a main menu, garage, controls and a
chase-camera drive through a partial Colonial area (original sectors 141–148).
No generated road mesh is included.

The area contains the existing 91 original road/terrain/prop meshes plus 73
nearby scenery instances: seven buildings, 19 trees, six signs, 39 props and two
wall/fence objects. Together they draw 11,944 triangles using 64 recovered world
textures, reduced to at most 128×128. All instance positions/rotations come from
the game files; transformed bounds agree with the stored bounds within 7 mm.
Missing models and objects beyond the scenery budget are omitted and counted
in the conversion manifest.
The BMW uses the recovered body plus four instances of its original front tire
mesh (7,704 car triangles total). Tire textures resolve; seven car texture
references still use plain gray placeholders, including generated paint.
**Wheel positions are estimates fitted to the original body arches, not recovered
axle metadata.** The original front tire is reused at all four corners. All four tires now roll with accepted car travel, and the front pair follows
the prototype controller steering angle. Placement remains provisional. Complete scenery, original lighting/materials,
traffic, police, races, progression, audio and the rest of the city are absent.
Some road materials look too light or stretched because the original material
system is not reproduced.

## Install

Extract the **complete ZIP** to the SD card root. This installs a separate app:

```text
/3ds/nfsmw-rockport/nfsmw-rockport.3dsx
/3ds/nfsmw-rockport/nfsmw-rockport.smdh
/3ds/nfsmw-rockport/body.nfm
/3ds/nfsmw-rockport/world.nfm
/3ds/nfsmw-rockport/road.nrd
/3ds/nfsmw-rockport/wheels.nwa
/3ds/nfsmw-rockport/car-textures/*.t3x
/3ds/nfsmw-rockport/world-textures/*.t3x
```

Launch **NFS MW Rockport Prototype v0.11** from Homebrew Launcher. Choose
**Drive Colonial sample**. A missing/invalid asset produces an error screen.
This app targets baseline ARMv6K and does not enable the New 3DS clock or L2 cache.
The user reports that v0.6 runs well on New 3DS without overclocking. This is
a qualitative report, with no measured FPS. The v0.11 navigation build has been
checked in the emulator; Old 3DS operation remains unverified.

| Control | During driving |
| --- | --- |
| A | Accelerate |
| B | Brake |
| Y | Reverse |
| Circle Pad / left-right D-pad | Steer |
| R | Prototype handbrake |
| X | Reset to starting position |
| START / SELECT | Main menu; simulation pauses there |

Use Up/Down and A in the menu. START exits from the main menu. B/START returns
from the garage or controls page. Entering Drive starts at the spawn again.

In the garage, hold A to roll the wheels and use the Circle Pad or left/right
D-pad to steer the front pair. Y pauses/resumes the camera orbit. X resets the
view, steering and wheel angles. These inspection controls do not move the car.

## Driving limits

The controller is a new kinematic model; it does not reproduce Most Wanted's
physics. Ground contact samples 2,930 original **rendered road triangles** with
barycentric height interpolation at 120 Hz or finer. The original collision
format has not been reconstructed. The car stops when its center would leave the
supported road or change height by more than the contact limit. This also stops
it at missing-sector edges. Reverse or X can recover from an edge.

There is no body/wheel collision, suspension, wall collision, jumping or off-road
simulation. The chassis now pitches and rolls with a plane fitted to road heights under
the four wheel pivots. This is rigid visual alignment, not suspension or tire
force simulation. The lowest converted car vertex sets the ground offset along
the fitted road normal. Rendering
uses recovered road/terrain/prop positions unchanged apart from coordinate
conversion and normalization. Road edges are not extrapolated or filled in.

## Build and reproduce

`bash tools/build_rockport.sh` uses the pinned offline devkitPro image. The older
BMW/menu build remains `bash tools/build_bmw.sh`; the brake app remains
`bash tools/build.sh`.

`tools/decode_world.py` reads world draw formats 1 (float32 positions) and 32
(S16 positions with eight fractional bits). Each corner references position,
color and UV, unlike the car layout. Chunk metadata/table/blob alignment uses
original file offsets. Every selected model passes its stored triangle count
and position bounds. The selected TRN matrices are identity. `tools/world_instances.py` reads the 72-byte object tables and aligned 64-byte
instance records. The object index is the final 16-bit field (offset 62), not
the field at 28. Three hashes provide LOD choices. Packed 3×3 rotation matrices
use row vectors with scale 1/8192; translations are float32 at offset 32. Local
modeling matrices are not applied a second time. A model is included only when
its transformed bounds fit the stored world bounds within the decoder tolerance.
The runtime does not synthesize instance placement. Later sectors with unresolved triangle
counts are recorded in the research and excluded from this sample.

`tools/build_rockport_scene.py WORLD_SAMPLE L2RA.BUN OUTPUT` accepts repeated
`--texture-bundle` arguments for the stream prefix, both world samples and the
uncompressed GLOBALB bundle. Add repeated `--scenery-bundle` arguments for the
stream prefix and both sector samples to recover instance geometry. The default
scenery radius is 180 m, with at most 16,000 additional triangles and 64 total
world textures. It selects sectors 141–148 from the original index,
recovers referenced textures, writes `world.nfm`, `road.nrd`, `scene.json` and
PNG textures. Convert PNGs with `tex3ds -f rgba8 -z auto -o output.t3x input.png`.
`tools/package_rockport.py WORLD_SCENE BMW_SCENE` makes the installation ZIP.
Only converted sidecars are loaded on the console; the game archives/DOL are not
executed there.

Both NFM scenes have CRC/size/count/float/batch/texture checks. NRD1 has a 64-byte
header (version, count, payload CRC, scale, car size, origin, spawn and heading)
followed by original road triangle coordinates in local meters. Runtime checks
validate CRC, reserved fields, ranges, finite floats, nonzero projected areas
and the spawn's ground contact before driving is enabled.

## Validation

The strict devkitARM build and shader assembly pass with `-Wall -Wextra -Werror`.
The Python suite covers world float/fixed vertices, raw/compiled strips, UVs,
triangle mismatches, invalid indices/primitives, nonfinite positions and bounds,
instance table alignment, LOD fallback, rotation convention, bounds rejection,
invalid indices and nonfinite transforms, as well as the existing archive/texture checks. Native ASan/UBSan checks cover
slopes, shared edges, missing ground, stopping at an edge, reversing away,
invalid inputs and the real converted road asset including CRC corruption.

Azahar 2126.2, with Mesa software OpenGL and a virtual SD, runs this build.
Startup, entering Drive, textured world/car drawing, acceleration, braking,
reverse, steering, handbrake input, reset, return navigation, garage, controls
and exit are checked there. Emulator execution is not a console FPS result.
Routine development does not require another hardware test from the user.

The Python suite passes 48 tests. Native road-contact checks pass on both the
v0.6 and v0.8 converted assets. Ground contact still uses the same 2,930 original
road triangles; scenery adds no collision or new drivable surfaces. Verified axle metadata remains unavailable; the fitted wheel placement is
explicitly provisional. No asset upload or device test is required from the user
while they are away from their PC.

## Vertex colour and wheel research in v0.8

World vertices now retain the original RGB colour attribute. Source colour alpha
is not treated as opacity because it participates in unresolved material/night
lighting. Original texture alpha still controls transparency. The shader uses
baked world RGB directly instead of applying generated normal-based lighting a
second time. The car retains inspection lighting. The original material system
is not fully reproduced.

NFM version 2 retains the `NFM1` magic and adds four float32 colour channels after
position/normal/UV, making a 48-byte file vertex. Version 1 remains supported
with white colours. Bounds, CRC, length and finite colour-range checks apply to
both versions. The runtime also uses a 48-byte vertex stride for legacy scenes.
The previous BMW build still compiles with the common loader.

Executable GX setup at 0x8010E428–0x8010E43C and
0x8010E4E8–0x8010E4FC confirms 12 fractional bits for world texture coordinates;
the existing 1/4096 UV scale is retained. GX formats 1 and 3 request RGBA8 colour
at 0x8010E410–0x8010E424 and 0x8010E4D0–0x8010E4E4.

`tools/build_bmw_scene.py ... --fit-wheels` enables a BMW-specific estimate.
`tools/fit_bmw_wheels.py` robustly fits circles to the body's side/arch vertices.
The fitted arch curves have roughly 3 mm RMS residual; that is **not a claim of
3 mm axle-placement accuracy**. A common axle height and conservative inboard
placement keep the four equal original tires on one plane and inside the body.
This is a temporary assembly for the prototype. Animation, suspension, rear tire
sizing and the original vehicle attributes remain unresolved.

## Wheel animation in v0.9

Wheel vertices are split into four independent material groups; body triangles
remain in group zero. The GPU rotates each group about its fitted pivot. No
per-frame vertex buffer rewrite or additional triangles are needed. The car
remains 7,704 triangles; the world remains 11,944 triangles.

The new `wheels.nwa` file binds the group map to the exact car scene CRC and
batch count. Its header/version, payload size/CRC, pivot/radius ranges, front
axle flags and group coverage are validated before rendering. Wrong/mixed car
and animation sidecars show an initialization error. Extract the complete ZIP
when eventually updating; retain the earlier ZIPs for rollback.

Signed accepted displacement determines rolling angle using the recovered tire's
axis radius (about 0.33 m). Square alpha-cut texture-backface corners are excluded
from the radius measurement. Reversing changes the rolling direction; a blocked
car stops wheel rotation. Front wheels use the controller's steering angle, and
the rear pair stays straight. X and starting a new drive reset all phases.
Suspension, original axle settings, Ackermann steering, tire slip and handbrake
wheel locking are not modeled.

Native ASan/UBSan checks cover real rig/car binding, forward/reverse travel,
stationary/blocked motion, long-run angle wrapping, reset, nonfinite inputs,
CRC corruption and mismatched scenes. Python checks cover rig layout/validation.
Emulator image checks compare wheel-only rolling/steering with the garage
camera paused and verify exact reset restoration, followed by driving/menu
regression checks. No physical-console test is requested while the user is on
their phone.

The tire orientation is also corrected in v0.9: the recovered TIRE_BACK plane
is at maximum local Y, so it now faces inboard. The textured rim faces outward
on both sides. A regression test covers this orientation and the radius
measurement. Garage animation recordings are actual emulator frames with the
camera paused, not a physical-console performance recording.

## Road slope alignment in v0.10

The renderer uses existing road contact data at the four fitted wheel pivots.
Three or four supported contacts define a least-squares plane. With fewer than
three, the actual center triangle normal supplies orientation; no missing road
surface is created. Pitch and roll are each limited to about 29 degrees to
restrain responses to curbs/steep triangles in this prototype. The chassis
translation follows the resulting up vector so that tilting does not simply
push the tires below the plane. Garage presentation is unchanged.

Contact sampling is cached while position/heading/height are unchanged; moving
frames add four footprint queries and one center query. No textures, vertices
or triangles are added. The original assets, spawn, movement controller, edge
stops and wheel animation are unchanged. There is no spring/damper behavior,
independent wheel suspension, jumping or recovered original vehicle physics.

Native ASan/UBSan tests cover flat/longitudinal/banked/combined slopes at four
headings, missing contacts, unsupported ground, tilt limits and invalid inputs.
The real spawn has four supported wheel contacts and about -1.9 degrees pitch;
a 600-step real-map drive maintains a valid pose. Existing contact tests and
48 Python tests pass. The strict 3DS build and emulator driving/reset/menu checks
also pass. No physical-console performance claim follows from these checks.

## Nearby-road map and warnings in v0.11

The driving HUD now includes a scrolling map showing the road surfaces available
in this partial build. White pixels are a top-down projection of the original
2,930 road contact triangles. The gold arrow shows the car's heading; the cyan
marker shows the reset/start position. It does not display uninstalled roads
as if they were driveable. The diagram is generated from the original triangles,
not a replacement road mesh or a recreated original NFS radar interface.

A 512×512 one-byte map is rasterized once at startup, with a bounded work budget.
A 152×128 crop is drawn into the lower console’s rotated RGB565 framebuffer
with explicit format and buffer-bounds checks. The HUD updates five times per
second. The map adds about 256 KiB for the mask plus a small RGB staging buffer;
it needs no new textures, game files or 3D geometry. The map is a 2D footprint,
so overlapping road levels are not distinguished there.

When moving, a straight-line ground probe checks 6–20 m ahead, depending on
speed, at 1 m intervals. Reverse checks behind. Missing supported ground shows
**Road edge ahead/behind** before the existing stop; hitting an edge shows
**Road edge reached — reverse or reset**. This warning can also appear where a
road bends away from the current heading. It is a preview aid, not route finding
or an automatic brake. The movement controller and actual edge stops are unchanged.

Native ASan/UBSan checks cover road coverage, arrow orientation, forward/reverse
warnings, stationary behavior, invalid inputs and the real map. The real mask
contains 10,656 covered pixels at about 1.91 m per pixel. Existing Python tests
and the strict 3DS build pass; Azahar checks cover the map, scrolling/start marker,
edge warning and stop, reverse, reset, garage animation and menus/exit.

A native blit regression test checks RGB565 colour conversion, rotated pixel
addresses, guard bytes outside the destination, undersized buffers and invalid
placement bounds. This covers the pixel-format mismatch caught during initial
emulator layout testing.
