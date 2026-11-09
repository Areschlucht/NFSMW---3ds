#include "road_map.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
#define SIDE 512
static float cross(float ax,float ay,float bx,float by) { return ax*by-ay*bx; }
void road_map_free(RoadMap *map)
{ if (map) { free(map->pixels);memset(map,0,sizeof(*map)); } }
bool road_map_init(const RoadWorld *w,RoadMap *out)
{
    if (!out) return false;
    memset(out,0,sizeof(*out));
    if (!w || !w->triangles || !w->count || w->count>20000) return false;
    float lowx=INFINITY,highx=-INFINITY,lowz=INFINITY,highz=-INFINITY;
    for (uint32_t i=0;i<w->count;++i) for (unsigned p=0;p<3;++p) {
        float x=w->triangles[i].p[p][0],z=w->triangles[i].p[p][2];
        if (!isfinite(x) || !isfinite(z) || fabsf(x)>20000 || fabsf(z)>20000) return false;
        lowx=fminf(lowx,x);highx=fmaxf(highx,x);lowz=fminf(lowz,z);highz=fmaxf(highz,z);
    }
    float span=fmaxf(highx-lowx,highz-lowz);
    if (span<.01f) return false;
    RoadMap map={.center_x=(lowx+highx)/2,.center_z=(lowz+highz)/2,.step=span/(SIDE-4)};
    map.pixels=calloc(SIDE*SIDE,1);if (!map.pixels) return false;
    unsigned long budget=12000000;
    for (uint32_t i=0;i<w->count;++i) {
        float x[3],y[3];
        for (unsigned p=0;p<3;++p) {
            x[p]=(map.center_x-w->triangles[i].p[p][0])/map.step+255.5f;
            y[p]=(map.center_z-w->triangles[i].p[p][2])/map.step+255.5f;
        }
        float area=cross(x[1]-x[0],y[1]-y[0],x[2]-x[0],y[2]-y[0]);
        if (fabsf(area)<.00001f) continue;
        int x0=(int)fmaxf(0,floorf(fminf(x[0],fminf(x[1],x[2]))));
        int x1=(int)fminf(SIDE-1,ceilf(fmaxf(x[0],fmaxf(x[1],x[2]))));
        int y0=(int)fmaxf(0,floorf(fminf(y[0],fminf(y[1],y[2]))));
        int y1=(int)fminf(SIDE-1,ceilf(fmaxf(y[0],fmaxf(y[1],y[2]))));
        unsigned long work=(unsigned long)(x1-x0+1)*(unsigned long)(y1-y0+1);
        if (work>budget) { road_map_free(&map);return false; }budget-=work;
        for (int py=y0;py<=y1;++py) for (int px=x0;px<=x1;++px) {
            float a=cross(x[1]-px,y[1]-py,x[2]-px,y[2]-py)/area;
            float b=cross(x[2]-px,y[2]-py,x[0]-px,y[0]-py)/area;
            if (a>=-.00001f && b>=-.00001f && a+b<=1.00001f) map.pixels[py*SIDE+px]=1;
        }
    }
    *out=map;return true;
}
static void pixel(unsigned char *rgb,unsigned w,unsigned h,int x,int y,unsigned r,unsigned g,unsigned b)
{
    if (x<0 || y<0 || (unsigned)x>=w || (unsigned)y>=h) return;
    unsigned char *p=rgb+((unsigned)y*w+(unsigned)x)*3;p[0]=(unsigned char)r;p[1]=(unsigned char)g;p[2]=(unsigned char)b;
}
static void line(unsigned char *rgb,unsigned w,unsigned h,int ax,int ay,int bx,int by)
{
    int dx=abs(bx-ax),sx=ax<bx?1:-1,dy=-abs(by-ay),sy=ay<by?1:-1,error=dx+dy;
    for (;;) {
        pixel(rgb,w,h,ax,ay,255,205,55);
        if (ax==bx && ay==by) break;
        int twice=2*error;if (twice>=dy) { error+=dy;ax+=sx; }if (twice<=dx) { error+=dx;ay+=sy; }
    }
}
bool road_map_render(const RoadMap *map,const RoadWorld *world,const DriveState *car,unsigned char *rgb,unsigned w,unsigned h)
{
    if (!map || !map->pixels || !world || !car || !rgb || w<20 || w>320 || h<20 || h>240 ||
        !isfinite(map->step) || map->step<=0 || !isfinite(map->center_x) || !isfinite(map->center_z) || !isfinite(car->x) || !isfinite(car->z) ||
        fabsf(car->x)>20000 || fabsf(car->z)>20000 || !isfinite(car->heading) ||
        !isfinite(world->spawn[0]) || !isfinite(world->spawn[2])) return false;
    float col=(map->center_x-car->x)/map->step+255.5f,row=(map->center_z-car->z)/map->step+255.5f;
    if (fabsf(col)>10000000 || fabsf(row)>10000000) return false;
    int cx=(int)lroundf(col),cy=(int)lroundf(row);
    for (unsigned y=0;y<h;++y) for (unsigned x=0;x<w;++x) {
        int px=cx+(int)x-(int)w/2,py=cy+(int)y-(int)h/2;
        bool road=px>=0 && py>=0 && px<SIDE && py<SIDE && map->pixels[py*SIDE+px];
        bool border=!x || !y || x==w-1 || y==h-1;
        unsigned shade=border?70:road?205:18;pixel(rgb,w,h,(int)x,(int)y,shade,shade,shade);
    }
    float startx=(car->x-world->spawn[0])/map->step+w/2,starty=(car->z-world->spawn[2])/map->step+h/2;
    if (startx>1 && starty>1 && startx<w-2 && starty<h-2) {
        int x=(int)lroundf(startx),y=(int)lroundf(starty);
        for (int a=-2;a<=2;++a) for (int b=-2;b<=2;++b) pixel(rgb,w,h,x+a,y+b,30,205,240);
    }
    return road_map_player_overlay(car,rgb,w,h);
}
bool road_map_player_overlay(const DriveState *car,unsigned char *rgb,unsigned w,unsigned h)
{
    if(!car||!rgb||w<20||w>320||h<20||h>240||!isfinite(car->heading))return false;
    float s=sinf(car->heading),c=cosf(car->heading);int x=(int)w/2,y=(int)h/2;
    int tx=x-(int)lroundf(s*8),ty=y-(int)lroundf(c*8);
    int ax=x+(int)lroundf(s*4+c*4),ay=y+(int)lroundf(c*4-s*4);
    int bx=x+(int)lroundf(s*4-c*4),by=y+(int)lroundf(c*4+s*4);
    line(rgb,w,h,tx,ty,ax,ay);line(rgb,w,h,ax,ay,bx,by);line(rgb,w,h,bx,by,tx,ty);
    return true;
}
bool road_edge_ahead(const RoadWorld *w,const DriveState *car,float height)
{
    if (!w || !car || !isfinite(car->x) || !isfinite(car->z) || !isfinite(car->heading) ||
        !isfinite(car->speed) || !isfinite(height) || fabsf(car->speed)<.5f) return false;
    float distance=fminf(20,fmaxf(6,fabsf(car->speed)*.8f));
    float direction=car->speed<0?-1:1,s=sinf(car->heading)*direction,c=cosf(car->heading)*direction;
    for (float d=1;d<=distance;d+=1) if (!road_height(w,car->x+s*d,car->z+c*d,height,&height)) return true;
    return false;
}
bool road_map_blit565(const unsigned char *rgb,unsigned width,unsigned height,unsigned char *framebuffer,size_t bytes,unsigned left,unsigned top)
{
    if (!rgb || !framebuffer || bytes<320*240*2 || !width || !height || left>=320 || top>=240 || width>320-left || height>240-top) return false;
    for (unsigned y=0;y<height;++y) for (unsigned x=0;x<width;++x) {
        const unsigned char *source=rgb+(y*width+x)*3;
        uint16_t pixel=(uint16_t)(((source[0]>>3)<<11)|((source[1]>>2)<<5)|(source[2]>>3));
        unsigned offset=((left+x)*240+(239-top-y))*2;
        framebuffer[offset]=(unsigned char)pixel;framebuffer[offset+1]=(unsigned char)(pixel>>8);
    }
    return true;
}
