# Source-art frontend across both 3DS screens

This subtask provides a concrete portable top-screen compositor and native asset,
not a replacement for the root's shared frontend controller. No main-loop,
bottom-screen renderer, GPU runtime, SDK build or commit was changed here.

## Division of responsibilities

The requested direction is the 2005 game's visual identity with a useful
handheld two-screen division: the top display supplies the logo, active Alias,
page context, selected car/route and live 3D vehicle; the bottom display carries
navigation and touch selection. This is a new 3DS adaptation. It is not presented
as a recovered one-to-one GameCube or Nintendo DS layout.

An attempt to inspect the actual Nintendo DS GamesDatabase page returned HTTP403:
https://www.gamesdatabase.org/game/nintendo-ds/need-for-speed-most-wanted . No DS
menu screenshot or manual was successfully reviewed in this subtask. Consequently
the two-screen role division is user-requested inspiration, not evidence that
these precise positions, labels, art or transitions occur in the DS release.

## Actual original artwork

`tools/build_frontend_top_assets.py` accepts only the previously verified
original-art NUI2, SHA256
`b8bee03d7491f54c0f8854c1bfea1bfdc3056540d518075bc26661530d0e4be2`.
It reuses the actual FONT_MW_BODY alpha atlas/metrics and MW_LOGO RGBA pixels.
The background is the existing documented source-art composition (original
WS_MWSPLASHBACK/TREAD/LOAD_SPLATTER), resized from320x240 to400x240 for the wider
3DS display. The background is not claimed to be a recovered original frontend
scene; parent 3D rendering remains responsible for the live vehicle.

No generated race image, replacement typeface, invented graffiti texture or
baked 3D vehicle is introduced. Procedural translucent UI panels/divider lines
are ordinary new layout geometry, not purported original game assets.

Private generated files:
`/workspace/port-research/frontend-two-screen/native-v1/`:

- frontend-top.nut:326,012-byte NUT1 asset with original-art provenance digest.
- provenance.json: source and output hashes, layout limits and host verification.
- top-0.png, top-1.png, top-2.png: compositor-only host previews, not emulator
  captures. The live 3D car is intentionally absent from these previews.

The original logo's RGBA SHA256 remains
`f621d740b62a7d1bbd0c26a428bf53676c813cafe308182ea5cb733ca0f46cf6`.
The direct body-alpha copy's SHA256 is
`03aec80cb55299a893a0e4188e3c6093cbbd4f0e7d57def9de4db1ac1623bc1d`.

## Native API and integration

`mw_frontend_top_open` strictly validates NUT1 magic/version/dimensions, exact
layout/size, payload CRC, reserved bytes, unique glyphs, glyph/atlas bounds and
all required ASCII metrics before publishing a borrowed immutable view. Failure
leaves the caller's view unchanged. Keep the source bytes alive until shutdown.

`mw_frontend_top_render` draws a400x240 rotated RGB565 canvas from that view and
`MwFrontendTopModel { page, alias, selection, detail }`. There are no runtime image
decoder, heap allocations, random decoration or GPU calls. Names use the actual
body font including lowercase and punctuation, with clipped width and bounded
96-character text work. The car area remains free of controls. Full-canvas redraw
is intended only when page/Alias/selection changes, not every frame.

`mw_frontend_top_pack` converts the canvas into512x256 tiled opaque ABGR8, exactly
524,288 bytes. Root can use C3D_TexInit(512,256,GPU_RGBA8) and an existing-style
C2D subtexture width400/height240, left0/top1/right400.f/512/bottom1-240.f/256.
Unused texture texels are opaque black. CPU canvas costs192,000 bytes, the GPU
texture524,288 bytes, plus326,012 immutable asset bytes and a small view.
No additional per-frame allocations/uploads are required.

Suggested order for a menu frame:

1. Outside an active frame, fence prior GPU work with C3D_FrameSync, render/pack
   a dirty canvas and flush its texture.
2. Clear/draw the top render target once and draw the opaque C2D backdrop quad.
3. C2D_Flush, then restore car shader, attributes, projection/model uniforms,
   alpha/blend/depth state and the normal car TEV/color-grade configuration.
   C2D changes TEV; restoring only a shader program is insufficient.
4. Draw the existing 3D car over the backdrop, preserving normal source textures.
5. Present the existing bottom menu/HUD separately. Never CPU-paint into the
   displayed LCD framebuffer during scanout.

Do not clear the top target again between steps2 and4. A source-art backdrop
must not cover driving/world rendering; enable it only in frontend/garage views
as decided by root. Correct material, reflection, original animation and menu
sound recovery remain separate work.

## Verification and reproduce

```sh
python tools/build_frontend_top_assets.py \
  --nui /workspace/port-research/ui-dual-screen/v0.18-original-art/ui.nui \
  --output-directory /workspace/port-research/frontend-two-screen/native-v1 \
  --verify-host
```

Host compilation uses strict C11 warnings. Three guarded page models render
without framebuffer writes beyond their bounds; wrong canvas size is rejected
without writes. Seven malformed asset cases are rejected, including a bad glyph
whose CRC is recomputed so the structural check is reached. All131,072 GPU texels
are compared against an independent bit-interleaving implementation, including
padding and RGB565 expansion. The NUT1 file is refused if an existing output has
different bytes. Python syntax and scoped whitespace checks pass.

This does not assert SDK compilation, emulator display, hardware memory budget,
performance, complete 1:1 frontend style or original DS behavior. Root should
validate the actual combined 2D backdrop/3D car and bottom menu after integration.
