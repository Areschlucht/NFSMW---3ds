#ifndef ROAD_MAP_H
#define ROAD_MAP_H
#include "road_contact.h"
typedef struct { unsigned char *pixels;float center_x,center_z,step; } RoadMap;
bool road_map_init(const RoadWorld *world,RoadMap *out);
void road_map_free(RoadMap *map);
bool road_map_render(const RoadMap *map,const RoadWorld *world,const DriveState *car,
                     unsigned char *rgb,unsigned width,unsigned height);
/* Redraw player above destination glyphs using the same north-up projection. */
bool road_map_player_overlay(const DriveState *,unsigned char *rgb,unsigned width,unsigned height);
/* Straight-line warning only; does not alter driving or generate ground. */
bool road_edge_ahead(const RoadWorld *world,const DriveState *car,float height);
/* Bottom console: rotated 320x240 RGB565 framebuffer, not RGB8. */
bool road_map_blit565(const unsigned char *rgb,unsigned width,unsigned height,
                      unsigned char *framebuffer,size_t bytes,unsigned left,unsigned top);
#endif
