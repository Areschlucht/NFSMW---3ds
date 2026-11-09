#ifndef MW_FRONTEND_TOP_H
#define MW_FRONTEND_TOP_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
enum { MW_FRONTEND_TOP_WIDTH=400,MW_FRONTEND_TOP_HEIGHT=240,
       MW_FRONTEND_TOP_BYTES=400*240*2,MW_FRONTEND_TOP_TEXTURE_BYTES=512*256*4 };
typedef struct { uint16_t x,y,advance;uint8_t width,height;int8_t left;uint8_t top; } MwFrontendGlyph;
/* Borrows immutable NUT1 bytes, which must outlive rendering. No allocation. */
typedef struct { const unsigned char *data,*background,*font,*logo;size_t bytes;MwFrontendGlyph ascii[128]; } MwFrontendTop;
typedef struct {
    const char *page;       /* e.g. MAIN MENU or QUICK RACE */
    const char *alias;      /* selected original-style Alias, not an implementation ID */
    const char *selection; /* selected car/route or page context */
    const char *detail;    /* short status; avoid backend diagnostics in normal menus */
} MwFrontendTopModel;
bool mw_frontend_top_open(MwFrontendTop *,const void *,size_t);
/* Rotated RGB565 output, matching existing UI convention. Draw this opaque
   full-screen canvas BEFORE the top-screen 3D car. It never draws over 3D. */
bool mw_frontend_top_render(const MwFrontendTop *,unsigned char *,size_t,const MwFrontendTopModel *);
/* For C3D_TexInit(512,256,GPU_RGBA8), full-canvas C2D subtexture400x240.
   Pack/upload only when page/Alias/selection changes, outside an active frame
   after FrameSync. This function allocates nothing and changes no GPU state. */
bool mw_frontend_top_pack(void *,size_t,const unsigned char *,size_t);
#endif
