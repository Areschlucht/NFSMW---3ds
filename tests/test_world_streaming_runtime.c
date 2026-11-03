#include "world_streaming.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned short read16(const unsigned char *p){return (unsigned short)(p[0]|p[1]<<8);}
static unsigned read32(const unsigned char *p){return p[0]|(unsigned)p[1]<<8|(unsigned)p[2]<<16|(unsigned)p[3]<<24;}
static float readf(const unsigned char *p){unsigned bits=read32(p);float value;memcpy(&value,&bits,4);return value;}
static unsigned char *load(const char *path,size_t *size){
    FILE *file=fopen(path,"rb");assert(file);assert(!fseek(file,0,SEEK_END));long bytes=ftell(file);assert(bytes>0&&bytes<1024*1024);rewind(file);
    unsigned char *data=malloc((size_t)bytes);assert(data);assert(fread(data,1,(size_t)bytes,file)==(size_t)bytes);fclose(file);*size=(size_t)bytes;return data;
}
int main(int argc,char **argv){
    assert(argc==3);size_t bytes,vector_bytes;unsigned char *data=load(argv[1],&bytes),*vectors=load(argv[2],&vector_bytes);
    WorldStreamingDatabase db;assert(world_streaming_open(data,bytes,&db)==WORLD_STREAMING_OK);
    WorldStreamingSelector selector;world_streaming_selector_init(&db,&selector);
    assert(vector_bytes>=8&&!memcmp(vectors,"WSQ1",4));unsigned cases=read32(vectors+4);size_t at=8;
    for(unsigned i=0;i<cases;i++){
        assert(at+12<=vector_bytes);float x=readf(vectors+at),y=readf(vectors+at+4);unsigned id=read16(vectors+at+8),count=read16(vectors+at+10);at+=12;
        assert(count<=147&&at+count*2<=vector_bytes);uint16_t selected=65535;
        assert(world_streaming_select(&db,&selector,x,y,&selected)==WORLD_STREAMING_OK);
        assert(read16(data+db.dependencies+selected*12)==id);
        uint16_t actual[147];size_t n=0;assert(world_streaming_plan(&db,&selected,1,actual,147,&n)==WORLD_STREAMING_OK&&n==count);
        for(size_t j=0;j<n;j++)assert(actual[j]==read16(vectors+at+j*2));
        uint16_t untouched[2]={123,456};size_t required=0;
        assert(world_streaming_plan(&db,&selected,1,untouched,1,&required)==WORLD_STREAMING_CAPACITY);
        assert(required==n&&untouched[0]==123&&untouched[1]==456);
        at+=count*2;
    }
    assert(at==vector_bytes);
    uint16_t untouched=65535;assert(world_streaming_select(&db,&selector,NAN,0,&untouched)==WORLD_STREAMING_INVALID&&untouched==65535);
    assert(world_streaming_select(&db,&selector,1e7f,1e7f,&untouched)==WORLD_STREAMING_NEAREST_REQUIRED&&untouched==65535);
    WorldStreamingSection source;assert(world_streaming_section(&db,141,&source));assert(source.id==141&&source.bytes>0);
    assert(!world_streaming_section(&db,101,&source));
    WorldStreamingResidency residency;world_streaming_residency_init(&residency,1000);
    assert(world_streaming_begin(&db,&residency,141,0)==WORLD_STREAMING_INVALID);
    assert(world_streaming_begin(&db,&residency,141,1001)==WORLD_STREAMING_BUDGET&&residency.used_bytes==0);
    assert(world_streaming_begin(&db,&residency,141,1000)==WORLD_STREAMING_OK&&residency.used_bytes==1000);
    assert(!world_streaming_is_ready(&db,&residency,141));
    assert(world_streaming_begin(&db,&residency,141,1)==WORLD_STREAMING_NOT_READY);
    assert(world_streaming_ready(&db,&residency,141)==WORLD_STREAMING_OK);
    assert(world_streaming_is_ready(&db,&residency,141));
    assert(world_streaming_release(&db,&residency,141)==WORLD_STREAMING_OK&&residency.used_bytes==0);
    assert(!world_streaming_is_ready(&db,&residency,141));
    assert(world_streaming_release(&db,&residency,141)==WORLD_STREAMING_NOT_READY);
    assert(world_streaming_begin(&db,&residency,101,1)==WORLD_STREAMING_INVALID);
    /* Rejected metadata leaves no borrowed database pointer exposed. */
    unsigned char *bad=malloc(bytes);assert(bad);memcpy(bad,data,bytes);bad[28]=255;bad[29]=255;bad[30]=255;bad[31]=255;
    WorldStreamingDatabase rejected;assert(world_streaming_open(bad,bytes,&rejected)==WORLD_STREAMING_INVALID&&!rejected.data);
    memcpy(bad,data,bytes);bad[db.polygons+2]=2;
    assert(world_streaming_open(bad,bytes,&rejected)==WORLD_STREAMING_INVALID&&!rejected.data);
    printf("{\"native_selector_and_plan_cases\":%u,\"metadata_bytes\":%zu,\"selector_state_bytes\":%zu,\"residency_state_bytes\":%zu}\n",cases,bytes,sizeof(selector),sizeof(residency));
    free(bad);free(data);free(vectors);return 0;
}
