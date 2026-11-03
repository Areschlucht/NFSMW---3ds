#ifndef MW_COLOR_GRADE_H
#define MW_COLOR_GRADE_H

#include <stdbool.h>
#include <stdint.h>

/* Optional "Piss filter" artistic approximation, not a recovered original LUT.
 * The caller defaults enabled=false. Neutral mode is an exact pass-through.
 */
enum {
    MW_COLOR_GRADE_RED = 246,
    MW_COLOR_GRADE_GREEN = 255,
    MW_COLOR_GRADE_BLUE = 201
};

/* Restore the current scene pipeline once per frame before world/car draws.
 * Owns TEV stages0..5: stage0 texture0 * primary; stage1 optional RGB grade;
 * stages2..5 pass through. Alpha, depth, blending and vertex shaders retain
 * their existing meanings. Call before scene geometry, not a UI overlay;
 * an overlay renderer must configure its own stage0 and pass-through tails.
 */
void mw_color_grade_apply(bool enabled);

/* Framebuffer clear convention is 0xRRGGBBAA (unlike TEV packed constants).
 * Apply the same RGB gains, nearest-byte rounding; alpha is unchanged.
 * GPU TEV quantization can differ from CPU clear rounding by a byte.
 */
uint32_t mw_color_grade_clear(uint32_t rgba, bool enabled);

#endif
