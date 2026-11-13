#include "mw_traffic.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void put(unsigned char *p,uint32_t v){for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(v>>(i*8));}
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
static void repair(unsigned char *p,size_t n){put(p+12,crc(p+16,n-16));}
static int deny(void *ctx,uint16_t segment,uint16_t flags,unsigned direction){(void)ctx;(void)segment;(void)flags;(void)direction;return 0;}
static int broken(void *ctx,uint16_t segment,uint16_t flags,unsigned direction){(void)ctx;(void)segment;(void)flags;(void)direction;return -1;}
static void reject(const void *p,size_t n){MwTrafficWorld view={.bytes=123};MwTrafficWorld before=view;assert(!mw_traffic_open(&view,p,n));assert(!memcmp(&view,&before,sizeof(view)));}
static uint32_t le(const unsigned char *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static float real(const unsigned char *p){uint32_t v=le(p);float f;memcpy(&f,&v,4);return f;}
int main(int argc,char **argv){
 assert(argc==2||argc==3);FILE *f=fopen(argv[1],"rb");assert(f&&!fseek(f,0,SEEK_END));long end=ftell(f);assert(end>192);rewind(f);size_t bytes=(size_t)end;unsigned char *data=malloc(bytes),*bad=malloc(bytes);assert(data&&bad&&fread(data,1,bytes,f)==bytes);assert(!fclose(f));
 MwTrafficWorld w;assert(mw_traffic_open(&w,data,bytes));assert(w.nodes==4385&&w.segments==6538&&w.profiles==710);
 unsigned reciprocal=0;for(uint32_t i=0;i<w.nodes;i++){MwTrafficNode n;assert(mw_traffic_node(&w,i,&n));assert(n.id==i&&n.count<=7);for(unsigned j=0;j<n.count;j++){MwTrafficSegment s;assert(mw_traffic_segment(&w,n.segments[j],&s));assert(s.nodes[0]==i||s.nodes[1]==i);reciprocal++;}}
 assert(reciprocal==w.segments*2);
 /* Exact original sampler checkpoints from source segment0. */
 const float expect[3]={-2464.642578125f,42.314842224121094f,2978.884033203125f};float p[3],d[3];assert(mw_traffic_sample(&w,0,.5f,p,d));for(unsigned i=0;i<3;i++)assert(fabsf(p[i]-expect[i])<.0001f);
 if(argc==3){
  FILE *v=fopen(argv[2],"rb");assert(v);unsigned char h[12];assert(fread(h,1,12,v)==12&&!memcmp(h,"MWTC",4)&&le(h+4)==1&&le(h+8)==640);float largest=0;
  for(unsigned i=0;i<le(h+8);i++){unsigned char row[20];assert(fread(row,1,20,v)==20);uint32_t id=le(row);assert(id<65536&&mw_traffic_sample(&w,(uint16_t)id,real(row+4),p,d));for(unsigned k=0;k<3;k++){float error=fabsf(p[k]-real(row+8+k*4));assert(error<=.001f);if(error>largest)largest=error;}}
  assert(fgetc(v)==EOF&&!fclose(v));printf("Native curve sampler:640 original points, maxabsolute error%.9g.\n",(double)largest);
 }
 float poison[3]={123,456,789};memcpy(p,poison,sizeof(p));assert(!mw_traffic_sample(&w,0,NAN,p,d));assert(!memcmp(p,poison,sizeof(p)));
 const float spawn[3]={-2441.7584f,164.77468f,385.9970f};MwTrafficWork query={0};uint16_t nearest=UINT16_MAX;float u=-1;
 assert(mw_traffic_nearest(&w,spawn,50,&nearest,&u,NULL,NULL,&query));assert(nearest<w.segments&&u>=0&&u<=1&&query.nearest_checks<=MW_TRAFFIC_MAX_NEAREST);
 uint16_t retained=nearest;float old_u=u;assert(!mw_traffic_nearest(&w,spawn,50,&nearest,&u,deny,NULL,NULL));assert(nearest==retained&&u==old_u);
 MwTrafficCar actors[MW_TRAFFIC_MAX_ACTORS];for(unsigned i=0;i<MW_TRAFFIC_MAX_ACTORS;i++)assert(mw_traffic_start(&w,&actors[i],nearest,i%2,fmodf(u+i*.07f,1),6+i,NULL,NULL,NULL));
 unsigned steps=0,checks_max=0,samples_max=0,transitions=0;float distance=0;
 for(unsigned frame=0;frame<3600;frame++)for(unsigned i=0;i<MW_TRAFFIC_MAX_ACTORS;i++){
  MwTrafficWork work={0};float prior[3];memcpy(prior,actors[i].position,sizeof(prior));int result=mw_traffic_step(&w,&actors[i],1.f/60,NULL,NULL,&work);assert(result>=0);
  assert(work.neighbor_checks<=MW_TRAFFIC_MAX_TRANSITIONS*7&&work.transitions<=MW_TRAFFIC_MAX_TRANSITIONS&&work.samples<=MW_TRAFFIC_MAX_TRANSITIONS*8+1);
  if(work.neighbor_checks>checks_max)checks_max=work.neighbor_checks;
  if(work.samples>samples_max)samples_max=work.samples;
  transitions+=work.transitions;
  float sum=0;for(unsigned a=0;a<3;a++){assert(isfinite(actors[i].position[a]));float v=actors[i].position[a]-prior[a];sum+=v*v;}distance+=sqrtf(sum);steps++;
 }
 assert(distance>500&&transitions>10);
 MwTrafficCar car;assert(mw_traffic_start(&w,&car,nearest,0,u,7,NULL,NULL,NULL));MwTrafficCar before=car;assert(mw_traffic_step(&w,&car,.01f,broken,NULL,NULL)==-1);assert(!memcmp(&car,&before,sizeof(car)));
 assert(mw_traffic_step(&w,&car,NAN,NULL,NULL,NULL)==-1);assert(!memcmp(&car,&before,sizeof(car)));
 assert(mw_traffic_step(&w,&car,.01f,deny,NULL,NULL)==0&&!car.active&&car.speed==0);assert(!memcmp(car.position,before.position,sizeof(car.position)));
 assert(!mw_traffic_start(&w,&car,nearest,2,u,8,NULL,NULL,NULL));assert(!mw_traffic_start(&w,&car,nearest,0,u,81,NULL,NULL,NULL));
 reject(data,0);reject(data,191);reject(data,bytes-1);reject(NULL,bytes);
 const unsigned offsets[]={0,4,8,12,16,20,24,28,32,36,40,44,48,52,56,60,128,132,136,140,191};
 for(unsigned i=0;i<sizeof(offsets)/sizeof(*offsets);i++){memcpy(bad,data,bytes);bad[offsets[i]]^=1;if(offsets[i]!=12)repair(bad,bytes);if(offsets[i]==128||offsets[i]==132||offsets[i]==136)continue;reject(bad,bytes);}
 memcpy(bad,data,bytes);bad[w.nodes_at+12]^=1;repair(bad,bytes);reject(bad,bytes);
 memcpy(bad,data,bytes);bad[w.nodes_at+16]=8;repair(bad,bytes);reject(bad,bytes);
 memcpy(bad,data,bytes);bad[w.segments_at+8]^=1;repair(bad,bytes);reject(bad,bytes);
 memcpy(bad,data,bytes);put(bad+w.grid_at+4,w.grid_refs+1);repair(bad,bytes);reject(bad,bytes);
 memcpy(bad,data,bytes);bad[w.refs_at]=255;bad[w.refs_at+1]=255;repair(bad,bytes);reject(bad,bytes);
 printf("Traffic: %u source adjacency references, %u bounded actor steps, %.1f source-units, %u transitions; max%u neighbor checks/%u samples per actor frame; spawn candidates%u; immutable pack%zuB, actor%zuB.\n",reciprocal,steps,(double)distance,transitions,checks_max,samples_max,query.nearest_checks,bytes,sizeof(MwTrafficCar));
 free(data);free(bad);return 0;
}
