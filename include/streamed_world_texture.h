#ifndef STREAMED_WORLD_TEXTURE_H
#define STREAMED_WORLD_TEXTURE_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
/* Source RGBA rows retain their orientation. Output is PICA RGBA8 (ABGR bytes,
   row-major8x8 Morton tiles). UV1-v is already applied during vertex expansion.
   zero_transparent_rgb is an OFFLINE Tex3DS comparison policy; productionfalse
   preserves original hiddenRGB for filtered cutout edges. Buffers must not overlap. */
bool streamed_world_texture_rgba8(uint8_t *output,size_t capacity,
    const uint8_t *rgba,unsigned width,unsigned height,unsigned alpha_test,unsigned blend,
    bool zero_transparent_rgb);
#endif
