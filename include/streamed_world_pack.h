#ifndef STREAMED_WORLD_PACK_H
#define STREAMED_WORLD_PACK_H
#include "streamed_world.h"
#include "mw_scene_pack.h"
StreamedWorldResult streamed_world_pack_read(void *pack,StreamedWorldAssetKind kind,
    uint32_t id,const uint8_t identity[32],void *destination,size_t capacity,size_t *bytes);
#endif
