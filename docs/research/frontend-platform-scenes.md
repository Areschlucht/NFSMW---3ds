# Original frontend garage/platform scene candidates

`build_frontend_platforms.py` extracts five actual platform ranges from the
verified ZZDATA1.BIN, SHA256470b7586d4fe53634c0078acfba716ecd1d1841cef4957a118a18f46f72c83b1.
The original names/ranges are also present in the directory inventory and DOL.

| Source platform | Decoded models | Original triangles | Static candidate triangles | Textures |
| --- | ---: | ---: | ---: | ---: |
| CAREER_SAFEHOUSE |14|16899|2097|33|
| CAR_LOT |8|10124|9047|53|
| CUSTOMIZATION_SHOP |12 plus one empty|11225|6757|55|
| CUSTOMIZATION_SHOP_BACKROOM |12|11225|1094|13|
| PLATFORMCRIB |15|14911|4819|33|

All nonempty models use the existing format22 world-geometry decoder. No shared
decoder constraint was relaxed. All accepted source positions, UVs, baked RGB,
material references, header transforms and declared/emitted statistics are kept
in each private all-source-models.json.gz. CUSTOMIZATION_SHOP's EMITTERTEST is an
explicit zero-descriptor, zero-payload record, validated separately rather than
silently treated as a failed visible mesh. Other unresolved nonempty models
would fail the export.

## Explicit static subset and limits

The native static candidate chooses exactly BACKDROP_CRIB and BACKDROP_CURRGEN.
This is a documented 3DS rendering subset; original pass-admission consumers have
not been recovered. BACKDROP_CAST_SHADOW_MAP, NEXTGEN shadow variants,
BACKDROP_REFLECTION, emitter boxes and helper geometry are retained separately
and named in scene.json. They are not rendered as ordinary scenery by this
export. Shadow/reflection passes, particles, fans and scene scripts remain
additional systems; no complete original menu lighting/material claim is made.

All selected texture references resolve to actual source pixels. The two bundles
that reference GREY00163c76 use its genuine32x32 FRONTB texture. No gray placeholder
or replacement texture is created. Original alpha/blend metadata remains in the
manifest; the NFM flag translation uses the existing prototype policy and does
not establish complete original material behavior.

## Native geometry and alignment

Each platform.nfm is NFM1/version2 with baked vertex colors and ordered adjacent
texture batches. It uses the existing source basis conversion(X,Z,-Y), then
divides by normalization_scale_world about origin zero to satisfy native NFM
coordinate bounds. Multiply by that factor to restore source viewer units.
source_bounds_viewer and normalization fields are recorded in scene.json.

The original static geometry headers are retained but not applied a second time;
their exact frontend consumer remains to verify. World meshes have no source
normal stream, so valid flat geometric normals are supplied for decoder
compatibility; baked-color rendering should use lighting1,0. Coordinate-degenerate
source triangles are retained with an unused up normal, and counted explicitly.

SourceXY(0,0) intersects a Z0 floor in CAREER_SAFEHOUSE and PLATFORMCRIB (the latter
also has a0.02344 layer); shop/backroom have0/0.01562 layers. CAR_LOT has a
-0.06634 layer there. These are geometric measurements, not a recovered original
car-placement policy. For the current normalized car, parent can align the
platform by restoring source units then subtracting that car's source viewer
center and dividing by its half extent. This must follow the active car's actual
normalization instead of assuming every car shares BMW's dimensions.

## Native textures and budgets

The asset-only --convert-existing command runs the cached pinned devkitARM
image's tex3ds with --network none, explicit local Docker socket and the
calling uid. It does not compile an application. Every generated uncompressed
RGBA8 tiled payload is compared with the independent existing tiled_rgba8
reference, including T3X envelope and dimensions. All187 texture assets and
26,862,848 GPU bytes pass. Pinned tex3ds canonicalizes hidden RGB when alpha is
zero; original source PNGs remain unchanged, and this policy is explicit.

Keep one current platform resident and evict it for driving. Native per-scene
texture/vertex/combined byte budgets are written in scene.json, with complete
per-texture hashes in native-texture-validation.json. Parent must test actual
heap/linear allocation and rendering; source export does not establish hardware
performance or that every frontend pass has been ported.

Strict native nfs_scene_decode under ASan/UBSan accepts all five scene candidates
and verifies expected source triangle/texture counts and ordered batches via
tests/test_frontend_platforms.c. Private results:
`/workspace/port-research/menu-reference/platform-native-v1/`.
