#include "nfs_scene.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void put(uint8_t *p,uint32_t v)
{ for (unsigned i=0;i<4;++i) p[i]=(uint8_t)(v>>(8*i)); }
static void update_crc(uint8_t *data,size_t size)
{
    uint32_t crc=0xffffffff;
    for (size_t i=32;i<size;++i) {
        crc^=data[i];for (unsigned b=0;b<8;++b) crc=(crc>>1)^((0-(crc&1))&0xedb88320);
    }
    put(data+24,~crc);
}
int main(int argc,char **argv)
{
    assert(argc==2 || argc==3);FILE *file=fopen(argv[1],"rb");assert(file);
    assert(!fseek(file,0,SEEK_END));long length=ftell(file);assert(length>32);rewind(file);
    size_t size=(size_t)length;uint8_t *data=malloc(size),*copy=malloc(size);assert(data&&copy);
    assert(fread(data,1,size,file)==size);fclose(file);NfsScene scene;
    assert(nfs_scene_decode(data,size,&scene));
    assert(scene.vertex_count==15744 && scene.batch_count==16 && scene.texture_count==16);
    assert(scene.vertices[0].position[0]>=-1.01f && scene.vertices[0].position[0]<=1.01f);
    for (unsigned i=0;i<4;++i) assert(scene.vertices[0].color[i]==1);
    nfs_scene_free(&scene);
    memcpy(copy,data,size);put(copy+32+12,5);update_crc(copy,size);
    assert(nfs_scene_decode(copy,size,&scene));assert(scene.textures[0].flags==5);nfs_scene_free(&scene);
    put(copy+32+12,4);update_crc(copy,size);assert(!nfs_scene_decode(copy,size,&scene));
    put(copy+32+12,8);update_crc(copy,size);assert(!nfs_scene_decode(copy,size,&scene));
    assert(!nfs_scene_decode(NULL,size,&scene));assert(!nfs_scene_decode(data,size,NULL));
    assert(!nfs_scene_decode(data,31,&scene));assert(!nfs_scene_decode(data,size-1,&scene));assert(!nfs_scene_decode(data,size+1,&scene));
    memcpy(copy,data,size);copy[size-1]^=1;assert(!nfs_scene_decode(copy,size,&scene));
    memcpy(copy,data,size);put(copy+32+4,7);update_crc(copy,size);assert(!nfs_scene_decode(copy,size,&scene));
    memcpy(copy,data,size);put(copy+32+16*16+8,16);update_crc(copy,size);assert(!nfs_scene_decode(copy,size,&scene));
    memcpy(copy,data,size);put(copy+32+16*16+16*16,0x7fc00000);update_crc(copy,size);assert(!nfs_scene_decode(copy,size,&scene));
    memcpy(copy,data,size);put(copy+32+16*16,200000);update_crc(copy,size);assert(!nfs_scene_decode(copy,size,&scene));
    assert(nfs_scene_decode(data,size,&scene));nfs_scene_free(&scene);nfs_scene_free(&scene);
    /* A v2 scene adds explicit per-vertex RGBA while v1 defaults to white. */
    size_t first=32+16*16+16*16,nv=15744,size2=size+nv*16;
    uint8_t *colored=calloc(1,size2);assert(colored);
    memcpy(colored,data,first);put(colored+4,2);put(colored+20,(uint32_t)(size2-32));
    for (size_t i=0;i<nv;++i) {
        uint8_t *v=colored+first+i*48;memcpy(v,data+first+i*32,32);
        put(v+32,0x3e800000);put(v+36,0x3f000000);put(v+40,0x3f400000);put(v+44,0x3f800000);
    }
    update_crc(colored,size2);assert(nfs_scene_decode(colored,size2,&scene));
    assert(scene.vertices[0].color[0]==.25f && scene.vertices[nv-1].color[2]==.75f);
    nfs_scene_free(&scene);
    put(colored+first+32,0x7fc00000);update_crc(colored,size2);assert(!nfs_scene_decode(colored,size2,&scene));
    put(colored+first+32,0x3f900000);update_crc(colored,size2);assert(!nfs_scene_decode(colored,size2,&scene));
    put(colored+first+32,0xbe800000);update_crc(colored,size2);assert(!nfs_scene_decode(colored,size2,&scene));
    assert(!nfs_scene_decode(colored,size2-1,&scene));free(colored);
    free(data);free(copy);
    if (argc==3) {
        file=fopen(argv[2],"rb");assert(file);assert(!fseek(file,0,SEEK_END));length=ftell(file);rewind(file);
        assert(length>32);size=(size_t)length;data=malloc(size);assert(data);assert(fread(data,1,size,file)==size);fclose(file);
        assert(nfs_scene_decode(data,size,&scene));assert(scene.texture_count>64 && scene.texture_count<=NFS_MAX_TEXTURES);
        printf("Expanded world: %u textures, %u vertices\n",scene.texture_count,scene.vertex_count);nfs_scene_free(&scene);
        put(data+16,NFS_MAX_TEXTURES+1);update_crc(data,size);assert(!nfs_scene_decode(data,size,&scene));free(data);
    }
    puts("NFM scene checks passed: bounds, CRC, dimensions, batches, nonfinite vertices, extended texture limit and cleanup.");
    return 0;
}
