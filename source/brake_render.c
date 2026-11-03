#include "brake_render.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>

typedef struct { float x,y,z; } Point;

static void pixel(uint8_t *fb, int x, int y, unsigned shade)
{
    size_t offset=((size_t)x*VIEW_HEIGHT+VIEW_HEIGHT-1-y)*3;
    fb[offset]=(uint8_t)(shade*3/4);
    fb[offset+1]=(uint8_t)shade;
    fb[offset+2]=(uint8_t)(shade*4/5);
}

static void line(uint8_t *fb, int x0, int y0, int x1, int y1)
{
    int dx=abs(x1-x0),sx=x0<x1?1:-1,dy=-abs(y1-y0),sy=y0<y1?1:-1,error=dx+dy;
    for (;;) {
        if (x0>=0 && x0<VIEW_WIDTH && y0>=0 && y0<VIEW_HEIGHT) pixel(fb,x0,y0,230);
        if (x0==x1 && y0==y1) break;
        int twice=2*error;
        if (twice>=dy) { error+=dy; x0+=sx; }
        if (twice<=dx) { error+=dx; y0+=sy; }
    }
}

static float edge(Point a, Point b, float x, float y)
{
    return (x-a.x)*(b.y-a.y)-(y-a.y)*(b.x-a.x);
}

static void triangle(uint8_t *fb, float *depth, Point a, Point b, Point c, unsigned shade)
{
    float area=edge(a,b,c.x,c.y);
    if (fabsf(area)<0.001f) return;
    int x0=(int)floorf(fminf(a.x,fminf(b.x,c.x))),x1=(int)ceilf(fmaxf(a.x,fmaxf(b.x,c.x)));
    int y0=(int)floorf(fminf(a.y,fminf(b.y,c.y))),y1=(int)ceilf(fmaxf(a.y,fmaxf(b.y,c.y)));
    if (x0<0) x0=0;
    if (y0<0) y0=0;
    if (x1>=VIEW_WIDTH) x1=VIEW_WIDTH-1;
    if (y1>=VIEW_HEIGHT) y1=VIEW_HEIGHT-1;
    float inv_area=1.0f/area;
    for (int y=y0;y<=y1;++y)
        for (int x=x0;x<=x1;++x) {
            float w0=edge(b,c,x+0.5f,y+0.5f)*inv_area;
            float w1=edge(c,a,x+0.5f,y+0.5f)*inv_area;
            float w2=1-w0-w1;
            if (w0<0 || w1<0 || w2<0) continue;
            float reciprocal=w0/a.z+w1/b.z+w2/c.z;
            size_t index=(size_t)y*VIEW_WIDTH+x;
            if (reciprocal<=depth[index]) continue;
            depth[index]=reciprocal;
            pixel(fb,x,y,shade);
        }
}

void brake_render(const BrakeMesh *mesh, uint8_t fb[VIEW_BYTES], float depth[VIEW_PIXELS],
                  float yaw, float pitch, float zoom, bool wireframe)
{
    memset(fb,12,VIEW_BYTES);
    memset(depth,0,sizeof(float)*VIEW_PIXELS);
    if (!mesh || !mesh->vertex_count || mesh->vertex_count>BRAKE_VERTICES ||
        mesh->face_count>BRAKE_MAX_FACES || !isfinite(yaw) || !isfinite(pitch) || !isfinite(zoom)) return;
    if (zoom<0.5f) zoom=0.5f;
    if (zoom>1.7f) zoom=1.7f;
    float low[3]={INFINITY,INFINITY,INFINITY},high[3]={-INFINITY,-INFINITY,-INFINITY};
    for (size_t i=0;i<mesh->vertex_count;++i)
        for (size_t a=0;a<3;++a) {
            float value=mesh->positions[i][a];
            if (!isfinite(value)) return;
            if (value<low[a]) low[a]=value;
            if (value>high[a]) high[a]=value;
        }
    float extent=fmaxf(high[0]-low[0],fmaxf(high[1]-low[1],high[2]-low[2]));
    if (extent<=0 || !isfinite(extent)) return;
    float cy=cosf(yaw),sy=sinf(yaw),cp=cosf(pitch),sp=sinf(pitch);
    Point view[BRAKE_VERTICES],screen[BRAKE_VERTICES];
    for (size_t i=0;i<mesh->vertex_count;++i) {
        float p[3];
        for (size_t a=0;a<3;++a) p[a]=(mesh->positions[i][a]-(low[a]+high[a])*0.5f)*2/extent;
        float x=cy*p[0]+sy*p[2],z=-sy*p[0]+cy*p[2];
        view[i]=(Point){x,cp*p[1]-sp*z,sp*p[1]+cp*z};
        float d=4+view[i].z;
        screen[i]=(Point){200+x*280*zoom/d,120-view[i].y*280*zoom/d,d};
    }
    for (size_t i=0;i<mesh->face_count;++i) {
        const uint8_t *f=mesh->faces[i];
        if (f[0]>=mesh->vertex_count || f[1]>=mesh->vertex_count || f[2]>=mesh->vertex_count) continue;
        if (wireframe) {
            for (size_t e=0;e<3;++e) {
                Point a=screen[f[e]],b=screen[f[(e+1)%3]];
                line(fb,(int)a.x,(int)a.y,(int)b.x,(int)b.y);
            }
        } else {
            Point a=view[f[0]],b=view[f[1]],c=view[f[2]];
            float ux=b.x-a.x,uy=b.y-a.y,uz=b.z-a.z,vx=c.x-a.x,vy=c.y-a.y,vz=c.z-a.z;
            float nx=uy*vz-uz*vy,ny=uz*vx-ux*vz,nz=ux*vy-uy*vx;
            float length=sqrtf(nx*nx+ny*ny+nz*nz);
            if (length<=0) continue;
            float light=fabsf((nx*0.3f+ny*0.5f-nz*0.8124038f)/length);
            if (light>1) light=1;
            unsigned shade=(unsigned)(55+light*190);
            triangle(fb,depth,screen[f[0]],screen[f[1]],screen[f[2]],shade);
        }
    }
}
