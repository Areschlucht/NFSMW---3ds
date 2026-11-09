#ifndef MW_DESTINATION_ICONS_H
#define MW_DESTINATION_ICONS_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
/* Authentic USA GC mini-map glyphs. Role assignment is the 3DS overlay contract;
   original 3D emitter, animation and original mini-map consumer are not ported. */
typedef struct { const unsigned char *data;size_t bytes; } MwDestinationIcons;
typedef struct { const unsigned char *rgba;unsigned width,height;uint32_t source_hash; } MwDestinationIcon;
bool mw_destination_icons_open(MwDestinationIcons *,const void *,size_t);
/* NFD1 kinds:1 safehouse,2 customshop,3 carlot,4 race. Only original race
   types0/P2P and1/circuit have verified corresponding source glyphs here. */
bool mw_destination_icon_find(const MwDestinationIcons *,unsigned kind,int32_t original_event_type,MwDestinationIcon *);
/* Tight RGB8 canvas, no allocation. Icon is centered at x/y and clipped safely.
   Unknown kinds/types and invalid buffers fail without writes. */
bool mw_destination_icon_blit(const MwDestinationIcons *,unsigned kind,int32_t original_event_type,
    unsigned char *rgb,size_t bytes,unsigned width,unsigned height,int x,int y);
#endif
