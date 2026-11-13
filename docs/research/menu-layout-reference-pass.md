# Original-art icon menus and changing top-screen car framing

The supplied reference images combine GameCube menu identity with the Nintendo
DS screen-role split. New portable modules implement a 3DS adaptation: bottom
touchable icon buttons and top current-car framing. They do not implement the
original FEng interpreter or reproduce a recovered DS layout pixel for pixel.

## Original frontend icons

`build_menu_icons.py` reads the pinned decoded USA FRONTEND-FRONTB.BUN, SHA256
bc3c7c33d8b2620deaa5506da8c43c7cecd6fa5ea3d3f369d8baf4bbee753920, and verifies the
USA DOL identity. Thirteen full-name/hash matches select genuine source pixels:
Career, Quick Race, Car Select, Challenge Series, Profile Manager, Options,
Resume Career, New Career, Resume Race, Parts, Performance, Visual and Arrow.
Long source texture record names are truncated, so the full label's original
hash is checked independently rather than matching just a shared name prefix.

`menu-icons.nmi` is198,176 bytes. NMI1 has a128-byte header,13 fixed32-byte
records and contiguous original RGBA8 pixels. Header fields are version@4,
total-size@8, CRC32@12 over bytes16..end, count@16, records-offset@20,
pixels-offset@24 and stride@28. Source FRONTB/DOL digests occupy32..63/64..95;
reserved96..127 must be zero. The reader rejects changed source identities,
unknown action/hash/dimension/range tuples, nonzero reserved fields and CRC errors
before publishing its borrowed immutable view.

Source pixels are not invented. Assigning Resume Race to the port's Resume Free
Roam action and Arrow to Main Menu are explicit new role bindings, not proved
original FEng button assignments. All original artwork and private sidecars stay
outside Git.

## Native controls and composition

`mw_menu_layout` accepts a caller-owned ordered action list, preserving parent
page policy instead of inventing eligibility. Up to16 actions use a four-button
sliding window. Buttons have stable70x98 touch bounds at x8,86,164,242 and y68.
A button tap immediately selects and activates its explicit action; empty screen
space does nothing. Footer arrows at x0..31/288..319,y177..206 only move selection.
Controller left/right uses the same wrapping selection helper.

`mw_menu_icons_render` overlays original icons and ordinary new panel geometry on
the existing rotated320x240 RGB565 canvas. There are no heap/GPU calls. Parent
renders original-font headings, selected caption at y181, detail at y201 and
footer at y221; keep caption between x32 and288 to avoid navigation arrows.
Current selection is raised and enlarged. Player/car ownership is never stored
inside the UI helper, and no BMW name/model is hardcoded.

`mw_menu_camera_focus/step` supplies changing page-dependent framing instead of
constant idle orbit. Interrupted transitions begin from the current pose and
use a bounded0.48-second smoothstep with shortest-yaw interpolation. These values
are explicit handheld framing choices, not claimed original GameCube constants.
Original FE_ATTRIB angle rows were found independently, but their consumers and
units must be proved before importing them as original camera behavior.

## Host checks

`tests/test_menu_layout.c`, compiled with strict C11 warnings and ASan/UBSan,
checks24 direct touch actions across all six main-menu windows, wrapping,
empty/gap touch suppression, malformed action lists, all16 framing actions,
frame-step-independent endpoints and interruption continuity. Six rendered
layouts preserve framebuffer guards. Native icon tests also cover104 structural
mutations with recomputed CRC, corrupt headers/source identity, unsupported
lookups and truncated buffers. No SDK application build or emulator result is
claimed by these portable checks; parent integrates and validates those layers.

Private inputs/results:
`/workspace/port-research/menu-reference/icons-v1/`.
