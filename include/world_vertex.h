#ifndef WORLD_VERTEX_H
#define WORLD_VERTEX_H
#include "nfs_scene.h"
/* World lighting is baked RGB: no normal fetch or runtime normal lighting. */
typedef struct { float position[3],uv[2],color[4]; } WorldVertex;
void world_vertex_pack(WorldVertex *out,const NfsVertex *source,size_t count);
#endif
