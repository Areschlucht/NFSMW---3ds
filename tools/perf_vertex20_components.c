#include "perf_vertex20_components.h"
#include <math.h>
#include <string.h>
_Static_assert(sizeof(PerfVertexUV32)==32 && offsetof(PerfVertexUV32,color)==16,"UV-only GPU layout");
_Static_assert(sizeof(PerfVertexColor24)==24 && offsetof(PerfVertexColor24,color)==20,"Colour-only GPU layout");
void perf_vertex20_uv32_unpack(WorldVertex *out,const PerfVertexUV32 *source,size_t count)
{
    for (size_t i=0;i<count;++i) {
        memcpy(out[i].position,source[i].position,sizeof(out[i].position));
        out[i].uv[0]=source[i].uv[0]/4096.0f;out[i].uv[1]=1-source[i].uv[1]/4096.0f;
        memcpy(out[i].color,source[i].color,sizeof(out[i].color));
    }
}
bool perf_vertex20_uv32_pack(PerfVertexUV32 *out,const WorldVertex *source,size_t count)
{
    if (!out || !source || !count || count>200000) return false;
    for (size_t i=0;i<count;++i) {
        PerfVertexUV32 packed;
        for (unsigned a=0;a<3;++a) if (!isfinite(source[i].position[a])) return false;
        for (unsigned a=0;a<4;++a) if (!isfinite(source[i].color[a])) return false;
        if (!isfinite(source[i].uv[0]) || !isfinite(source[i].uv[1])) return false;
        float u=roundf(source[i].uv[0]*4096),v=roundf((1-source[i].uv[1])*4096);
        if (!isfinite(u) || !isfinite(v) || u<-32768 || u>32767 || v<-32768 || v>32767) return false;
        packed.uv[0]=(int16_t)u;packed.uv[1]=(int16_t)v;
        memcpy(packed.position,source[i].position,sizeof(packed.position));memcpy(packed.color,source[i].color,sizeof(packed.color));
        WorldVertex restored;perf_vertex20_uv32_unpack(&restored,&packed,1);
        if (memcmp(&restored,&source[i],sizeof(restored))) return false;
        out[i]=packed;
    }
    return true;
}
void perf_vertex20_color24_unpack(WorldVertex *out,const PerfVertexColor24 *source,size_t count)
{
    for (size_t i=0;i<count;++i) {
        memcpy(out[i].position,source[i].position,sizeof(out[i].position));memcpy(out[i].uv,source[i].uv,sizeof(out[i].uv));
        for (unsigned a=0;a<4;++a) out[i].color[a]=source[i].color[a]/255.0f;
    }
}
bool perf_vertex20_color24_pack(PerfVertexColor24 *out,const WorldVertex *source,size_t count)
{
    if (!out || !source || !count || count>200000) return false;
    for (size_t i=0;i<count;++i) {
        PerfVertexColor24 packed;
        for (unsigned a=0;a<3;++a) if (!isfinite(source[i].position[a])) return false;
        for (unsigned a=0;a<2;++a) if (!isfinite(source[i].uv[a])) return false;
        for (unsigned a=0;a<4;++a) {
            float color=source[i].color[a];if (!isfinite(color) || color<0 || color>1) return false;
            packed.color[a]=(uint8_t)roundf(color*255);
        }
        memcpy(packed.position,source[i].position,sizeof(packed.position));memcpy(packed.uv,source[i].uv,sizeof(packed.uv));
        WorldVertex restored;perf_vertex20_color24_unpack(&restored,&packed,1);
        if (memcmp(&restored,&source[i],sizeof(restored))) return false;
        out[i]=packed;
    }
    return true;
}
