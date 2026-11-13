#ifndef MW_MENU_ICONS_H
#define MW_MENU_ICONS_H
#include "mw_menu_layout.h"
#include <stdint.h>
typedef struct { const unsigned char *data;size_t bytes; } MwMenuIcons;
typedef struct { const unsigned char *rgba;unsigned width,height;uint32_t source_hash; } MwMenuIcon;
/* Immutable NMI1 bytes stay alive until shutdown. Source art is genuine; port
   role assignments/layout are documented adaptations, not FEng reconstruction. */
bool mw_menu_icons_open(MwMenuIcons *,const void *,size_t);
bool mw_menu_icon_find(const MwMenuIcons *,MwMenuAction,MwMenuIcon *);
/* Overlay four source-art icon buttons on an existing rotated320x240 RGB565
   framebuffer. Caption/footer text is rendered by the caller using its font.
   No heap/GPU calls. Exactly153600 output bytes are required. */
bool mw_menu_icons_render(const MwMenuIcons *,const MwMenuLayout *,unsigned char *,size_t);
#endif
