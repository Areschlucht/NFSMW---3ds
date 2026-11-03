#include "perf_vertex20.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(int argc,char **argv)
{
    WorldVertex source={.position={.1f,-0.0f,.3f},.uv={-8,9},.color={0,1/255.0f,254/255.0f,1}};
    PerfVertex20 packed;WorldVertex restored;
    assert(perf_vertex20_pack(&packed,&source,1));assert(packed.uv[0]==-32768 && packed.uv[1]==-32768);
    perf_vertex20_unpack(&restored,&packed,1);assert(!memcmp(&source,&restored,sizeof(source)));
    for (unsigned c=0;c<256;++c) {
        source.color[1]=c/255.0f;assert(perf_vertex20_pack(&packed,&source,1));
        assert(packed.color[1]==c);perf_vertex20_unpack(&restored,&packed,1);assert(!memcmp(&source,&restored,sizeof(source)));
    }
    source.color[1]=.1f;assert(!perf_vertex20_pack(&packed,&source,1));
    source.color[1]=0;source.uv[0]=.00001f;assert(!perf_vertex20_pack(&packed,&source,1));
    source.uv[0]=-0.0f;assert(!perf_vertex20_pack(&packed,&source,1));
    source.uv[0]=0;source.color[1]=-0.0f;assert(!perf_vertex20_pack(&packed,&source,1));
    source.color[1]=NAN;assert(!perf_vertex20_pack(&packed,&source,1));
    assert(!perf_vertex20_pack(NULL,&source,1));assert(!perf_vertex20_pack(&packed,NULL,1));
    assert(!perf_vertex20_pack(&packed,&source,0));
    if (argc==2) {
        FILE *f=fopen(argv[1],"rb");assert(f);assert(!fseek(f,0,SEEK_END));long n=ftell(f);assert(n>32);rewind(f);
        uint8_t *raw=malloc((size_t)n);assert(raw);assert(fread(raw,1,(size_t)n,f)==(size_t)n);fclose(f);
        NfsScene scene;assert(nfs_scene_decode(raw,(size_t)n,&scene));free(raw);
        WorldVertex *full=malloc(scene.vertex_count*sizeof(*full)),*roundtrip=malloc(scene.vertex_count*sizeof(*roundtrip));
        PerfVertex20 *compact=malloc(scene.vertex_count*sizeof(*compact));assert(full && roundtrip && compact);
        world_vertex_pack(full,scene.vertices,scene.vertex_count);
        assert(perf_vertex20_pack(compact,full,scene.vertex_count));
        perf_vertex20_unpack(roundtrip,compact,scene.vertex_count);
        assert(!memcmp(full,roundtrip,scene.vertex_count*sizeof(*full)));
        printf("Actual world: all %u corners round-trip byte-exactly, including original unflipped Q12 UVs and RGBA8.\n",scene.vertex_count);
        free(full);free(roundtrip);free(compact);nfs_scene_free(&scene);
    }
    puts("Vertex20 CPU codec checks passed: extrema, flip overflow, every byte-colour level, signed zero, nonrepresentable and invalid input.");return 0;
}
