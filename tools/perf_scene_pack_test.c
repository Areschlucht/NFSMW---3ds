#include "mw_scene_pack.h"
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint32_t word(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
int main(int argc,char **argv)
{
    assert(argc==3);MwScenePack pack={0};
    bool reject_open=!strcmp(argv[1],"--reject-open"),reject_read=!strcmp(argv[1],"--reject-read");
    const char *archive=reject_open||reject_read?argv[2]:argv[1];
    MwScenePackResult opened=mw_scene_pack_open(&pack,archive,2*1024*1024);
    if (reject_open) { assert(opened!=MW_SCENE_PACK_OK);assert(!pack.file && !pack.index && !pack.count);return 0; }
    assert(opened==MW_SCENE_PACK_OK);unsigned checked=0;size_t total=0;
    for (uint32_t i=0;i<pack.count;++i) {
        const uint8_t *raw=pack.index+(size_t)i*64;uint32_t kind=word(raw),id=word(raw+4);MwScenePackEntry entry;
        assert(mw_scene_pack_find(&pack,kind,id,raw+8,&entry)==MW_SCENE_PACK_OK);
        size_t size=0;assert(mw_scene_pack_read(&pack,kind,id,raw+8,NULL,0,&size)==MW_SCENE_PACK_OK && size==entry.bytes);
        uint8_t *storage=malloc(size+32);assert(storage);memset(storage,0xa7,size+32);
        assert(mw_scene_pack_read(&pack,kind,id,raw+8,storage+16,size-1,&total)==MW_SCENE_PACK_CAPACITY && !total);
        for (size_t at=0;at<size+32;++at) assert(storage[at]==0xa7);
        MwScenePackResult read=mw_scene_pack_read(&pack,kind,id,raw+8,storage+16,size,&total);
        if (reject_read && read!=MW_SCENE_PACK_OK) { assert((read==MW_SCENE_PACK_CRC || read==MW_SCENE_PACK_IO) && !total);free(storage);mw_scene_pack_close(&pack);return 0; }
        assert(read==MW_SCENE_PACK_OK && total==size);
        for (unsigned at=0;at<16;++at) assert(storage[at]==0xa7 && storage[size+16+at]==0xa7);
        if (!reject_read) {
            char path[1024],identity[65];
            for (unsigned at=0;at<32;++at) snprintf(identity+at*2,3,"%02x",raw[8+at]);
            int length=kind==1?snprintf(path,sizeof(path),"%s/models/%08x.wsm",argv[2],id):
                kind==2?snprintf(path,sizeof(path),"%s/sections/%u.wsi",argv[2],id):
                snprintf(path,sizeof(path),"%s/textures/%08x-%s.wtx",argv[2],id,identity);
            assert(length>0 && (size_t)length<sizeof(path));FILE *source=fopen(path,"rb");assert(source);
            uint8_t scratch[4096];size_t at=0;
            while (at<size) { size_t n=size-at<sizeof(scratch)?size-at:sizeof(scratch);assert(fread(scratch,1,n,source)==n);assert(!memcmp(scratch,storage+16+at,n));at+=n; }
            assert(fgetc(source)==EOF && !ferror(source));fclose(source);
        }
        free(storage);++checked;
    }
    assert(!reject_read);printf("Verified%u packed payloads against original files.\n",checked);
    MwScenePackEntry absent;
    assert(mw_scene_pack_find(&pack,0,0,NULL,&absent)==MW_SCENE_PACK_INVALID);
    assert(mw_scene_pack_find(&pack,3,0,NULL,&absent)==MW_SCENE_PACK_INVALID);
    assert(mw_scene_pack_find(&pack,2,0xffffffffu,NULL,&absent)==MW_SCENE_PACK_NOT_FOUND);
    total=9;assert(mw_scene_pack_read(&pack,2,0xffffffffu,NULL,NULL,0,&total)==MW_SCENE_PACK_NOT_FOUND && !total);
    mw_scene_pack_close(&pack);assert(!pack.file && !pack.index && !pack.count);
    assert(mw_scene_pack_open(&pack,archive,0)==MW_SCENE_PACK_CAPACITY && !pack.file && !pack.index);
    mw_scene_pack_close(&pack);return 0;
}
