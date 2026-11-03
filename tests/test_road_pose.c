#include "road_pose.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void plane(RoadTriangle t[2],float gx,float gz)
{
    const float xz[2][3][2]={{{-10,-10},{10,-10},{10,10}},{{-10,-10},{10,10},{-10,10}}};
    memset(t,0,2*sizeof(*t));
    for (unsigned i=0;i<2;++i) {
        for (unsigned p=0;p<3;++p) {
            float x=xz[i][p][0],z=xz[i][p][1];
            t[i].p[p][0]=x;t[i].p[p][1]=5+gx*x+gz*z;t[i].p[p][2]=z;
        }
        t[i].minx=t[i].minz=-10;t[i].maxx=t[i].maxz=10;
        t[i].denominator=400;
    }
}
static unsigned char *read(const char *path,size_t *size)
{
    FILE *f=fopen(path,"rb");assert(f);assert(!fseek(f,0,SEEK_END));long n=ftell(f);rewind(f);
    unsigned char *raw=malloc((size_t)n);assert(raw);assert(fread(raw,1,(size_t)n,f)==(size_t)n);fclose(f);*size=(size_t)n;return raw;
}
static unsigned word(const unsigned char *p)
{ return (unsigned)p[0]|(unsigned)p[1]<<8|(unsigned)p[2]<<16|(unsigned)p[3]<<24; }
int main(int argc,char **argv)
{
    RoadTriangle triangles[2];WheelRig rig={0};RoadWorld w={.count=2,.triangles=triangles,.car_half_extent=2};DriveState car={0};RoadPose pose;
    for (unsigned i=0;i<4;++i) { rig.wheels[i].pivot[0]=i%2?.6f:-.6f;rig.wheels[i].pivot[2]=i<2?.35f:-.35f; }
    const float slopes[4][2]={{0,0},{.1f,0},{0,-.15f},{.1f,.2f}};
    for (unsigned slope=0;slope<4;++slope) for (unsigned heading=0;heading<4;++heading) {
        float gx=slopes[slope][0],gz=slopes[slope][1];plane(triangles,gx,gz);car.heading=heading*1.5707963f;
        assert(road_pose_sample(&w,&rig,&car,5,&pose));assert(pose.contacts==4);assert(fabsf(pose.height-5)<.0001f);
        float norm=sqrtf(gx*gx+1+gz*gz);
        assert(fabsf(pose.normal[0]+gx/norm)<.0001f);assert(fabsf(pose.normal[1]-1/norm)<.0001f);assert(fabsf(pose.normal[2]+gz/norm)<.0001f);
    }
    /* At an unsupported edge, use the actual center triangle's normal. */
    plane(triangles,.1f,.1f);car=(DriveState){.x=9,.heading=.78539816f};
    assert(road_pose_sample(&w,&rig,&car,5.9f,&pose));assert(pose.contacts==3);
    assert(fabsf(pose.normal[0]+.1f/sqrtf(1.02f))<.0001f);
    plane(triangles,.1f,.1f);car=(DriveState){.x=9.8f};
    assert(road_pose_sample(&w,&rig,&car,5.98f,&pose));assert(pose.contacts==2);assert(isfinite(pose.roll));
    RoadPose unchanged=pose;car.x=20;
    assert(!road_pose_sample(&w,&rig,&car,5,&pose));assert(!memcmp(&pose,&unchanged,sizeof(pose)));
    car.x=NAN;assert(!road_pose_sample(&w,&rig,&car,5,&pose));
    plane(triangles,2,0);car=(DriveState){0};assert(road_pose_sample(&w,&rig,&car,5,&pose));assert(fabsf(pose.roll)<=.50001f);
    if (argc==4) {
        size_t n;unsigned char *raw=read(argv[1],&n);RoadWorld actual;assert(road_decode(raw,n,&actual));free(raw);
        raw=read(argv[3],&n);unsigned batches=word(raw+12),crc=word(raw+24);free(raw);
        raw=read(argv[2],&n);WheelRig actual_rig;assert(wheel_rig_decode(raw,n,batches,crc,&actual_rig));free(raw);
        car=(DriveState){.x=actual.spawn[0],.z=actual.spawn[2],.heading=actual.heading};
        assert(road_pose_sample(&actual,&actual_rig,&car,actual.spawn[1],&pose));
        printf("Real spawn: %u contacts, pitch %.3f deg, roll %.3f deg\n",pose.contacts,pose.pitch*57.29578f,pose.roll*57.29578f);
        assert(pose.contacts>=3 && fabsf(pose.pitch)>.001f);
        float y=actual.spawn[1];
        for (unsigned i=0;i<600;++i) {
            assert(road_height(&actual,car.x,car.z,y,&y));
            (void)road_drive_step(&actual,&car,&y,(DriveInput){.throttle=1},1.0f/60);
            assert(road_pose_sample(&actual,&actual_rig,&car,y,&pose));
        }
        wheel_rig_free(&actual_rig);road_free(&actual);
    }
    puts("Road pose checks passed: flat/hill/bank/combined slopes at four headings, missing contacts, limits, invalid input and real map.");return 0;
}
