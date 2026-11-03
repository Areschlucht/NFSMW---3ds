#include "nfs_scene.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>

_Static_assert(sizeof(NfsVertex)==48,"Expected twelve packed float32 fields");
static uint32_t word(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static float real(const uint8_t *p)
{ uint32_t value=word(p);float result;memcpy(&result,&value,4);return result; }
static uint32_t crc32(const uint8_t *data,size_t length)
{
    uint32_t crc=0xffffffff;
    for (size_t i=0;i<length;++i) {
        crc^=data[i];
        for (unsigned bit=0;bit<8;++bit) crc=(crc>>1)^((0-(crc&1))&0xedb88320);
    }
    return ~crc;
}
/* Original GX car normals use three signed bytes with six fractional bits.
   Component truncation can move their squared length outside the tighter
   reconstructed-normal window. Keep their exact values; the shader normalizes.
   sqrt(3)/64 is a conservative component-quantization error bound. */
static bool quantized_normal(const float normal[3],float squared_length)
{
    if (squared_length<.946f || squared_length>1.055f) return false;
    for (unsigned a=0;a<3;++a) {
        float scaled=normal[a]*64;
        if (fabsf(normal[a])>1 || scaled!=truncf(scaled)) return false;
    }
    return true;
}
void nfs_scene_free(NfsScene *scene)
{
    if (!scene) return;
    free(scene->vertices);free(scene->batches);free(scene->textures);
    memset(scene,0,sizeof(*scene));
}
bool nfs_scene_decode(const uint8_t *data,size_t size,NfsScene *out)
{
    if (!out) return false;
    memset(out,0,sizeof(*out));
    if (!data || size<32 || memcmp(data,"NFM1",4) || word(data+28)) return false;
    uint32_t version=word(data+4);
    if (version!=1 && version!=2) return false;
    uint32_t stride=version==1?32:48;
    uint32_t nv=word(data+8),nb=word(data+12),nt=word(data+16),bytes=word(data+20);
    if (!nv || nv>200000 || nv%3 || !nb || nb>2048 || !nt || nt>NFS_MAX_TEXTURES ||
        bytes!=nt*16+nb*16+nv*stride || size-32!=bytes || crc32(data+32,bytes)!=word(data+24)) return false;
    NfsScene scene={.vertex_count=nv,.batch_count=nb,.texture_count=nt};
    scene.vertices=malloc(nv*sizeof(*scene.vertices));
    scene.batches=malloc(nb*sizeof(*scene.batches));
    scene.textures=malloc(nt*sizeof(*scene.textures));
    if (!scene.vertices || !scene.batches || !scene.textures) goto invalid;
    size_t p=32;
    for (uint32_t i=0;i<nt;++i,p+=16) {
        NfsTexture *t=&scene.textures[i];
        t->key=word(data+p);t->width=word(data+p+4);t->height=word(data+p+8);t->flags=word(data+p+12);
        if (t->width<8 || t->width>1024 || (t->width&(t->width-1)) ||
            t->height<8 || t->height>1024 || (t->height&(t->height-1)) || t->flags>7 || ((t->flags&4) && !(t->flags&1))) goto invalid;
    }
    uint32_t expected_first=0;
    for (uint32_t i=0;i<nb;++i,p+=16) {
        NfsBatch *b=&scene.batches[i];
        b->first=word(data+p);b->count=word(data+p+4);b->texture=word(data+p+8);b->reserved=word(data+p+12);
        if (b->first!=expected_first || b->first>nv || !b->count || b->count%3 || b->count>nv-b->first || b->texture>=nt || b->reserved) goto invalid;
        expected_first+=b->count;
    }
    if (expected_first!=nv) goto invalid;
    for (uint32_t i=0;i<nv;++i,p+=stride) {
        NfsVertex *v=&scene.vertices[i];
        for (unsigned a=0;a<3;++a) {
            v->position[a]=real(data+p+a*4);v->normal[a]=real(data+p+12+a*4);
            if (!isfinite(v->position[a]) || fabsf(v->position[a])>1.01f || !isfinite(v->normal[a])) goto invalid;
        }
        float length=0;
        for (unsigned a=0;a<3;++a) length+=v->normal[a]*v->normal[a];
        if ((length<0.98f || length>1.02f) && !quantized_normal(v->normal,length)) goto invalid;
        for (unsigned a=0;a<2;++a) {
            v->uv[a]=real(data+p+24+a*4);
            if (!isfinite(v->uv[a]) || fabsf(v->uv[a])>16) goto invalid;
        }
        for (unsigned a=0;a<4;++a) {
            v->color[a]=version==1?1.0f:real(data+p+32+a*4);
            if (!isfinite(v->color[a]) || v->color[a]<0 || v->color[a]>1) goto invalid;
        }
    }
    *out=scene;
    return true;
invalid:
    nfs_scene_free(&scene);
    return false;
}
