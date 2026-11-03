# Original Rockport collision recovery checkpoint

This recovers original game collision data and isolated original local query primitives. It does **not** make the current 3DS build a full city port or add vehicle/body collision response. No existing renderer, driving, packaging, or scene builder files were modified by this specialist.

## Verified source

Full original STREAML2RA.BUN: 109,279,744 bytes; SHA256 `58fdd0adb8bdf1ebc3545ee679076c768acb3c52308c4b916ca960b4a0ac5552`.
Original USA Speed.dol SHA256 `33c5eae699f871beac059b6932475cad5e9f610bb2b2298e046d043757b94166`.
Always map DOL virtual addresses through its section table: late data sections do not share the common VA/file offset.

## Recovered data and space requirements

`tools/world_collision.py` strictly validates all 450 physical original collision packages (chunk 0x0003B801), their CARP resource bounds, assets, instances, quantized strips, wall bank records and material indices. All 9,326 physical instances use identity observed bases; raw bases/translation/flags are retained.

Physical inventory: 9,326 assets/instances, 49,022 quantized parts, 308,132 triangle candidates, 57,075 wall records. These are physical archive counts, including exact duplicate packages.

All 60 repeated package IDs are **byte-identical copies**, not alternate content. Content-addressing yields 390 unique packages: 7,531 assets/instances, 38,352 quantized parts, 242,794 triangle candidates, 45,803 wall records. Original compressed/packed collision chunks occupy 7,284,544 physical bytes or 5,795,264 unique bytes. These counts do not include render geometry/textures/runtime structures.

`tools/map_recovery_collision_manifest.py` emits every original source byte range, content SHA, duplicate aliases, material primitive counts and native/viewer source-point bounds without flattening the world into one mesh. See `collision-streaming-manifest.json`. Bounds are transformed original mesh vertices and wall endpoints; they are **not** activation volumes or invented solid blockers. Collision package IDs must not be equated to render section IDs. Original activation/linking rules still need tracing.

## Source format and original consumers

Loader 0x801FCFB8 dispatches chunk0x3B801 to0x802EE710. CARP parsing0x802EEE70/802EEF1C; instance fixup0x802EF084; material resolution0x802EEFFC→0x80278C98.

Collision wrapper is little endian four u32; CARP and asset internals big endian. Root starts16 bytes after aligned wrapper. Arti directory entries16 bytes: tag, packed size/relative flag, item count, offset relative to its own descriptor. Validated resources Name, ca+u16 local index, ci+u16 group. Executable supports co112-byte records, but none observed in this full stream; decoder rejects them until independently supported.

CA16-byte header `>4H2BHI`: mesh part count, mesh bytes, wall record count, wall bytes, fixed flag, material count, material bytes, raw token. Resource size rounds used banks to64 bytes. Mesh and wall banks can coexist. Preserve arbitrary padding; it is not necessarily zero.

Mesh bank starts with16-byte nodes: float center3, u16 radius, u16 strip offset relative to asset+16. Vertex strip8-byte records: signed16 xyz decoded center+q/128 (original0x802EF290), plus metadata. First metadata u16 is vertex count; second is flags; each subsequent byte6 is material index and byte7 triangle attributes. Consecutive triples are original triangle candidates. Original broadphase radius is u16/16, rounded down; full-stream points fit within next quantum. Do not discard strip orientation/attribute bytes.

Wall32-byte records: endpointA float3, material index byte12, flags byte13, rawu16 byte14, endpointB float3 byte16, inverse horizontal XZ length float byte28. Every original inverse validates against endpoint length; maximum relative residual9.718e-8. Flags observed2,6,18; rawu16 observed0x347c. Endpoint geometry and field sizes are established; vertical extents and original segment selection were subsequently proven by executable reference (see second checkpoint below). Contact/response assembly remains unresolved.

CI64-byte records: basisX at0, extentX12, rawu32 at16 (low16 orientationflags at18), extentY20, rawu16 at24, local asset index26, runtime pointer28, basisZ32, extentZ44, **world-to-local translation**48, metric60. Decoder keeps all these raw values.

## Coordinate proof

Original0x802EDF84 constructs a four-row matrix. Flags&3=0 gives rows basisX, unitY, basisZ, translation. Original point-transform leaf0x80193498 evaluates a row vector and **adds** translation. Thus source identity CI inverse is local−translation. General inverse helper handles scale, reflection and shear instead of blindly negating translation. Unobserved nonzero orientation flags are rejected until the original cross-product construction branch is referenced.

