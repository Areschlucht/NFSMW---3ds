# Rendering checkpoint: base materials and optional grade

The user-requested default is neutral. `mw_color_grade_apply(false)` restores the existing texture-times-primary scene output exactly, and `mw_color_grade_clear(color,false)` is byte-identical. The UI owns the literal optional label `Piss filter` and initializes its model false.

## Implemented isolated integration

New files `include/mw_color_grade.h` and `source_bmw/mw_color_grade.c` expose:

```c
void mw_color_grade_apply(bool enabled);
uint32_t mw_color_grade_clear(uint32_t rgba, bool enabled);
```

Call apply once at render start before scene world/car geometry. Pass clear color through the clear helper with the same boolean. No vertex uniforms, geometry formats, shader instruction counts, draw calls, render targets or texture reads are added. The module owns TEV stages0..5 in the current scene pipeline: stage0 is texture0 * primary for RGB and alpha; stage1 optionally multiplies only RGB by constant `(246,255,201)/255`; alpha is PREVIOUS/REPLACE; stages2..5 pass through. Disabled stage1 is also PREVIOUS/REPLACE. These gains are an explicitly provisional artistic approximation, not recovered original color coefficients or LUT.

The TEV constant is packed `0xFFC9FFF6` using PICA `0xAABBGGRR`, while framebuffer-clear API uses `0xRRGGBBAA`. The clear helper preserves alpha and rounds nearest. TEV framebuffer quantization may differ by a byte. The grading stage does not change alpha test, depth write, standard/additive blend state or vertex programs.

Restore all scene stages each frame because another renderer can leave state behind. A future top-screen UI overlay must establish its own TEV pipeline/pass-through tails and draw after scene grading. The current bottom-screen text console is a separate framebuffer, so it is unaffected. Per-fragment multiplication commutes with ordinary alpha blending in ideal linear unsaturated arithmetic; additive saturation and fixed-point rounding mean this is not an exact final-frame postprocess. Avoid describing it as one.

Verification: strict devkitARM compile against the installed real citro3d headers passed `-std=c11 -Wall -Wextra -Werror -O2 -march=armv6k -mtune=mpcore -mfloat-abi=hard -mtp=soft -D__3DS__`. Mock state regression tests start poisoned, inspect all6stages, preserve alpha, toggle warm→neutral→warm and exhaust every clear alpha byte. Repo tests/test_mw_color_grade.c uses tests/color_grade_support/citro3d.h; the fake never participates in production builds.

```sh
cc -std=c11 -Wall -Wextra -Werror -Iinclude -Itests/color_grade_support source_bmw/mw_color_grade.c tests/test_mw_color_grade.c -o /tmp/test_mw_color_grade
/tmp/test_mw_color_grade
```

## Original base rendering evidence

Keep the world 13-instruction vertex shader's original baked RGB. It intentionally omits generated normals and inspection light because the original world mesh already contains lighting. World original TexInfo byte85/86 determines alpha-test/blend mode; existing recovery distinguishes opaque/source-alpha/additive. Do not re-light all baked world vertices to imitate the warm grade.

The car shader currently generates triangle normals, applies an absolute two-sided directional dot product in eye space, and uses ambient/diffuse .5/.5. Its own comments call this inspection lighting. This is a material fidelity gap separate from optional grading: camera-dependent illumination, absent original vertex-normal/smoothing evidence, paint/reflection/gloss composition and window/light runtime alias targets still require recovered consumers. A larger per-vertex light shader cannot cure a missing original generated paint source.

The material checkpoint has now recovered the actual M3GTRCAREERSTART preset, PSRTEST texture/mask, base metal paint183gray/GLOSS128, original mask/128 blend and exact native RGB5A3 CPU adapter/packback. The separate canonical-skin-native-preview output preserves fourth-byte data and opaque diffuse. It improves source fidelity while keeping the remaining indexed edge quantizer and reflection/specular pipeline explicitly open. Do not bake gloss into diffuse opacity or use BMW_24 just because its name sounds plausible; the original preset selects PSRTEST.

## Actual original post-effect data, not a guessed RGB LUT

`tools/material_recovery_render.py` exports all5original visuallook rows with field source SHA/offset/raw bytes to original-visuallook-evidence.json. Original default ColourBloomTint is `[.863,.98,.078,1]`, intensity1.5, desaturation.627, black bloom intensity.25. These are bloom inputs, not direct RGB gain multipliers. Curves have exact VLT hash labels ColourBloomCurve, BlackBloomCurve and DetailMapCurve, each four Vec4 rows. Original scalar function802E6548 evaluates a cubic Bernstein combination of their Y values. Original GC calls at8010F20C/22C populate a64x64lookup texture from two such curves, with input0..63 divided by64. Semantic binding of that texture's channels, the later multi-pass sampling/blending and dynamic look transitions are not fully transcribed. No exact original 3D color LUT is claimed.

A faithful future base-material progression is: recover original normals/material constants and texture composition; establish world-space directional/ambient inputs and original environment source selection; then map specular/reflection/gloss terms to PICA lighting/TEV. Maintain a measured stock-clock budget and change one visible material effect at a time. Optional warm grading remains independent and defaults off throughout. The current grade requires no more user files. Exact car material/paint work can continue with the newly supplied native bundle; original lighting context may need the actual active look/environment consumers, not another indiscriminate art upload.
