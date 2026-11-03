# Rockport driving prototype v0.14

This build expands the original Colonial roads and scenery using the newly
supplied stream samples. The v0.13 solid-wall/asphalt correction, navigation,
road alignment and animated wheels remain. It is a new native 3DS application
built around recovered assets, not the original NFS engine running on ARM.
It has a main menu, garage, controls and chase-camera driving through a partial
Colonial area. No generated road mesh is included.

The area contains 164 original road/terrain/prop meshes plus 294 validated
scenery instances: 58 buildings, 36 trees, 10 signs, 76 props and 114 wall/fence
objects. Together they draw 37,359 triangles using 128 recovered world textures,
reduced to at most 128×128. All instance positions/rotations come from the
game files. All selected textures resolve. Objects beyond the 350 m scenery
radius or the texture/triangle budgets are omitted and counted in the manifest.
Scenery remains incomplete and has no collision.

The BMW uses the recovered body plus four instances of its original front tire
mesh (7,704 car triangles total). Tire textures resolve; seven car texture
references still use plain gray placeholders, including generated paint.
**Wheel positions are estimates fitted to the original body arches, not recovered
axle metadata.** The original front tire is reused at all four corners. All four tires now roll with accepted car travel, and the front pair follows
the prototype controller steering angle. Placement remains provisional. Complete scenery, original lighting/materials,
traffic, police, races, progression, audio and the rest of the city are absent.
The original lighting, texture layering, reflections and material effects remain
incomplete. The v0.12 transparent-wall/pale-road defect is corrected for the
selected assets; this does not reproduce the complete original renderer.

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

Launch **NFS MW Rockport Prototype v0.14** from Homebrew Launcher. Choose
**Drive Colonial sample**. A missing/invalid asset produces an error screen.
This app targets baseline ARMv6K and does not enable the New 3DS clock or L2 cache.
The user reports that v0.12, like the earlier builds they tested, runs very
well on New 3DS without overclocking. This is a qualitative report with no
measured FPS. The v0.14 expansion has been checked in the emulator;
Old 3DS operation remains unverified.

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
physics. Ground contact samples 5,483 original **rendered road triangles** with
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
PNG textures. The v0.12 scene adds `--scenery-radius 350 --scenery-textures 128
--free-drive --complete-scenery --center-spawn`. The texture cap is 128 in both
runtime loaders. Free drive omits 61 named race-barrier instances whose original
activation rules are unresolved; one building with two missing textures is
omitted. Another 122 nearby instances have no matching available model.
The centerline start chooses between the two original segment directions using
actual road support: its initial straight run is 118 m, versus 32 m at the old
start. This is a spawn selection check, not a recovered race route.

Convert PNGs with `tex3ds -f rgba8 -z auto -o output.t3x input.png`.
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

The Python suite passes 63 tests. Native road-contact checks pass on both the
v0.6 and v0.8 converted assets. The v0.14 ground-contact asset expands to 5,483 original road triangles.
Scenery adds no collision or new drivable surfaces. Verified axle metadata remains unavailable; the fitted wheel placement is
explicitly provisional. No additional asset upload is needed for this build.

## Vertex colour and wheel research in v0.8

World vertices now retain the original RGB colour attribute. Source colour alpha
is not treated as opacity because it participates in unresolved material/night
lighting. In v0.13, texture alpha affects opacity only when the source render settings
enable blending or alpha testing, as described below. The shader uses
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

## Colonial scenery pass in v0.12

The scenery selection radius grows from 180 to 350 m around the same Colonial
starting area. All added positions and rotations come from the original
instance records and pass transformed-bounds checks. The first eight road
sectors remain unchanged; no replacement road geometry is generated.

The common scene limit and both app texture arrays now support up to 128
references. This build uses 100 world textures, about 1.64 MiB of decoded RGBA
texels, and 58,491 world vertices (about 2.68 MiB at runtime). These are asset
buffer sizes, not total process memory or a performance measurement. The car
geometry and animation sidecars are unchanged.

For this free-drive prototype, 61 objects explicitly named TrackBarrier are
omitted. This removes race-closure props while their original activation rules
remain unresolved; it does not reproduce the game's scene-activation system.
One available tire-shop object is omitted because two of its textures are
missing. All 100 included world texture references resolve. The conversion
report still records 122 unavailable model instances inside the larger radius,
including fences and streetlights. This area is denser, not complete.