Native collision y is up. Native→current viewer is `(z,y,x)`; native→original render source is `(z,-x,y)`.

`point-transform-reference.json`: bounded interpreter executes actual uploaded84-byte paired-single transform leaf; 9,326 original placements and10,000 exact dyadic affine cases pass. Max binary32-reference vs binary64 affine output difference0.236511mm. This interpreter is scoped to its supported unquantized operations and does not claim exact Gekko FMA tie/FPSCR/NaN/subnormal emulation.

`render-collision-overlap.json`: all5,483 existing road render triangle centroids covered by original collision mesh; median height difference3.1916mm, p95 20.547mm, max98.2895mm; all within10cm. Wrong reflected transform only covers3,821/5,483 and medianerror385mm. These are evidence of original geometry registration, not evidence that game collision response is complete.

## Original local candidate query now portable

`include/world_collision_query.h` / `source_bmw/world_collision_query.c` implement only original0x802EF290's point→strip triangle candidate primitive. Input is validated original BE strip bytes, node center, local point and exclusion mask; output raw triangle corners, material index/attributes and triangle index. No heap allocation, scene scanning or guessed forces.

Verified semantics:
- `(exclusionMask & stripFlags)!=0` rejects entire strip.
- Triangle attributes bit8 always skipped; `(exclusionMask & attributes)!=0` also skips.
- Strip bit0 chooses projected winding and toggles each triangle.
- Strip bit1 accepts either projected orientation, but requires `min(vertexY)<pointY+1.0`.
- Returns the first accepted candidate in original strip order; it does not itself cast a ray or solve suspension height.

`tools/map_recovery_strip_reference.py` runs the uploaded original PPC routine under bounded Unicorn. It skips only paired-single f31 stack save/restore (preserved incoming value irrelevant to output); scalar decode, floating arithmetic, branches and metadata copying all execute original instructions. Requires the pinned executable SHA; no original bytes bundled. Original routine SHA `0918f93c11e01423a2899f1878aae84a59ef8bfd01b62641ae7171877f319554`.

`strip-query-differential.json`:10,460 sampled original strip/mask/height cases across the full stream, including flags0/1/2:9,117 hits; zero hit/material/attribute/corner mismatches, maximum output vertex difference0. Boundary/FPSCR exhaustive equivalence is not claimed; The C implementation explicitly uses fmaf for projected edges to preserve original fused multiply/subtract order; complete FPSCR/subnormal/NaN and compiler-mode equivalence is not claimed.

Top-level0x802F0364 applies CI world→local, extent and node-radius checks, calls candidate primitive, computes/normalizes a normal, chooses a height under additional filters, transforms output and resolves material. This larger function remains to be fully referenced. Its normal is flipped to nativeY≥0; source axes are established. The observed identity-CI local point path is now referenced below, while full ray/suspension consumer linkage remains unresolved.

## Surface link

Twenty unique original collision material keys;17 directly join original ATTRIBUTES simsurface row keys: asphalt, concrete, cobble, gravel, grass, dirt, grass_shoulder, asphalt_no_leaves, railroad, stone, golf_rough, glass, golf_green, wood, metal, golf_fairway, sand. Unresolved0,0x33199393,0x4BB72BD3. See `surface-key-join.json` and driving specialist's actual47-row `surface-values.json`. Preserve keys rather than introducing guessed friction numbers.

Driving specialist independently traced actual simsurface pointer provenance and original tire force multipliers DRIVE_GRIP+236/LATERAL_GRIP+240; do not assume GROUND_FRICTION/WORLD_FRICTION are tire coefficients without their consumer traces.

## Validation and remaining work

12 Python parser/DOL/transform/manifest tests pass. Portable C query regression executable passes with AddressSanitizer+UndefinedBehaviorSanitizer and `-Wall -Wextra -Werror`. Reference probes are private source-data-dependent research scripts, not required by public synthetic unit tests.

Remaining before faithful runtime collision: full top-level point/ray/contact query semantics and bounds; original instance activation association to renderer sections; unknown material fallback resolution; original wall query geometry/filtering; native collision normal/contact output frame and wheel/body consumers; collision response and static/dynamic props. Complete original Rockport stream is now available, so no additional source bytes are needed merely to continue this research.

