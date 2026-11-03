#include "road_map.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void square(RoadTriangle t[2])
{
    const float points[2][3][3]={{{-10,0,-10},{10,0,-10},{10,0,10}},{{-10,0,-10},{10,0,10},{-10,0,10}}};
    memset(t,0,2*sizeof(*t));
    for (unsigned i=0;i<2;++i) {
        memcpy(t[i].p,points[i],sizeof(points[i]));t[i].minx=t[i].minz=-10;t[i].maxx=t[i].maxz=10;t[i].denominator=400;
    }
}
int main(int argc,char **argv)
{
    RoadTriangle triangles[2];square(triangles);RoadWorld world={.count=2,.triangles=triangles};RoadMap map;
    assert(road_map_init(&world,&map));assert(map.pixels[256*512+256]);
    unsigned char image[152*128*3];DriveState car={0};assert(road_map_render(&map,&world,&car,image,152,128));
    unsigned char *tip=image+(56*152+76)*3;assert(tip[0]==255 && tip[1]==205 && tip[2]==55);
    car.heading=-1.5707963f;assert(road_map_render(&map,&world,&car,image,152,128));
    tip=image+(64*152+84)*3;assert(tip[0]==255 && tip[1]==205);
    unsigned char *frame=malloc(320*240*2+16);assert(frame);memset(frame,0xa5,320*240*2+16);
    assert(road_map_blit565(image,152,128,frame,320*240*2,164,88));
    /* Heading-right tip: RGB(255,205,55) -> RGB565 0xfe66. */
    unsigned address=((164+84)*240+(239-(88+64)))*2;
    assert(frame[address]==0x66 && frame[address+1]==0xfe);
    assert(frame[0]==0xa5);for (unsigned i=0;i<16;++i) assert(frame[320*240*2+i]==0xa5);
    assert(!road_map_blit565(image,152,128,frame,320*240*2-1,164,88));
    assert(!road_map_blit565(image,152,128,frame,320*240*2,319,88));free(frame);
    car=(DriveState){.speed=5};assert(!road_edge_ahead(&world,&car,0));
    car.z=8;assert(road_edge_ahead(&world,&car,0));
    car.speed=-5;assert(!road_edge_ahead(&world,&car,0));car.z=-8;assert(road_edge_ahead(&world,&car,0));
    car.speed=0;assert(!road_edge_ahead(&world,&car,0));
    car.x=NAN;assert(!road_map_render(&map,&world,&car,image,152,128));
    road_map_free(&map);road_map_free(&map);assert(!road_map_render(&map,&world,&car,image,152,128));
    if (argc==3) {
        FILE *f=fopen(argv[1],"rb");assert(f);assert(!fseek(f,0,SEEK_END));long n=ftell(f);rewind(f);
        unsigned char *raw=malloc((size_t)n);assert(raw);assert(fread(raw,1,(size_t)n,f)==(size_t)n);fclose(f);
        RoadWorld real;assert(road_decode(raw,(size_t)n,&real));free(raw);assert(road_map_init(&real,&map));
        car=(DriveState){.x=real.spawn[0],.z=real.spawn[2],.heading=real.heading};
        assert(road_map_render(&map,&real,&car,image,152,128));
        unsigned pixels=0;for (unsigned i=0;i<512*512;++i) pixels+=map.pixels[i]!=0;
        assert(pixels>1000 && pixels<512*512/2);
        f=fopen(argv[2],"wb");assert(f);fprintf(f,"P6\n152 128\n255\n");assert(fwrite(image,1,sizeof(image),f)==sizeof(image));fclose(f);
        printf("Real road map: %u covered pixels, %.2f meters/pixel\n",pixels,map.step);
        road_map_free(&map);road_free(&real);
    }
    puts("Map checks passed: original coverage, heading arrows, ahead/reverse edge prediction, stationary behavior and invalid input.");return 0;
}
