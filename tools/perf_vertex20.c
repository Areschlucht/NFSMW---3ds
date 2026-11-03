#include "perf_vertex20.h"
#include <math.h>
#include <string.h>
_Static_assert(sizeof(PerfVertex20)==20,"Experimental GPU stride");
_Static_assert(offsetof(PerfVertex20,uv)==12 && offsetof(PerfVertex20,color)==16,"Experimental GPU attribute offsets");
void perf_vertex20_unpack(WorldVertex *out,const PerfVertex20 *source,size_t count)
{
    for (size_t i=0;i<count;++i) {
        memcpy(out[i].position,source[i].position,sizeof(out[i].position));
        out[i].uv[0]=source[i].uv[0]/4096.0f;
        out[i].uv[1]=1-source[i].uv[1]/4096.0f;
        for (unsigned a=0;a<4;++a) out[i].color[a]=source[i].color[a]/255.0f;
    }
}
bool perf_vertex20_pack(PerfVertex20 *out,const WorldVertex *source,size_t count)
{
    if (!out || !source || !count || count>200000) return false;
    for (size_t i=0;i<count;++i) {
        PerfVertex20 packed;
        for (unsigned a=0;a<3;++a) if (!isfinite(source[i].position[a])) return false;
        memcpy(packed.position,source[i].position,sizeof(packed.position));
        if (!isfinite(source[i].uv[0]) || !isfinite(source[i].uv[1])) return false;
        float u=roundf(source[i].uv[0]*4096),v=roundf((1-source[i].uv[1])*4096);
        if (!isfinite(u) || !isfinite(v) || u<-32768 || u>32767 || v<-32768 || v>32767) return false;
        packed.uv[0]=(int16_t)u;packed.uv[1]=(int16_t)v;
        for (unsigned a=0;a<4;++a) {
            float c=source[i].color[a];
            if (!isfinite(c) || c<0 || c>1) return false;
            packed.color[a]=(uint8_t)roundf(c*255);
        }
        WorldVertex restored;perf_vertex20_unpack(&restored,&packed,1);
        if (memcmp(&restored,&source[i],sizeof(restored))) return false;
        out[i]=packed;
    }
    return true;
}
