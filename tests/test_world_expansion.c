#include "road_contact.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

static RoadWorld load(const char *path)
{
    FILE *f=fopen(path,"rb");assert(f);assert(!fseek(f,0,SEEK_END));long n=ftell(f);assert(n>64);rewind(f);
    unsigned char *raw=malloc((size_t)n);assert(raw);assert(fread(raw,1,(size_t)n,f)==(size_t)n);fclose(f);
    RoadWorld w;assert(road_decode(raw,(size_t)n,&w));free(raw);return w;
}
int main(int argc,char **argv)
{
    assert(argc==4);RoadWorld old=load(argv[1]),new=load(argv[2]);assert(new.count>old.count);
    /* All prior roads must remain, allowing only float32 coordinate rebasing. */
    for (unsigned i=0;i<old.count;++i) for (unsigned p=0;p<3;++p) for (unsigned a=0;a<3;++a)
        assert(fabsf((old.triangles[i].p[p][a]+old.origin[a])-(new.triangles[i].p[p][a]+new.origin[a]))<.001f);
    for (unsigned a=0;a<3;++a) assert(fabsf((old.spawn[a]+old.origin[a])-(new.spawn[a]+new.origin[a]))<.001f);
    assert(old.heading==new.heading);
    FILE *f=fopen(argv[3],"r");assert(f);unsigned probes=0;
    for (;;) {
        float p[3][3];int n=fscanf(f,"%f %f %f %f %f %f %f %f %f",&p[0][0],&p[0][1],&p[0][2],&p[1][0],&p[1][1],&p[1][2],&p[2][0],&p[2][1],&p[2][2]);
        if (n==EOF) break;
        assert(n==9);++probes;
        /* Walk from old surface through the common edge to the added surface. */
        for (unsigned leg=0;leg<2;++leg) for (unsigned step=0;step<=20;++step) {
            float t=step/20.0f,at[3];for (unsigned a=0;a<3;++a) at[a]=p[leg][a]+t*(p[leg+1][a]-p[leg][a]);
            float height;assert(road_height(&new,at[0],at[2],at[1],&height));assert(fabsf(height-at[1])<.005f);
        }
    }
    fclose(f);assert(probes>0);printf("Expansion: %u -> %u road triangles; prior road/spawn retained; %u traversable seam probes.\n",old.count,new.count,probes);
    road_free(&old);road_free(&new);return 0;
}
