#include "perf_vertex20_components.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(int argc,char **argv)
{
    WorldVertex source={.position={-.1f,-0.0f,.3f},.uv={-8,9},.color={.1f,.2f,.3f,.7f}},restored;
    PerfVertexUV32 uv;PerfVertexColor24 color;
    assert(perf_vertex20_uv32_pack(&uv,&source,1));assert(uv.uv[0]==-32768 && uv.uv[1]==-32768);
    perf_vertex20_uv32_unpack(&restored,&uv,1);assert(!memcmp(&source,&restored,sizeof(source)));
    assert(!perf_vertex20_color24_pack(&color,&source,1));
    source.uv[0]=-0.0f;source.uv[1]=.00001f;
    for (unsigned c=0;c<256;++c) {
        source.color[0]=c/255.0f;source.color[1]=128/255.0f;source.color[2]=254/255.0f;source.color[3]=1;
        assert(perf_vertex20_color24_pack(&color,&source,1));
        perf_vertex20_color24_unpack(&restored,&color,1);assert(!memcmp(&source,&restored,sizeof(source)));
    }
    assert(!perf_vertex20_uv32_pack(&uv,&source,1));
    source.uv[0]=0;source.uv[1]=1;source.color[0]=-0.0f;
    assert(perf_vertex20_uv32_pack(&uv,&source,1));assert(!perf_vertex20_color24_pack(&color,&source,1));
    source.color[0]=NAN;assert(!perf_vertex20_uv32_pack(&uv,&source,1));assert(!perf_vertex20_color24_pack(&color,&source,1));
    if (argc==2) {
        FILE *f=fopen(argv[1],"rb");assert(f);assert(!fseek(f,0,SEEK_END));long n=ftell(f);rewind(f);
        uint8_t *raw=malloc((size_t)n);assert(raw);assert(fread(raw,1,(size_t)n,f)==(size_t)n);fclose(f);
        NfsScene scene;assert(nfs_scene_decode(raw,(size_t)n,&scene));free(raw);
        WorldVertex *full=malloc(scene.vertex_count*sizeof(*full)),*roundtrip=malloc(scene.vertex_count*sizeof(*roundtrip));
        PerfVertexUV32 *uvs=malloc(scene.vertex_count*sizeof(*uvs));PerfVertexColor24 *colors=malloc(scene.vertex_count*sizeof(*colors));assert(full && roundtrip && uvs && colors);
        world_vertex_pack(full,scene.vertices,scene.vertex_count);
        assert(perf_vertex20_uv32_pack(uvs,full,scene.vertex_count));perf_vertex20_uv32_unpack(roundtrip,uvs,scene.vertex_count);assert(!memcmp(full,roundtrip,scene.vertex_count*sizeof(*full)));
        assert(perf_vertex20_color24_pack(colors,full,scene.vertex_count));perf_vertex20_color24_unpack(roundtrip,colors,scene.vertex_count);assert(!memcmp(full,roundtrip,scene.vertex_count*sizeof(*full)));
        printf("Both component ablations round-trip all%u world corners exactly.\n",scene.vertex_count);
        free(full);free(roundtrip);free(uvs);free(colors);nfs_scene_free(&scene);
    }
    puts("Component codec checks passed: independent fields, Q12 extrema, all256 byte colours, exact precision and invalid input.");return 0;
}
