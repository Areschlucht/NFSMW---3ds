# Free-roam arrow correction and two-screen destination integration

This integration supersedes the context-zero and blocked-free-roam state shown
in the earlier race-menu preview. The user authorized building and emulator
screenshots after the source checkpoint. This is an unfinished native port.

## Shared activation state

`mw_world_state` reads a bounded, CRC-checked NWS1 sidecar with stream/gameplay
source digests, the original normal draw context0x10, active collision groups
and sparse expected-source/effective instance flags. The renderer rejects a
source-word mismatch transactionally. Both consumers borrow the same immutable
state. Group0 ordinary scenery stays admitted. Nonzero collision groups follow
the original group-table admission rule, without deleting C0 walls or assets.

The current shortcut is explicitly **unlocked exploration**, using the original
cold Bin1 operations. It suppresses all8,763 track-barrier provider occurrences.
The original Bin15/16 career plans retain their legitimate district locks; those
plans are not applied to the exploration shortcut. No guessed unlock thresholds
or per-Alias career completion are introduced.

NWS1 currently supports the cold-plan0x10 flag overrides only. A test-only
group3 plan proves the former blocker can be restored, including its render
flags and collision. This is not a completed per-event race activation system.
The separately recovered0x400 matrix reflection remains available for that work.

## Destinations and screen roles

`mw_free_roam` loads161 original destination records:146 race entries, eight
customization shops, four safehouses and three car lots. The original source
positions/radii and explicit references are retained. Current distance-based
D-pad Up prompts are a 3DS interaction adaptation, not the original actor-shape
trigger implementation or an original career availability/unlock filter.

Race entries resolve original event names and prepare the existing session;
starting a race is explicitly unavailable. Parts-shop categories open, but
purchase/economy/tuning remains unavailable. Safehouses open the new navigation;
Jump to Safe House opens frontend mode2 as the recovered original callback does.
No nearest-house teleport is invented. Car lots currently lead to the BMW garage,
without a purchasing or complete car-selection system. Pause/resume and returning
from a destination retain the current car state instead of resetting the spawn.

The top screen uses the original logo/font/background artwork with a live3D car
and Alias/page/selection context. Bottom-screen angled selection rows carry
navigation and touch input. It is a new two-screen adaptation. An exact Nintendo
DS layout, original frontend scene/materials/transitions and full menu sounds
are not claimed. Texture uploads remain outside active frames after a GPU fence;
the CPU does not paint directly into the displayed bottom framebuffer.

The small NFI1 sidecar adds the authentic original mini-map glyphs for safehouse,
customization shop, car lot, P2P and circuit. Icons use the same north-up source
coordinate projection as the existing road map, and the player arrow is drawn
above them. Unknown race modes have no substituted icon. This is a documented
3DS overlay binding; the original mini-map-specific consumer and3D marker effects
remain unported. Road coverage in this minimap still comes from the partial NRD.

## Validation

- Pinned devkitARM build compiled/linked `nfsmw-exploration-preview.3dsx`.
- ASan/UBSan regression removes actual group3 `BARRIER_SPLINE_458`, preserves a
  normal group0 wall, retains career groups and restores group3 on activation.
- Actual renderer/collision/provisional driving ran600 fixed-step frames:
  118.57 source-distance units, versus51.63 in the former unfiltered probe.
  Later ordinary walls still block; this is not an autonomous complete-city run.
- Four original safehouse respawns admit renderer and collision within the same
  12MiB normal/20MiB linear budgets and find ordinary group0 ground. Draw-run
  counts were1390,1570,1345 and155; these are host workload counts, not FPS.
- Destination tests cover all161 centers, original type counts, malformed CRC,
  NaN and no-match behavior. Frontend tests cover guarded layouts, malformed
  assets and every packed texture texel.
- Actual Azahar reached the new title/main menu, arrow-free starting road,
  drove beyond the former initial obstruction, opened pause/Jump to Safe House,
  and resumed at the advanced position. Captures are actual native pixels,
  cropped from the desktop, with no generated or reconstructed gameplay images.
- Separate emulator admission probes started at the actual original shop
  EB9E71EB and race-entry5D93BF20 centers, then used D-pad Up. They reached Parts
  Shop/categories and original-titled `Hwy 4 & Clubhouse` preparation respectively.
  These shots test source-location admission and interaction; they are not a claim
  that an automated driver traversed from the starting road to those locations.
  `NFS_DESTINATION_PROBE_KEY` is absent from the packaged executable.
- Five paused-menu bottom-screen crops have identical SHA256
  da697c493d53c054f26291da635ce1f7817138a1fd72236f0f1709a1c9eb2600.
  This is an emulator stability check, not proof of every hardware flicker fixed.
- The preexisting streamed integration suite also passes:40 failed region-change
  rollback/recovery cycles, missing/CRC/provider failures, source normals, ordered
  draws and all17,260 packed payload comparisons. Icon tests pass35 guarded alpha
  draws, extreme clipping coordinates and recomputed-CRC structural corruptions.

The authored race activation exporter now supplies all82 supported source course
plans against both exploration and early-career bases. The original event loop
and conditional entry reset are verified; ordinary exit ordering remains open.
See race-activation.md. This is retained source work, not yet a live race mode.

Emulator counters do not establish stock3DS performance. Handling/camera,
whole-city route traversal, races/AI/rewards, original sound/story/cutscenes,
complete shops and complete car roster remain unfinished.

Reproduction uses `tools/build_free_roam_activation.py`,
`tools/build_world_state.py`, `tools/build_free_roam_destinations.py`,
`tools/build_frontend_top_assets.py`, `tests/test_world_activation.c` and
`tools/test_free_roam.sh`. Original inputs and converted sidecars stay private.

To recreate the test-only group3 reactivation fixture, copy the Bin1 JSON,
append an argument0 operation for group3, and set its mapped instance flags to
`original_flags & ~0x10` using the exported `instances[].group_id` (group3).
Rebuild sorted `overrides` from changed original/effective pairs and pack with
`build_world_state.py`. Keep this fixture separate from exploration.nws and
exclude it from the user installation. It is a controlled reactivation test,
not a recovered complete race configuration.
