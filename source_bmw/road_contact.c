#include "road_contact.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
static uint32_t word(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static float real(const uint8_t *p)
{ uint32_t u=word(p);float f;memcpy(&f,&u,4);return f; }
static uint32_t crc32(const uint8_t *data,size_t size)
{
    uint32_t crc=0xffffffff;
    for (size_t i=0;i<size;++i) {
        crc^=data[i];
        for (unsigned b=0;b<8;++b) crc=(crc>>1)^((0-(crc&1))&0xedb88320);
    }
    return ~crc;
}
void road_free(RoadWorld *w)
{
    if (!w) return;
    if (w->grid) { free(w->grid->offsets);free(w->grid->indices);free(w->grid); }
    free(w->triangles);memset(w,0,sizeof(*w));
}
static void grid_range(const RoadGrid *g,const RoadTriangle *t,unsigned *x0,unsigned *x1,unsigned *z0,unsigned *z1)
{
    *x0=(unsigned)fmaxf(0,floorf((t->minx-.001f-g->minx)/g->cell));
    *x1=(unsigned)fminf(g->columns-1,floorf((t->maxx+.001f-g->minx)/g->cell));
    *z0=(unsigned)fmaxf(0,floorf((t->minz-.001f-g->minz)/g->cell));
    *z1=(unsigned)fminf(g->rows-1,floorf((t->maxz+.001f-g->minz)/g->cell));
}
bool road_build_grid(RoadWorld *w)
{
    if (!w || !w->triangles || !w->count || w->count>20000) return false;
    if (w->grid) return true;
    float lowx=INFINITY,lowz=INFINITY,highx=-INFINITY,highz=-INFINITY;
    for (uint32_t i=0;i<w->count;++i) {
        const RoadTriangle *t=&w->triangles[i];
        if (!isfinite(t->minx) || !isfinite(t->maxx) || !isfinite(t->minz) || !isfinite(t->maxz) ||
            fabsf(t->minx)>20000 || fabsf(t->maxx)>20000 || fabsf(t->minz)>20000 || fabsf(t->maxz)>20000 || t->minx>t->maxx || t->minz>t->maxz) return false;
        lowx=fminf(lowx,t->minx);lowz=fminf(lowz,t->minz);highx=fmaxf(highx,t->maxx);highz=fmaxf(highz,t->maxz);
    }
    RoadGrid *g=calloc(1,sizeof(*g));if (!g) return false;
    g->minx=lowx-.002f;g->minz=lowz-.002f;
    g->cell=fmaxf(32,fmaxf(highx-lowx,highz-lowz)/126);
    g->columns=(uint32_t)floorf((highx+.002f-g->minx)/g->cell)+1;
    g->rows=(uint32_t)floorf((highz+.002f-g->minz)/g->cell)+1;
    if (!g->columns || !g->rows || g->columns>128 || g->rows>128) goto invalid;
    unsigned cells=g->columns*g->rows;
    g->offsets=calloc(cells+1,sizeof(*g->offsets));if (!g->offsets) goto invalid;
    for (uint32_t i=0;i<w->count;++i) {
        unsigned x0,x1,z0,z1;grid_range(g,&w->triangles[i],&x0,&x1,&z0,&z1);
        for (unsigned z=z0;z<=z1;++z) for (unsigned x=x0;x<=x1;++x) {
            if (++g->references>200000) goto invalid;
            ++g->offsets[z*g->columns+x+1];
        }
    }
    for (unsigned i=0;i<cells;++i) g->offsets[i+1]+=g->offsets[i];
    g->indices=malloc(g->references*sizeof(*g->indices));if (!g->indices) goto invalid;
    uint32_t *cursor=malloc(cells*sizeof(*cursor));if (!cursor) goto invalid;
    memcpy(cursor,g->offsets,cells*sizeof(*cursor));
    /* Preserve original triangle order in each cell, including deck/tie rules. */
    for (uint32_t i=0;i<w->count;++i) {
        unsigned x0,x1,z0,z1;grid_range(g,&w->triangles[i],&x0,&x1,&z0,&z1);
        for (unsigned z=z0;z<=z1;++z) for (unsigned x=x0;x<=x1;++x) g->indices[cursor[z*g->columns+x]++]=i;
    }
    free(cursor);w->grid=g;return true;
invalid:
    free(g->offsets);free(g->indices);free(g);return false;
}
bool road_surface(const RoadWorld *w,float x,float z,float reference,float *height,float normal[3])
{
    if (!w || !w->triangles || !height || !isfinite(x) || !isfinite(z) || !isfinite(reference)) return false;
    float best=2.0f,result=0,up[3]={0,1,0};bool found=false;
    uint32_t begin=0,end=w->count;const RoadGrid *grid=w->grid;
    if (grid) {
        float gx=(x-grid->minx)/grid->cell,gz=(z-grid->minz)/grid->cell;
        if (gx<0 || gz<0 || gx>=grid->columns || gz>=grid->rows) return false;
        unsigned cell=(unsigned)gz*grid->columns+(unsigned)gx;
        begin=grid->offsets[cell];end=grid->offsets[cell+1];
    }
    for (uint32_t candidate=begin;candidate<end;++candidate) {
        uint32_t i=grid?grid->indices[candidate]:candidate;
        const RoadTriangle *t=&w->triangles[i];
        if (x<t->minx-.001f || x>t->maxx+.001f || z<t->minz-.001f || z>t->maxz+.001f) continue;
        float ax=t->p[1][0]-t->p[0][0],az=t->p[1][2]-t->p[0][2];
        float bx=t->p[2][0]-t->p[0][0],bz=t->p[2][2]-t->p[0][2];
        float dx=x-t->p[0][0],dz=z-t->p[0][2];
        float a=(dx*bz-dz*bx)/t->denominator,b=(ax*dz-az*dx)/t->denominator;
        if (a<-.00001f || b<-.00001f || a+b>1.00001f) continue;
        float y=t->p[0][1]+a*(t->p[1][1]-t->p[0][1])+b*(t->p[2][1]-t->p[0][1]);
        float distance=fabsf(y-reference);
        if (distance<best) {
            result=y;best=distance;found=true;
            if (normal) {
                float ay=t->p[1][1]-t->p[0][1],by=t->p[2][1]-t->p[0][1];
                float gx=(ay*bz-by*az)/t->denominator,gz=(ax*by-bx*ay)/t->denominator;
                float inv=1/sqrtf(gx*gx+1+gz*gz);
                up[0]=-gx*inv;up[1]=inv;up[2]=-gz*inv;
            }
        }
    }
    if (found) { *height=result;if (normal) memcpy(normal,up,sizeof(up)); }
    return found;
}
bool road_height(const RoadWorld *w,float x,float z,float reference,float *height)
{ return road_surface(w,x,z,reference,height,NULL); }
bool road_decode(const uint8_t *data,size_t size,RoadWorld *out)
{
    if (!out) return false;
    memset(out,0,sizeof(*out));
    if (!data || size<64 || memcmp(data,"NRD1",4) || word(data+4)!=1 || word(data+52) || word(data+56) || word(data+60)) return false;
    uint32_t count=word(data+8);
    if (!count || count>20000 || size-64!=count*36 || crc32(data+64,size-64)!=word(data+12)) return false;
    for (unsigned i=0;i<9;++i) if (!isfinite(real(data+16+i*4)) || fabsf(real(data+16+i*4))>20000) return false;
    RoadWorld w={.count=count,.scale=real(data+16),.car_half_extent=real(data+20),.heading=real(data+48)};
    if (w.scale<.00001f || w.scale>1 || w.car_half_extent<1 || w.car_half_extent>4) return false;
    for (unsigned i=0;i<3;++i) { w.origin[i]=real(data+24+i*4);w.spawn[i]=real(data+36+i*4); }
    w.triangles=calloc(count,sizeof(*w.triangles));
    if (!w.triangles) return false;
    for (uint32_t i=0;i<count;++i) {
        RoadTriangle *t=&w.triangles[i];
        for (unsigned p=0;p<3;++p) for (unsigned a=0;a<3;++a) {
            float value=real(data+64+i*36+p*12+a*4);
            if (!isfinite(value) || fabsf(value)>20000) goto invalid;
            t->p[p][a]=value;
        }
        t->minx=fminf(t->p[0][0],fminf(t->p[1][0],t->p[2][0]));
        t->maxx=fmaxf(t->p[0][0],fmaxf(t->p[1][0],t->p[2][0]));
        t->minz=fminf(t->p[0][2],fminf(t->p[1][2],t->p[2][2]));
        t->maxz=fmaxf(t->p[0][2],fmaxf(t->p[1][2],t->p[2][2]));
        t->denominator=(t->p[1][0]-t->p[0][0])*(t->p[2][2]-t->p[0][2])-(t->p[1][2]-t->p[0][2])*(t->p[2][0]-t->p[0][0]);
        if (fabsf(t->denominator)<1e-6f) goto invalid;
    }
    /* Allocation/budget failure falls back to the exact original linear query. */
    (void)road_build_grid(&w);
    float height;
    if (!road_height(&w,w.spawn[0],w.spawn[2],w.spawn[1],&height)) goto invalid;
    *out=w;return true;
invalid:
    road_free(&w);return false;
}
bool road_drive_step(const RoadWorld *w,DriveState *car,float *height,DriveInput input,float seconds)
{
    if (!w || !car || !height || !isfinite(*height) || !isfinite(seconds) || seconds<=0 || seconds>.1f) return false;
    unsigned steps=(unsigned)ceilf(seconds*120);bool supported=true;
    for (unsigned i=0;i<steps;++i) {
        DriveState candidate=*car;
        if (!drive_step(&candidate,input,seconds/steps)) return false;
        float y;
        if (road_height(w,candidate.x,candidate.z,*height,&y)) { *car=candidate;*height=y; }
        else { car->speed=0;car->lateral_speed=0;car->yaw_rate=0;car->drift=0;car->steering=candidate.steering;supported=false;break; }
    }
    return supported;
}
