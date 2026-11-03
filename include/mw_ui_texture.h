#ifndef MW_UI_TEXTURE_H
#define MW_UI_TEXTURE_H
#include <stdbool.h>
#include <stddef.h>
enum { MW_UI_TEXTURE_WIDTH=512,MW_UI_TEXTURE_HEIGHT=256,MW_UI_TEXTURE_BYTES=512*256*4 };
/* Rotated 320x240 RGB565 canvas -> PICA tiled ABGR8. Unused texels are opaque
   black. No allocation or SDK dependency; texture upload is caller-fenced. */
bool mw_ui_texture_pack(void *destination,size_t bytes,const unsigned char *canvas,size_t canvas_bytes);
#endif
