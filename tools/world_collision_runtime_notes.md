# Activating original collision alongside streamed Rockport sections

The implementation is `include/world_collision_runtime.h`, `source_bmw/world_collision_runtime.c`, and `source_bmw/world_collision_query.c`. It loads original quantized geometry, original collision instances and material keys; it does not derive building boxes from rendered scenery. It currently accepts the observed identity CI basis/orientation case and rejects unsupported transforms during packing/loading.

Generate the data from the user's private original stream and the streaming specialist's strict containment manifest:

```sh
python tools/world_collision_pack.py STREAML2RA-full.BUN original-render-collision-containment.json rockport-collision.nwc
```

The current full-world file is **5,797,152 bytes**, SHA256 `3db8a855c9b862d02d6095cc89c85736dfcd5534a00602b3a66680cfbc9acc7d`. It contains 390 unique collision packages and 450 exact physical stream-section associations. Original BE CA banks and full 64-byte CI records are preserved; compact LE directory entries provide bounded access. Source aliases retain their actual original physical byte offsets in query provenance. The source stream SHA is stored in the file header. Do not commit the generated game-data file.

The context uses 28,760 host bytes (target `sizeof` may differ slightly), plus caller-provided ordinary RAM for the active collision cache. stdio owns its normal FILE/buffering state. Queries perform no allocation or file I/O. A **1 MiB** arena covers every recovered normal one/two-viewpoint dependency plan: measured worst 380,848 bytes for one viewpoint and 684,608 bytes across all pairs of the 435 original dependency lists. These figures exclude graphics, textures, car, audio, UI and future special-group changes. The complete-world validation uses a separate 6 MiB host arena; runtime should activate its selected sections.

## Shared coordinate and readiness contract

Collision native world is `(x,y,z)`, with **Y up**. Existing exporter viewer world is `(nativeZ,nativeY,nativeX)`. NRD1 `RoadWorld.origin` is already in that viewer world frame; its road/car positions are local meters, before display scaling. Position helpers use that origin; normal/vector conversion uses only the axis swap.

`world_streaming_select` takes original **render-source horizontal(X,Y)**, which is `(collisionNative.z, -collisionNative.x)`. It does not take collision-native `(x,z)`.

A concrete admission sequence, using the independently verified streaming module:

```c
static WorldCollisionRuntime collision; /* zero-initialized */
static unsigned char collision_cache[1024 * 1024];

int status = world_collision_runtime_open(&collision, collision_path,
    collision_cache, sizeof collision_cache);
/* Handle status before enabling queries. Close before reopening this context. */

float native[3];
world_collision_viewer_to_native(car_local_meters, road_world.origin, native);
uint16_t dependency, sections[147];
size_t section_count;
/* Check every return: outside the recovered contained-region branch, the
   streaming selector explicitly asks to retain the last complete resident set. */
world_streaming_select(&database, &selector, native[2], -native[0], &dependency);
world_streaming_plan(&database, &dependency, 1, sections, 147, &section_count);

WorldCollisionAdmission admission;
status = world_collision_runtime_admit(&collision, sections, section_count, &admission);
/* Budget failure preserves the existing ready collision set. Keep the complete
   previous render/texture/collision set until the next plan can be admitted. */
if (status == 0) {
    status = world_collision_runtime_activate(&collision, sections, section_count, &admission);
}
/* Publish the new scene only when graphics, textures AND collision are ready.
   Activation is blocking: schedule in the application's load/admission phase. */
```

The example omits the application's error/UI handling; do not ignore streaming or collision return codes. Exact physical indexed section IDs flow into activation. No `sectionID-40` rule is used. IDs without collision data are counted as `sections_without_collision`, because many valid graphics/texture sections contain no collision bank.

Admission reports total `required_bytes`, `required_read_bytes`, unique packages and retained packages. Common packages survive section changes with zero reads; the cache compacts retained data in ascending old physical address before loading new data. Traversal follows the requested logical section order. Alias-only changes update physical source provenance without reloading identical data. Budget/argument rejection leaves the old cache usable. Once a load begins, an I/O, checksum or semantic-validation failure clears readiness so partial/stale data cannot be queried. Calls must be serialized by the application's main/load thread.

## Query outputs and remaining physics linkage

```c
WorldCollisionContact contact;
int hit = world_collision_runtime_ground(&collision, native_query_point, 0, &contact);
if (hit == 1) {
    float local_point[3], local_normal[3];
    world_collision_native_to_viewer(contact.point_native, road_world.origin, local_point);
    world_collision_native_vector_to_viewer(contact.normal_native, local_normal);
    /* Resolve contact.material_key against original simsurface attributes.
       Feed a wheel solver only after its original point/velocity/load frame
       producers are connected. This API does not invent those producers. */
}
```

Ground queries choose the nearest **strictly below** original candidate, retaining original mesh bounds, radius quantization, strip winding, exclusions, material index and attribute bytes. The returned ground normal is the original query-plane producer with upward Y clamp `0.9999`; this is explicitly **not yet proven to be the original wheel-force normal producer**. The caller must supply the proper original wheel/query point. This API does not secretly offset a wheel probe, replace missing surfaces or extrapolate a road.

`world_collision_runtime_wall` takes native world segment endpoints and returns closest original vertical-wall contact point/normal. Original normals face the segment start and use rounded transformed world endpoints multiplied by the stored local inverse length. No guessed bounce, car impulse, drift damping or chassis response is applied.

Material keys are the original on-disc hashes. Seventeen keys directly join original simsurface rows; zero and two other keys still require original fallback-resolution tracing. Do not replace an unknown material with invented grip values. Inputs include the original exclusion mask: mask meaning depends on the original query consumer; a general physical vehicle-wall mask has not been assumed.

The runtime applies proven original `0x802EE544` load-time prop mutations: CI+0x18 nonzero sets associated wall flag bits `0xC0`, and also CI flags for meshless assets. Full raw CI bytes remain preserved. Dynamic breakable/event state, collision-list activation beyond the requested streamed packages, original outer spatial-list tie order and rigid-body response are still unresolved. Current tests establish geometry/query/material provenance, not a completed 1:1 driving engine.

## Validation

Public tests: `python -m unittest discover -s tests -p 'test_world_collision*.py'` (15 tests), plus standalone C regressions. Runtime tests cover bounded admission, strict no-contact below/on ground, nearest surfaces, original flag mutation, cache retention/reordering/compaction, physical aliases, corrupted data checksums, invalid pointers with recomputed CRC, readiness recovery and coordinate conversion. Host C also passes ASan/UBSan and warnings-as-errors.

Private source-dependent evidence is under `/workspace/port-research/map-collision/runtime/`. The runtime-vs-original differential activates exact containing sections and compares against actual uploaded USA PPC routines: 201 ground +207 wall queries, zero selected hit/geometry/material/source-provenance mismatches; max ground gap error `5.96e-8 m`, query-normal component error `1.79e-7`, and wall point/normal errors zero. Original ground normalization uses a checksum-pinned external Dolphin Gekko reciprocal-estimate model; portable runtime uses ordinary `sqrtf`. These are emulator-reference results, not console timing or full GameCube bit-parity claims.
