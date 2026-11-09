#include "mw_free_roam.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(int argc,char **argv){
 assert(argc==2);FILE *f=fopen(argv[1],"rb");assert(f);assert(!fseek(f,0,SEEK_END));long n=ftell(f);rewind(f);assert(n>96);void *data=malloc((size_t)n);assert(data&&fread(data,1,(size_t)n,f)==(size_t)n);fclose(f);
 MwFreeRoam view;assert(mw_free_roam_open(&view,data,(size_t)n)&&view.count==161);unsigned kinds[5]={0};
 for(uint32_t i=0;i<view.count;i++){MwDestination d,near;assert(mw_free_roam_get(&view,i,&d));kinds[d.kind]++;assert(mw_free_roam_near(&view,d.position,&near));float delta[3];double squared=0;for(unsigned a=0;a<3;a++){delta[a]=d.position[a]-near.position[a];squared+=delta[a]*delta[a];}assert(squared<=near.radius*near.radius);}
 assert(kinds[1]==4&&kinds[2]==8&&kinds[3]==3&&kinds[4]==146);
 MwDestination unchanged={.key=123},out=unchanged;float nowhere[]={100000,100000,100000};assert(!mw_free_roam_near(&view,nowhere,&out));assert(!memcmp(&out,&unchanged,sizeof(out)));
 float invalid[]={NAN,0,0};assert(!mw_free_roam_near(&view,invalid,&out));
 unsigned char *raw=data;raw[n-1]^=1;MwFreeRoam before=view;assert(!mw_free_roam_open(&view,data,(size_t)n));assert(!memcmp(&view,&before,sizeof(view)));
 free(data);puts("161 original hotspot centers, source radii, type counts, no-match/NaN and malformed-pack guards pass.");
}
