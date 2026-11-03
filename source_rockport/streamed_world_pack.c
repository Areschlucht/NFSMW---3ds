#include "streamed_world_pack.h"
StreamedWorldResult streamed_world_pack_read(void *pack,StreamedWorldAssetKind kind,
    uint32_t id,const uint8_t identity[32],void *destination,size_t capacity,size_t *bytes)
{
    unsigned resource;
    switch(kind){
    case STREAMED_WORLD_MODEL:resource=MW_SCENE_PACK_MODEL;break;
    case STREAMED_WORLD_SECTION:resource=MW_SCENE_PACK_SECTION;break;
    case STREAMED_WORLD_TEXTURE:resource=MW_SCENE_PACK_TEXTURE;break;
    default:return STREAMED_WORLD_INVALID;
    }
    switch(mw_scene_pack_read(pack,resource,id,identity,destination,capacity,bytes)){
    case MW_SCENE_PACK_OK:return STREAMED_WORLD_OK;
    case MW_SCENE_PACK_IO:return STREAMED_WORLD_IO;
    case MW_SCENE_PACK_MEMORY:return STREAMED_WORLD_BUDGET;
    case MW_SCENE_PACK_NOT_FOUND:return STREAMED_WORLD_MISSING;
    case MW_SCENE_PACK_CAPACITY:return STREAMED_WORLD_CAPACITY;
    case MW_SCENE_PACK_CRC:return STREAMED_WORLD_FORMAT;
    default:return STREAMED_WORLD_INVALID;
    }
}