## Second checkpoint: per-instance ground and original wall selection

`world_collision_mesh_point_below` now reconstructs original0x802F0364's observed flags&3==0 path in native local coordinates. It preserves CI XZ half-extent rejection, original floor-quantized node-radius broadphase (strict distance²<radius²), strip masks/order, upward normal,0.9999 upper Y clamp, original plane height, strict positive gap and closest-node selection, plus min(vertexY)−0.5<queryY bound. It deliberately uses ordinary sqrtf rather than embedding a third-party Gekko estimate table.

`top-query-c-differential.json`: actual original per-instance point query vs portable C on1,336 source asset/mask/height cases:802 hits, zero selected-triangle/material/attribute/corner differences; max gap error0.000000238419m (0.239 micrometers). This tests the real query under a model, not the original game's whole wheel suspension/response.

`tools/map_recovery_contact_reference.py` now provides the original top-level bounded PPC reference with explicitly interpreted paired-single operations. It accepts a caller-supplied pinned external frsqrte estimate model. Tests used actual Dolphin FloatUtils reference commit86d554802d7560acf12b5c5a2b3acb344069b5ce (adapter from driving specialist), while the original Newton refinement/scalar operations continue to execute. No GPL reference source/tables or original executable bytes enter runtime code. PS uses binary64 intermediates rounded binary32, so FMA ties/FPSCR/subnormals remain explicit model boundaries. The ordinary-sqrt portable candidate passed the above corpus against this Gekko estimate model.

Original0x802F3E6C wall-bank selection is also executing from the supplied DOL. Reference stops at0x802F4000 before output/contact-response assembly. Original0x803078E4 computes the XZ segment intersection and interpolates query Y. Parallel determinant exactlyzero rejects; determinant-numerator comparisons use original constants±0.0001, not an invented parameter-space epsilon. The wall selection loop applies `(exclusionMask & wallFlags)==0`, requires **strictly** min(endpointY)<intersectionY<max(endpointY), then chooses closest squared distance from segment start. This proves that the two stored opposite wall endpoints span a vertical face, rather than an inferred building box. Source orientation is retained; query selection itself accepts segment crossings from either direction. Separate body contact paths can still be one-sided.

`world_collision_wall_bank_segment` implements that native local single-bank selection, retaining material/flags/index and selected point. `wall-query-differential.json`:3,225 actual source bank/mask/height cases, all observed wall flags2/6/18 covered;1,427 hits; zero hit/selected-wall/material/flag/point differences, maximum point difference0. Public C synthetic tests cover closest-hit order, reversed segment, masks, strict height endpoints, malformed ranges and nonfinite inputs; ASan/UBSan pass.

Caller responsibilities remain explicit: original CI transformation, scene activation, original material resolution and original load-time flag mutation. Original0x802EE544 detects CI+0x18!=0 and ORs0xC0 into associated wall flags; for meshless assets it also ORs0xC0 into CI+0x12. Across physical source data1,083 CI records have this field nonzero,1,081 are meshless and10,566 walls are affected. Decoder preserves on-disc bytes; source-only queries have not silently invented runtime mutations. This may link destructible props, but that interpretation is not yet proven.

Original0x802EE710 indexes global table pointer0x80438F68 by packageID*4, loads CARP when absent and calls registered callbacks `(ID,1)`. Unload0x802EE7FC calls `(ID,0)` and removes it. This proves ID-keyed load/unload callbacks; render-sector dependency mapping remains the streaming specialist's open task.

Original ground wrapper0x803082D4 calls per-instance point query, picks nearest candidate and invokes0x80308F20. That routine uses triangle material index at+0x2C to index the fixed-up material table `asset+16+meshBytes+wallBytes` and stores resolved pointer at ground-state+0x38. Driving specialist has this exact bridge for tracing wheel-contact input. Other CI orientations use0x802F0818 instead; the current source all has low orientationflags0.

Next gate for runtime: combine proved local queries with original activation/material/contact consumers, then verify original wall contact-normal/response assembly and dynamic-prop behavior. No body impulses, wall bounce or road support implementation has been wired into the 3DS viewer by this specialist.

## Third checkpoint: full original segment-wall contact output

