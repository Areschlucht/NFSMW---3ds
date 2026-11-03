#include "world_index.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void verify(const NfsVertex *source,size_t count,const WorldIndexedVertices *indexed)
{
    assert(indexed->index_count==count);
    for (size_t i=0;i<count;++i) {
        WorldVertex packed;world_vertex_pack(&packed,&source[i],1);
        assert(indexed->indices[i]<indexed->vertex_count);
        assert(!memcmp(&packed,&indexed->vertices[indexed->indices[i]],sizeof(packed)));
    }
}
int main(int argc,char **argv)
{
    NfsVertex vertices[6]={0};
    for (unsigned i=0;i<6;++i) {
        vertices[i].position[0]=(float)(i%3)/10;
        vertices[i].uv[1]=(float)(i%3)/4;
        vertices[i].color[3]=1;
    }
    NfsVertex original[6];memcpy(original,vertices,sizeof(vertices));WorldIndexedVertices indexed;
    assert(world_index_encode(vertices,6,&indexed)==WORLD_INDEX_OK);
    assert(indexed.vertex_count==3);verify(vertices,6,&indexed);
    assert(!memcmp(original,vertices,sizeof(vertices)));world_index_free(&indexed);world_index_free(&indexed);
    vertices[0].position[0]=0;vertices[3].position[0]=-0.0f;
    vertices[4].color[0]=nextafterf(1.0f,0.0f);
    assert(world_index_encode(vertices,6,&indexed)==WORLD_INDEX_OK);
    assert(indexed.vertex_count==5);verify(vertices,6,&indexed);world_index_free(&indexed);
    assert(world_index_encode(NULL,6,&indexed)==WORLD_INDEX_INVALID);
    assert(world_index_encode(vertices,5,&indexed)==WORLD_INDEX_INVALID);
    vertices[0].color[0]=NAN;assert(world_index_encode(vertices,6,&indexed)==WORLD_INDEX_INVALID);
    assert(!indexed.vertices && !indexed.indices && !indexed.vertex_count && !indexed.index_count);
    NfsVertex *many=calloc(65538,sizeof(*many));assert(many);
    for (unsigned i=0;i<65538;++i) { many[i].position[0]=i*.00001f;many[i].color[3]=1; }
    many[65536]=many[0];many[65537]=many[1];
    assert(world_index_encode(many,65538,&indexed)==WORLD_INDEX_OK);
    assert(indexed.vertex_count==65536 && indexed.indices[65535]==65535);verify(many,65538,&indexed);world_index_free(&indexed);
    many[65537].position[0]=.9f;
    assert(world_index_encode(many,65538,&indexed)==WORLD_INDEX_OVERFLOW);
    assert(!indexed.vertices && !indexed.indices && !indexed.vertex_count && !indexed.index_count);free(many);
    if (argc==2) {
        FILE *f=fopen(argv[1],"rb");assert(f);assert(!fseek(f,0,SEEK_END));long n=ftell(f);assert(n>32);rewind(f);
        unsigned char *raw=malloc((size_t)n);assert(raw);assert(fread(raw,1,(size_t)n,f)==(size_t)n);fclose(f);
        NfsScene scene;assert(nfs_scene_decode(raw,(size_t)n,&scene));free(raw);
        assert(world_index_encode(scene.vertices,scene.vertex_count,&indexed)==WORLD_INDEX_OK);verify(scene.vertices,scene.vertex_count,&indexed);
        /* Batch boundaries remain index offsets, and every material's exact
           ordered vertex stream can be reconstructed without changing batches. */
        for (unsigned b=0;b<scene.batch_count;++b) {
            NfsBatch batch=scene.batches[b];assert(batch.first+batch.count<=indexed.index_count);
            for (unsigned i=batch.first;i<batch.first+batch.count;++i) {
                WorldVertex packed;world_vertex_pack(&packed,&scene.vertices[i],1);
                assert(!memcmp(&packed,&indexed.vertices[indexed.indices[i]],sizeof(packed)));
            }
        }
        printf("Actual world: %u -> %u vertices; %zu -> %zu GPU bytes including u16 indices; all ordered material streams reconstruct exactly.\n",scene.vertex_count,indexed.vertex_count,(size_t)scene.vertex_count*sizeof(WorldVertex),(size_t)indexed.vertex_count*sizeof(WorldVertex)+(size_t)indexed.index_count*sizeof(uint16_t));
        nfs_scene_free(&scene);world_index_free(&indexed);
    }
    puts("Index encoder checks passed: exact bytes, signed zero, low-bit colour, source preservation, u16 boundary/overflow fallback, invalid input and cleanup.");return 0;
}
