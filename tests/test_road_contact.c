#include "road_contact.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void prepare(RoadTriangle *t)
{
    t->minx=fminf(t->p[0][0],fminf(t->p[1][0],t->p[2][0]));
    t->maxx=fmaxf(t->p[0][0],fmaxf(t->p[1][0],t->p[2][0]));
    t->minz=fminf(t->p[0][2],fminf(t->p[1][2],t->p[2][2]));
    t->maxz=fmaxf(t->p[0][2],fmaxf(t->p[1][2],t->p[2][2]));
    t->denominator=(t->p[1][0]-t->p[0][0])*(t->p[2][2]-t->p[0][2])-(t->p[1][2]-t->p[0][2])*(t->p[2][0]-t->p[0][0]);
}
int main(int argc,char **argv)
{
    RoadTriangle triangles[2]={ {.p={{-5,0,-5},{5,0,-5},{5,1,5}}}, {.p={{-5,0,-5},{5,1,5},{-5,1,5}}} };
    for (unsigned i=0;i<2;++i) prepare(&triangles[i]);
    RoadWorld w={.count=2,.triangles=triangles};float y=-999;
    assert(road_height(&w,0,0,.5f,&y) && fabsf(y-.5f)<1e-6f);
    assert(road_height(&w,-5,-5,0,&y) && y==0);
    y=123;assert(!road_height(&w,6,0,0,&y) && y==123);
    assert(!road_height(&w,0,0,20,&y));assert(!road_height(&w,NAN,0,0,&y));
    DriveState car;drive_reset(&car,0,0,0);y=.5f;
    bool hit_edge=false;
    for (unsigned i=0;i<600;++i) {
        if (!road_drive_step(&w,&car,&y,(DriveInput){.throttle=1},1.0f/60)) hit_edge=true;
        /* Shared-edge barycentric tolerance permits at most a sub-mm overrun. */
        assert(car.x>=-5.001f && car.x<=5.001f && car.z>=-5.001f && car.z<=5.001f);
        assert(fabsf(y-(car.z+5)*.1f)<.0001f);
    }
    assert(hit_edge && car.speed==0 && car.z>4.9f);
    float previous_z=car.z;
    for (unsigned i=0;i<30;++i) assert(road_drive_step(&w,&car,&y,(DriveInput){.throttle=-1},1.0f/60));
    assert(car.z<previous_z && car.speed<0);
    assert(!road_drive_step(&w,&car,&y,(DriveInput){0},NAN));
    if (argc==2 || argc==3) {
        FILE *f=fopen(argv[1],"rb");assert(f);assert(!fseek(f,0,SEEK_END));long n=ftell(f);rewind(f);
        unsigned char *raw=malloc((size_t)n);assert(raw);assert(fread(raw,1,(size_t)n,f)==(size_t)n);fclose(f);
        RoadWorld actual;assert(road_decode(raw,(size_t)n,&actual));
        assert(actual.count==(argc==3?strtoul(argv[2],NULL,10):2930));assert(road_height(&actual,actual.spawn[0],actual.spawn[2],actual.spawn[1],&y));
        road_free(&actual);raw[n-1]^=1;assert(!road_decode(raw,(size_t)n,&actual));
        assert(!road_decode(raw,63,&actual));free(raw);
    }
    puts("Road checks passed: slopes, shared edges, missing ground, edge stop, reverse, invalid input and optional real asset/CRC.");
    return 0;
}
