# Bounded native world streaming integration checkpoint

The new native module is ready for root review and integration as a selector,
source-range lookup, request planner and budget/readiness bookkeeping component.
It is not a mesh renderer or a complete original asynchronous streamer.

Files:

- `include/world_streaming.h`
- `source_bmw/world_streaming.c`
- `tools/world_streaming_export.py`
- `tools/world_streaming_runtime_verify.py`
- `tests/test_world_streaming_runtime.c`
- `runtime/world-streaming.bin`: 102,718 bytes, SHA256
  `7bd3af44c6617586325f7269b4caf0695a19dbe3d973e7eae48b8cbabdca4d95`.

## Usable interface

1. Load the small WST1 metadata file into normal RAM, keep its bytes alive, and call
   `world_streaming_open`. It validates bounded counts, ranges, source bounds,
   sorted unique section IDs, finite polygons and source references. The full
   109,279,744-byte original stream stays on SD. Source/index SHA256 values are in
   metadata offsets64/96; archive/asset identity must be checked by the packaging
   layer. This module does not hash game assets during each frame.
2. Initialize one `WorldStreamingSelector`. Call `world_streaming_select` with
   absolute original RENDER-SOURCE horizontal(X,Y) coordinates, not collision-native(x,z). Current exporter conversion is
   native `(x,y,z)` to viewer `(x,z,-y)`, so selection uses `(viewer_x,-viewer_z)`
   BEFORE scene normalization/origin subtraction. From collision-native coordinates,
   inputs are `(collisionNative.z,-collisionNative.x)`. Output is a dependency INDEX,
   not a sector ID. The selector retains original move-to-front history.
3. Feed up to two selected dependency indices into `world_streaming_plan`.
   Output is the deduplicated ordered list of exact indexed stream section IDs:
   original mandatory banks2500,2400,2600 precede viewpoint dependency lists.
   Missing logical IDs are skipped by the original normal-mode gather, not
   guessed from a global offset. Capacity147 covers two72-ID lists plus3banks.
   Capacity failure reports required length and writes no partial result.
4. Resolve each physical section through `world_streaming_section`; it returns
   original byte offset/length. The largest raw source slice is936,960 bytes,
   allowing a1MiB input window. That does not bound decoded GPU/texture workspace.
5. Compute desired-vs-resident resources and actual allocation costs from converted
   asset manifests. `world_streaming_begin` requires a nonzero ACTUAL allocation
   charge; unknown costs must not be silently treated as zero. Maintain separate
   `WorldStreamingResidency` instances for normal/linear resident pools. Reserve
   scratch/graphics/car/UI memory outside those resident budgets first. If either
   pool admission fails, undo staged reservations and preserve the prior complete
   region. The module never implicitly evicts existing resources.
6. Read/decode/fix up staged resources, build/upload GPU buffers and prepare collision
   packets. Only after all required consumers are complete call
   `world_streaming_ready`. Expose a section to collision/rendering only when the
   required resource pools and consumer handles are ready. IO completion alone is
   insufficient. Flush GPU data through the existing platform upload path.
7. Release objects only after all model/texture/collision references and GPU-inflight
   uses are gone, then call `world_streaming_release` to clear their budget charge.
   Serialize API calls/completions on the main thread. The caller owns IO queues,
   cancellation, ownership, references, GPU fences and atomic region commit.

Selector state is1,026 bytes; residency bookkeeping5,128 bytes per pool. Database
view is tiny and borrows metadata bytes. No3DS clock/L2 changes are made.

## Original request and readiness evidence

Original gather `0x802BACA4` walks requested IDs, exact-index-looks up each through
`0x802B90C4`, skips absent records, and appends each source record only once per
viewpoint request-bit set. Original caller `0x802BADCC` requests2500/2400/2600
before two viewport region/group lists. Optional ID-remap mode and dynamic special
memberships are not enabled by this component.

Four complete gather results have been compared with executed original PPC,
including absent logical IDs and original ordering. Native plan/selector tests
cover563 sequential real-world queries, including repeated/reversed traversals,
against the previously original-code-verified host policies.

Original `0x802B9888` sets loadedstate3 and dispatches source chunks; requested
sections then register/fix up through `0x802B965C` / `0x801FC654` and reach state4.
Unregister `0x802B9704` transitions4→3; free `0x802B97AC` transitions3→0. The native
UNLOADED/LOADING/READY enum is an application admission contract, not a numerical
relabeling of every original state or a claim that read completion is readiness.

## Collision contract

The collision specialist consumes the SAME exact indexed source section IDs.
`original-render-collision-containment.json` maps all450 physical collision
packages to their containing source section and offsets. No global delta is used.
Duplicate collision IDs must retain source aliases and safe active reference
counts; unregistering one owner must not invalidate another resident alias.

Activation/request lists are not visibility masks. Preserve existing renderer
spatial/frustum culling separately. A desired section is not automatically ready,
and a ready section need not be currently visible.

## Actual memory constraints

Hardware specialist audit:
`/workspace/port-research/hardware-optimization/stream-budget/source-budget.json`.
Original mandatory raw banks total1,264,684 bytes. Worst single-region+mandatory raw
source set is4,895,092 bytes (region717). A separate expanded validated stored-model
estimate reaches9,029,632 bytes (region803), EXCLUDING instance copies, textures,
rejected models and runtime collision. Neither is an allocation budget.

Default libctru linear heap is capped32MiB and can be less under a launcher's
resource allowance, even on New3DS. Measure successfully available normal/linear
arenas after graphics/car/UI initialization, preserve reserves, and reject unknown
converted costs. Do not infer available pools from physical RAM/model name.

## Remaining integration gates

- Nearest-region fallback is explicit `WORLD_STREAMING_NEAREST_REQUIRED`. The caller
  retains the previous complete resident set; no guessed region or road is used.
  Original nearest code is localized at802C0F00/802C0060/80061188, with0.1 distance
  threshold and source point-segment normalization/reciprocal-sqrt details. It is
  not yet translated into native code.
- No converted full-world geometry/texture database is emitted by WST1. This
  metadata selects source ranges; a bounded asset exporter/loader must preserve
  original4-slot LOD bindings, same-hash bank variants, material flags and original
  packet/placement semantics. Never preload every mesh into RAM.
- Original distance LOD selection, dynamic special groups, prediction and full
  scheduling/eviction remain separate original-policy gates.
- The clean opt-in `decode_model(...allow_triangle_statistic_mismatch=True)` is now
  used by the recovery diagnostic. Source bytes are no longer privately patched.
  Default strict readers stay strict; all consumed geometry constraints remain.
- Eight consumed texture hashes and21 model-reference hashes remain unresolved in
  the currently scanned banks. Do not replace these with invented original assets.

## Validation

`native-runtime-verification.json` records563 native selector/plan cases and four
executed-original gather cases. Native build uses-Wall-Wextra-Werror-pedantic,
-fno-fast-math,-ffp-contract=off, ASan and UBSan. Tests include malformed ranges/counts,
invalid polygons, capacity/no-partial-output behavior, zero/overbudget admission,
loading/ready/release transitions and invalid source IDs.20 relevant Python tests
pass after switching the diagnostic to the clean decoder opt-in.

Root main/build/runtime asset files were not edited by this specialist.