The spawn is projected about 12 m from its old curb-side triangle centroid onto
original navigation segment 406. Original road triangles validate the center
and four footprint samples. The chosen original segment direction provides
about 118 m of straight supported road, versus about 32 m from the old spawn;
normal bends still require steering. This is a free-drive start selection, not
a recovered original race grid.

To reproduce, add `--scenery-radius 350 --scenery-textures 128 --free-drive
--complete-scenery --center-spawn` to the world conversion command. Source assets
and validated transforms are unchanged. Older ZIPs remain available for rollback.

Validation includes the expanded real scene above 64 textures, the 128-reference
rejection limit, legacy NFM v1/v2 scenes, all native contact/pose/map tests, and
51 Python tests including original-centerline selection and unsupported decks.
Azahar checks cover startup, the expanded scenery, sustained driving, warnings,
reverse/reset, wheel preview, controls and exit. The user has not been asked to
test the denser build on hardware; its physical-console FPS is unmeasured.


## World opacity in v0.13

The texture reader preserves the original TextureInfo bytes 85 and 86 as
`alpha_test_mode` and `blend_mode`. In the supplied executable, 0x801066D8
enables alpha testing only when byte 85 equals 1. The switch at 0x8010670C
disables blending for byte 86 = 0 and selects SRCALPHA/INVSRCALPHA for mode 1.
The opaque branch also enables depth writes through 0x801064FC.

The world converter previously inferred transparency from pixel alpha alone.
It now sets output alpha to 255 when the source disables both blending and
alpha testing, leaving decoded source RGB unchanged before resizing. This fixes
35 of the 100 converted images, including walls and road surfaces. The original
decoded bytes remain unmodified, and the manifest records their hashes and the
applied opacity rule. Existing alpha-tested trees and blended fences retain source alpha.
The car scene and its wheel textures are unchanged.

The selected textures contain 91 solid, eight alpha-tested and one blended
material. All use blend modes 0 or 1.
Other world blend modes are rejected until supported. The renderer still lacks
original layered/reflective/night effects, the original alpha-test threshold
and transparent depth sorting. The
world geometry, road contact, spawn and original RGB vertex colors are unchanged
from v0.12; no new scenery or collision geometry is added in this release.


## Expanded Colonial area in v0.14

Selected original sectors are 141–148, 160, 163–165 and 168–170. Every selected
TRN model passes its stored triangle count, bounds and identity-matrix checks.
The converter accepts `--world-range FIRST_SECTOR FILE` for separate indexed
ranges and repeated `--extra-sector ID` selections; it does not fabricate
intervening archive bytes or include unchecked intermediate sectors. Overlapping
source ranges must agree. The default remains the original 141–148 selection.

This scene uses the new first-24-MiB prefix and both new sector ranges as model
and texture catalogs. Use the v0.12 conversion options above, raise
`--scenery-triangles 24000`, add `--world-range 161 NEW_HIGH_RANGE`, then select
160, 163, 164, 165, 168, 169 and 170 with repeated `--extra-sector` arguments.
Add all five supplied prefix/high/low ranges to both the texture and scenery
bundles, plus GLOBALB as a texture bundle. Selected scenery contains no missing
model or texture placeholders; 157 other instances exceed the texture budget
and 200 exceed the triangle budget. Another 137 named race barriers are omitted
while their activation rules remain unresolved. This is still a partial area.

The scene includes one additive tower-light image. TextureInfo blend mode 2
maps to SRCALPHA/ONE at original executable 0x80106774. NFM texture flag bit 2
records additive blending and requires the blended-pass flag. The renderer
applies it per world batch and restores standard alpha blending before drawing
the car. Other unsupported blend modes remain rejected.

Native ASan/UBSan verifies that all 2,930 prior road triangles and the original
spawn survive coordinate rebasing within 1 mm. Forty-eight shared-edge probes
check supported ground across old/new surfaces. Real-map contact, rigid pose,
navigation mask and scene validation pass, as do the strict Rockport and legacy
BMW builds. Azahar checks the expanded scene, driving/edge/reverse/reset, garage
wheels and menus. The emulator reports 60 FPS at full speed in the captured run.
This is not a new physical-console measurement.