Original0x802F3E6C is now referenced through its complete return (routine SHA256 `f6d9436b68fd27ef178b254136f59f2549ffcf3e2c546c182ee4136d24d3c170`), including original contact-point transform, world normal orientation and material-token selection. `OriginalContactReference.query_wall_contact` runs that path; `query_wall_bank` retains the narrower selection-stop mode for isolation.

The separate portable `world_collision_wall_contact_normal` mirrors original0x802F4184..0x802F420C. Inputs must be **world floats after CI inverse**: normal=`((B.z-A.z)*storedLocalInv,0,(A.x-B.x)*storedLocalInv)`, then flip if dot(queryStart−worldHit,normal)<0. Original uses stored *local* inverse length after transforming endpoints; deriving a normal from untransformed local endpoints loses the original world-subtraction rounding. No additional renormalization is invented.

`wall-contact-differential.json`:3,870 original full segment-wall queries,2,072 hits, both segment directions, masks/heights, all source flags2/6/18; **zero** hit/world-point/world-normal/material-token differences. This validates contact-query output, not vehicle/body impulses, collision integration or dynamic prop response. Source material table entries remain on-disc keys in this probe; original material-fixup consumer identity is traced separately.

Final checkpoint tests:12 Python tests pass; expanded standalone C tests cover strip, nearest point-below surface, strict ground gap, source broadphase bounds, closest wall selection, masks, strict vertical endpoints, world normal facing and invalid inputs. Host C passes `-O2 -Wall -Wextra -Werror -fsanitize=address,undefined`; original reference comparisons are source-data-dependent private probes. All differential JSONs record final C source/header SHA256. No 3DS viewer/runtime/build packaging files were edited; toolchain target compilation and real-device performance for this isolated query module remain integration work.

## Runtime activation checkpoint

A concrete integration API is now implemented in `include/world_collision_runtime.h` / `source_bmw/world_collision_runtime.c`, with reproducible packer `tools/world_collision_pack.py` and usage contract `tools/world_collision_runtime_notes.md`. No main/controller/build file was modified.

Full source NWC1 artifact is5,797,152 bytes, SHA256`3db8a855c9b862d02d6095cc89c85736dfcd5534a00602b3a66680cfbc9acc7d`. It retains original CA banks/full CI records and exact450-section→390-unique-package containment; aliases retain actual requested source offsets. Runtime cache loading strictly checks version/count/ranges/CRC/source records and applies actual0xC0 prop flag mutations. Admission failure preserves old ready cache; load failure clears readiness. Common packages compact safely in place and survive transitions with zero reads; native queries allocate nothing and perform noI/O. Context is28,760 host bytes, separate from caller-owned collision arena and stdio buffer state.

Collision cache budgets measured exhaustively across all435 recovered normal dependency lists: one-view max380,848B, median149,456B; all two-viewpoint pairs max684,608B.1MiB covers this recovered normal-mode collision workload. These are collision bytes, not render/texture/whole-process budgets. Complete-world all390-package ASan/UBSan smoke uses5,779,200B in a separate6MiB host arena.

Source-dependent runtime differential:201 ground +207 wall queries across exact containing source sections versus actual original per-instance outputs aggregated in sourceCI order, including loader flag mutations. Zero hit/geometry/material/source-offset mismatches. Ground maxgap error5.96e-8m, querynormal error1.79e-7; wall worldpoint/normal errors0. See runtime/runtime-original-differential.json. Portable normals use ordinary sqrtf; original reference uses external pinned Dolphin Gekko estimate model.

15 public Python/C runtime tests pass, plus ASan/UBSan runtime/query regressions. Both C modules compile with existing pinned devkitARM image, ARMv6K/MPCore hard-float, O2/warnings-as-errors. Root independently verified WST original region/plan→NWCactivation→all5,483 road triangle centroids within1MiB, all5,483 groundhits and maxrender/collisionheightdelta0.0982971m; maxactivecollision176,992B. Root report is /workspace/port-research/rockport/v0.18-dev/world-runtime-bridge.json.

Shared coordinate contract: selector uses original render-source horizontal(X,Y)=(collisionNative.z,−collisionNative.x). NRD1 origin is already viewerWorld=(nativeZ,nativeY,nativeX); viewer local meters convert through provided helpers. Do not use collision-native(x,z) directly as streaming-selector coordinates, and do not apply display scale to physical query coordinates.

Next authorized specialist stage is original static car-body shape/contact-response recovery, beyond these proved queries; no guessed wall impulse or full1:1 handling claim.
