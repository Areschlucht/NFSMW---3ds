#include "road_contact.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
static unsigned queries;
static void compare(const RoadWorld *indexed,float x,float z,float reference)
{
    RoadWorld linear=*indexed;linear.grid=NULL;float a=123,b=123,na[3],nb[3];
    bool one=road_surface(indexed,x,z,reference,&a,na),two=road_surface(&linear,x,z,reference,&b,nb);
    assert(one==two);assert(a==b);
    if (one) for (unsigned i=0;i<3;++i) assert(na[i]==nb[i]);
    ++queries;
}
int main(int argc,char **argv)
{
    assert(argc==2);FILE *f=fopen(argv[1],"rb");assert(f);assert(!fseek(f,0,SEEK_END));long n=ftell(f);rewind(f);
    unsigned char *data=malloc((size_t)n);assert(data);assert(fread(data,1,(size_t)n,f)==(size_t)n);fclose(f);
    RoadWorld world;assert(road_decode(data,(size_t)n,&world));free(data);assert(world.grid);
    unsigned long long candidates=0;unsigned max_candidates=0;
    for (unsigned i=0;i<world.count;++i) {
        RoadTriangle *t=&world.triangles[i];float center[3]={0};
        for (unsigned a=0;a<3;++a) for (unsigned p=0;p<3;++p) center[a]+=t->p[p][a]/3;
        compare(&world,center[0],center[2],center[1]+.15f);
        for (unsigned p=0;p<3;++p) compare(&world,t->p[p][0],t->p[p][2],t->p[p][1]);
        unsigned x=(unsigned)((center[0]-world.grid->minx)/world.grid->cell),z=(unsigned)((center[2]-world.grid->minz)/world.grid->cell),cell=z*world.grid->columns+x;
        unsigned count=world.grid->offsets[cell+1]-world.grid->offsets[cell];candidates+=count;if(count>max_candidates)max_candidates=count;
    }
    unsigned random=12345;
    for (unsigned i=0;i<12000;++i) {
        random=random*1664525u+1013904223u;float x=world.grid->minx+(random&65535)/65535.0f*world.grid->columns*world.grid->cell;
        random=random*1664525u+1013904223u;float z=world.grid->minz+(random&65535)/65535.0f*world.grid->rows*world.grid->cell;
        compare(&world,x,z,world.spawn[1]);
    }
    for (unsigned z=0;z<world.grid->rows;++z) for (unsigned x=0;x<world.grid->columns;++x) {
        float px=world.grid->minx+x*world.grid->cell,pz=world.grid->minz+z*world.grid->cell;
        compare(&world,px-.0005f,pz,world.spawn[1]);compare(&world,px+.0005f,pz,world.spawn[1]);
    }
    compare(&world,NAN,0,0);compare(&world,1e30f,0,0);
    printf("Road grid: %ux%u cells, %u references, %.2f average/%u max centroid candidates instead of %u; %u indexed/linear height+normal queries match exactly.\n",world.grid->columns,world.grid->rows,world.grid->references,(double)candidates/world.count,max_candidates,world.count,queries);
    assert(candidates<((unsigned long long)world.count*world.count)/10);
    DriveState car;drive_reset(&car,world.spawn[0],world.spawn[2],world.heading);car.speed=14;float height=world.spawn[1];
    for (unsigned i=0;i<42;++i) assert(road_drive_step(&world,&car,&height,(DriveInput){.throttle=1,.steering=.8f,.handbrake=true},1.0f/120));
    assert(fabsf(atan2f(car.lateral_speed,car.speed))*57.29578f>12);
    for (unsigned i=0;i<36;++i) assert(road_drive_step(&world,&car,&height,(DriveInput){.throttle=1},1.0f/120));
    assert(fabsf(atan2f(car.lateral_speed,car.speed))*57.29578f>8);
    puts("Real original-road handbrake tap/release retains supported contact and >8 deg slip.");
    road_free(&world);road_free(&world);
    RoadWorld invalid={0};assert(!road_build_grid(&invalid));
    /* A pathological set of giant overlapping bounds must respect the memory
       cap and retain the linear fallback, without leaving partial allocations. */
    RoadWorld huge={.count=1000};huge.triangles=calloc(huge.count,sizeof(*huge.triangles));assert(huge.triangles);
    for (unsigned i=0;i<huge.count;++i) { huge.triangles[i].maxx=1000;huge.triangles[i].maxz=1000; }
    assert(!road_build_grid(&huge));assert(!huge.grid);road_free(&huge);
    RoadWorld decks={.count=4};decks.triangles=calloc(4,sizeof(*decks.triangles));assert(decks.triangles);
    for (unsigned i=0;i<4;++i) {
        RoadTriangle *t=&decks.triangles[i];float y=i/2;
        t->p[0][0]=-10;t->p[0][1]=y;t->p[0][2]=-10;
        t->p[1][0]=10;t->p[1][1]=y;t->p[1][2]=i%2?10:-10;
        t->p[2][0]=i%2?-10:10;t->p[2][1]=y;t->p[2][2]=10;
        t->minx=t->minz=-10;t->maxx=t->maxz=10;t->denominator=400;
    }
    assert(road_build_grid(&decks));compare(&decks,0,0,.5f);compare(&decks,0,0,1.1f);
    float y;assert(road_height(&decks,0,0,.5f,&y) && y==0);assert(road_height(&decks,0,0,1.1f,&y) && y==1);
    road_free(&decks);
    puts("Grid equivalence, bounds, holes, boundaries, invalid input, memory cap and cleanup passed.");return 0;
}
