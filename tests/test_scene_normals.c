#include "nfs_scene.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned word(const unsigned char *p){return p[0]|(unsigned)p[1]<<8|(unsigned)p[2]<<16|(unsigned)p[3]<<24;}
static void put(unsigned char *p,unsigned v){for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(v>>(8*i));}
static void checksum(unsigned char *p,size_t bytes){unsigned c=~0u;for(size_t i=32;i<bytes;i++){c^=p[i];for(unsigned j=0;j<8;j++)c=(c>>1)^(0xedb88320u&(0u-(c&1)));}put(p+24,~c);}
int main(int argc,char **argv)
{
    assert(argc==2);FILE *f=fopen(argv[1],"rb");assert(f);assert(!fseek(f,0,SEEK_END));long n=ftell(f);assert(n>32);rewind(f);
    unsigned char *raw=malloc((size_t)n);assert(raw);assert(fread(raw,1,(size_t)n,f)==(size_t)n);fclose(f);
    NfsScene scene;assert(nfs_scene_decode(raw,(size_t)n,&scene));assert(word(raw+4)==1);
    unsigned start=32+(word(raw+12)+word(raw+16))*16,old_rejected=0;
    for(unsigned i=0;i<scene.vertex_count;i++) {
        assert(!memcmp(scene.vertices[i].normal,raw+start+i*32+12,12));float squared=0;
        for(unsigned a=0;a<3;a++)squared+=scene.vertices[i].normal[a]*scene.vertices[i].normal[a];
        if(squared<.98f || squared>1.02f)++old_rejected;
    }
    assert(old_rejected);printf("Preserved %u source normals exactly; %u fell outside old reconstructed-normal window.\n",scene.vertex_count,old_rejected);nfs_scene_free(&scene);
    const float invalid[][3]={{0,0,0},{.98f,0,0},{1.03125f,0,0},{NAN,0,1}};
    for(unsigned i=0;i<sizeof invalid/sizeof *invalid;i++) {
        memcpy(raw+start+12,invalid[i],12);checksum(raw,(size_t)n);assert(!nfs_scene_decode(raw,(size_t)n,&scene));
    }
    const float quantized[3]={36.0f/64,36.0f/64,36.0f/64};
    memcpy(raw+start+12,quantized,12);checksum(raw,(size_t)n);assert(nfs_scene_decode(raw,(size_t)n,&scene));
    assert(!memcmp(scene.vertices[0].normal,quantized,12));nfs_scene_free(&scene);free(raw);
    puts("Nonquantized, zero, nonfinite and oversized normals rejected; bounded original S8/64 accepted.");return 0;
}
