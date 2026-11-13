#include "vehicle_index.h"
#include "wheel_motion.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static NfsVertex base_vertex(void)
{ return (NfsVertex){.normal={0,1,0},.color={1,1,1,1}}; }
static void set_x_bits(NfsVertex *v,uint32_t bits)
{ memcpy(&v->position[0],&bits,sizeof(bits)); }
static uint32_t independent_hash(const NfsVertex *v)
{
    const unsigned char *p=(const unsigned char *)v;uint32_t h=2166136261u;
    for(unsigned i=0;i<48;i++)h=(h^p[i])*16777619u;
    return h;
}
static void reconstruction(const NfsVertex *source,size_t count,const VehicleIndexedVertices *indexed)
{
    assert(indexed->index_count==count&&indexed->vertex_count&&indexed->vertex_count<=65535);
    uint32_t next=0;
    for(size_t i=0;i<count;i++){
        uint16_t index=indexed->indices[i];assert(index<indexed->vertex_count);
        assert(!memcmp(&source[i],&indexed->vertices[index],48));
        if(index==next){assert(!memcmp(&source[i],&indexed->vertices[next],48));next++;}
        else assert(index<next);
    }
    assert(next==indexed->vertex_count);
}
static void *load(const char *name,size_t *bytes)
{
    FILE *f=fopen(name,"rb");assert(f&&!fseek(f,0,SEEK_END));long n=ftell(f);assert(n>0);rewind(f);
    unsigned char *data=malloc((size_t)n);assert(data&&fread(data,1,(size_t)n,f)==(size_t)n);assert(!fclose(f));*bytes=(size_t)n;return data;
}
static uint32_t word(const unsigned char *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static void real_scene(const char *folder)
{
    char path[1024];assert(snprintf(path,sizeof(path),"%s/body.nfm",folder)>0);size_t bytes;unsigned char *raw=load(path,&bytes);NfsScene scene;
    assert(nfs_scene_decode(raw,bytes,&scene));uint32_t body_crc=word(raw+24);free(raw);
    assert(snprintf(path,sizeof(path),"%s/wheels.nwa",folder)>0);raw=load(path,&bytes);WheelRig rig;
    assert(wheel_rig_decode(raw,bytes,scene.batch_count,body_crc,&rig));free(raw);
    NfsBatch *batches=malloc(scene.batch_count*sizeof(*batches));uint8_t *groups=malloc(scene.batch_count);assert(batches&&groups);
    memcpy(batches,scene.batches,scene.batch_count*sizeof(*batches));memcpy(groups,rig.groups,scene.batch_count);
    VehicleIndexedVertices indexed={0},again={0};
    assert(vehicle_index_encode(scene.vertices,scene.vertex_count,&indexed)==VEHICLE_INDEX_OK);reconstruction(scene.vertices,scene.vertex_count,&indexed);
    assert(vehicle_index_encode(scene.vertices,scene.vertex_count,&again)==VEHICLE_INDEX_OK);
    assert(again.vertex_count==indexed.vertex_count&&again.index_count==indexed.index_count);
    assert(!memcmp(again.indices,indexed.indices,indexed.index_count*2)&&!memcmp(again.vertices,indexed.vertices,indexed.vertex_count*48));
    assert(!memcmp(batches,scene.batches,scene.batch_count*sizeof(*batches))&&!memcmp(groups,rig.groups,scene.batch_count));
    unsigned group_triangles[5]={0};uint32_t cursor=0;
    for(uint32_t i=0;i<scene.batch_count;i++){
        const NfsBatch *b=&scene.batches[i];assert(b->first==cursor&&b->first+b->count<=indexed.index_count);cursor+=b->count;
        group_triangles[groups[i]]+=b->count/3;
        for(uint32_t j=b->first;j<b->first+b->count;j++)assert(!memcmp(&scene.vertices[j],&indexed.vertices[indexed.indices[j]],48));
    }
    assert(cursor==indexed.index_count);for(unsigned i=0;i<5;i++)assert(group_triangles[i]);
    NfsVertex *old_gpu=malloc(scene.vertex_count*48),*indexed_gpu=malloc(indexed.vertex_count*48);assert(old_gpu&&indexed_gpu);
    memcpy(old_gpu,scene.vertices,scene.vertex_count*48);memcpy(indexed_gpu,indexed.vertices,indexed.vertex_count*48);
    for(uint32_t i=0;i<scene.vertex_count;i++)old_gpu[i].uv[1]=1-old_gpu[i].uv[1];
    for(uint32_t i=0;i<indexed.vertex_count;i++)indexed_gpu[i].uv[1]=1-indexed_gpu[i].uv[1];
    for(uint32_t i=0;i<scene.vertex_count;i++)assert(!memcmp(&old_gpu[i],&indexed_gpu[indexed.indices[i]],48));
    free(old_gpu);free(indexed_gpu);
    float old_min[3]={INFINITY,INFINITY,INFINITY},old_max[3]={-INFINITY,-INFINITY,-INFINITY};
    float new_min[3]={INFINITY,INFINITY,INFINITY},new_max[3]={-INFINITY,-INFINITY,-INFINITY};
    for(uint32_t i=0;i<scene.vertex_count;i++)for(unsigned j=0;j<3;j++){old_min[j]=fminf(old_min[j],scene.vertices[i].position[j]);old_max[j]=fmaxf(old_max[j],scene.vertices[i].position[j]);}
    for(uint32_t i=0;i<indexed.vertex_count;i++)for(unsigned j=0;j<3;j++){new_min[j]=fminf(new_min[j],indexed.vertices[i].position[j]);new_max[j]=fmaxf(new_max[j],indexed.vertices[i].position[j]);}
    for(unsigned j=0;j<3;j++)assert(old_min[j]==new_min[j]&&old_max[j]==new_max[j]);
    uint32_t before=scene.vertex_count*48,after=indexed.vertex_count*48+indexed.index_count*2;
    printf("{\"source\":\"%s\",\"original_vertices\":%u,\"unique_vertices\":%u,\"index_count\":%u,\"original_gpu_bytes\":%u,\"indexed_gpu_bytes\":%u,\"saved_bytes\":%u,\"batches\":%u,\"wheel_groups_preserved\":true}\n",folder,scene.vertex_count,indexed.vertex_count,indexed.index_count,before,after,before-after,scene.batch_count);
    vehicle_index_free(&again);vehicle_index_free(&indexed);free(batches);free(groups);wheel_rig_free(&rig);nfs_scene_free(&scene);
}
int main(int argc,char **argv)
{
    NfsVertex source[9];for(unsigned i=0;i<9;i++)source[i]=base_vertex();
    source[1].uv[0]=1;source[2].color[1]=.5f;source[3]=source[0];source[4]=source[2];source[5]=source[1];
    source[6].position[0]=-0.0f;source[7]=source[6];source[8]=source[0];
    VehicleIndexedVertices out={0};assert(vehicle_index_encode(source,9,&out)==VEHICLE_INDEX_OK);
    assert(out.vertex_count==4);const uint16_t expected[]={0,1,2,0,2,1,3,3,0};assert(!memcmp(out.indices,expected,sizeof(expected)));reconstruction(source,9,&out);
    VehicleIndexedVertices before=out;
    assert(vehicle_index_encode(NULL,3,&out)==VEHICLE_INDEX_INVALID);
    assert(vehicle_index_encode(source,0,&out)==VEHICLE_INDEX_INVALID&&vehicle_index_encode(source,1,&out)==VEHICLE_INDEX_INVALID);
    assert(vehicle_index_encode(source,SIZE_MAX,&out)==VEHICLE_INDEX_INVALID&&vehicle_index_encode(source,200001,&out)==VEHICLE_INDEX_INVALID);
    assert(vehicle_index_encode(source,3,NULL)==VEHICLE_INDEX_INVALID);assert(!memcmp(&out,&before,sizeof(out)));
    /* Every field participates, including signed zero and low mantissa bits. */
    for(unsigned field=0;field<12;field++){
        NfsVertex triangle[3]={base_vertex(),base_vertex(),base_vertex()};
        unsigned char *different=(unsigned char *)&triangle[1];different[field*4]^=1;
        VehicleIndexedVertices result={0};assert(vehicle_index_encode(triangle,3,&result)==VEHICLE_INDEX_OK&&result.vertex_count==2);reconstruction(triangle,3,&result);vehicle_index_free(&result);
        uint32_t invalid=0x7f800000u;memcpy(different+field*4,&invalid,4);
        assert(vehicle_index_encode(triangle,3,&out)==VEHICLE_INDEX_INVALID&&!memcmp(&out,&before,sizeof(out)));
    }
    /* Exercise clustered open-address probing and its explicit fallback budget. */
    for(unsigned count=63;count<=66;count+=3){
        NfsVertex cluster[66];unsigned found=0;uint32_t mask=count==63?127:255;
        for(uint32_t bits=0x3f000000;found<count;bits++){
            NfsVertex v=base_vertex();set_x_bits(&v,bits);
            if(!(independent_hash(&v)&mask))cluster[found++]=v;
        }
        if(count==63){VehicleIndexedVertices result={0};assert(vehicle_index_encode(cluster,count,&result)==VEHICLE_INDEX_OK);reconstruction(cluster,count,&result);vehicle_index_free(&result);}
        else assert(vehicle_index_encode(cluster,count,&out)==VEHICLE_INDEX_BUDGET&&!memcmp(&out,&before,sizeof(out)));
    }
    size_t count=65538;NfsVertex *large=malloc(count*sizeof(*large));assert(large);
    for(size_t i=0;i<count;i++){large[i]=base_vertex();set_x_bits(&large[i],0x3f000000u+(uint32_t)i);}
    VehicleIndexedVertices at_cap={0};assert(vehicle_index_encode(large,65535,&at_cap)==VEHICLE_INDEX_OK&&at_cap.vertex_count==65535);
    assert(at_cap.indices[65534]==65534);reconstruction(large,65535,&at_cap);vehicle_index_free(&at_cap);
    assert(vehicle_index_encode(large,count,&out)==VEHICLE_INDEX_OVERFLOW&&!memcmp(&out,&before,sizeof(out)));
    free(large);reconstruction(source,9,&out);vehicle_index_free(&out);vehicle_index_free(&out);vehicle_index_free(NULL);assert(!out.vertices&&!out.indices&&!out.vertex_count&&!out.index_count);
    for(int i=1;i<argc;i++)real_scene(argv[i]);
    puts("Vehicle index: complete48-byte reconstruction, stable order, signed-zero/seams, collision budget, unique cap and transactional failures pass.");return 0;
}
