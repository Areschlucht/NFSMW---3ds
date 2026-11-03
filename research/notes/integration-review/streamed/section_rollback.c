#include "streamed_world.h"
#include "world_streaming.h"
#include <assert.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef struct {const char *root;bool fail;unsigned section_reads;} Reader;
static StreamedWorldResult read_asset(void *context,StreamedWorldAssetKind kind,uint32_t id,const uint8_t identity[32],void *destination,size_t capacity,size_t *bytes){
 Reader *r=context;char path[1024];
 if(kind==STREAMED_WORLD_SECTION){
  if(destination&&r->fail&&++r->section_reads==2)return STREAMED_WORLD_IO;
  snprintf(path,sizeof(path),"%s/sections/%u.wsi",r->root,id);
 }else if(kind==STREAMED_WORLD_MODEL)snprintf(path,sizeof(path),"%s/models/%08x.wsm",r->root,id);
 else {assert(identity);char digest[65];for(unsigned i=0;i<32;++i)snprintf(digest+i*2,3,"%02x",identity[i]);snprintf(path,sizeof(path),"%s/textures/%08x-%s.wtx",r->root,id,digest);}
 FILE *f=fopen(path,"rb");if(!f)return STREAMED_WORLD_MISSING;
 assert(!fseek(f,0,SEEK_END));long n=ftell(f);assert(n>0);*bytes=(size_t)n;
 if(!destination){fclose(f);return capacity?STREAMED_WORLD_INVALID:STREAMED_WORLD_OK;}
 if(capacity<(size_t)n){fclose(f);return STREAMED_WORLD_CAPACITY;}
 rewind(f);bool ok=fread(destination,1,(size_t)n,f)==(size_t)n;fclose(f);return ok?STREAMED_WORLD_OK:STREAMED_WORLD_IO;
}
static float number(const unsigned char*p){uint32_t u=(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;float x;memcpy(&x,&u,4);return x;}
static unsigned short half(const unsigned char*p){return (unsigned short)(p[0]|(unsigned)p[1]<<8);}
static uint64_t draw(StreamedWorld *w){shaderProgram_s p={0};C3D_Mtx m;Mtx_Identity(&m);mock_draw_stream_hash=UINT64_C(14695981039346656037);streamed_world_draw(w,&p,0,1,&m);return mock_draw_stream_hash;}
int main(int argc,char **argv){
 assert(argc==3);Reader reader={.root=argv[1]};StreamedWorldConfig cfg={.metadata_path=argv[2],.read_asset=read_asset,.read_context=&reader,.normal_bytes=20*1024*1024,.linear_bytes=24*1024*1024,.scratch_bytes=4*1024*1024,.cache_entries=2048,.object_capacity=8192,.run_capacity=65536,.render_scale=.001f,.lod_mode=STREAMED_WORLD_REFERENCE_SLOT0,.alpha_reference=40};
 StreamedWorld *w=NULL;assert(streamed_world_create(&cfg,&w)==STREAMED_WORLD_OK);
 StreamedWorldView view={.camera_viewer={360,180,-2410},.forward_viewer={0,0,1},.up_viewer={0,1,0},.vertical_fov_radians=1,.aspect=400.f/240,.near_world=.15f,.far_world=350,.original_fov_turn=0x3000};assert(streamed_world_prepare(w,360,2410,&view)==STREAMED_WORLD_OK);
 StreamedWorldStats first;streamed_world_stats(w,&first);uint64_t original=draw(w);
 FILE *f=fopen(argv[2],"rb");assert(f);assert(!fseek(f,0,SEEK_END));long n=ftell(f);rewind(f);unsigned char *bytes=malloc((size_t)n);assert(bytes);assert(fread(bytes,1,(size_t)n,f)==(size_t)n);fclose(f);WorldStreamingDatabase db;assert(world_streaming_open(bytes,(size_t)n,&db)==WORLD_STREAMING_OK);
 WorldStreamingSelector selector;world_streaming_selector_init(&db,&selector);uint16_t selected,old_ids[147];size_t old_n;assert(world_streaming_select(&db,&selector,360,2410,&selected)==WORLD_STREAMING_OK);assert(world_streaming_plan(&db,&selected,1,old_ids,147,&old_n)==WORLD_STREAMING_OK);
 float x=0,y=0;bool found=false;unsigned region=0;
 for(uint32_t p=0;p<db.polygon_count&&!found;++p){const unsigned char *poly=db.data+db.polygons+p*36;float cx=(number(poly+8)+number(poly+16))*.5f,cy=(number(poly+12)+number(poly+20))*.5f;WorldStreamingSelector candidate=selector;uint16_t ix,ids[147];size_t count;if(world_streaming_select(&db,&candidate,cx,cy,&ix)!=WORLD_STREAMING_OK)continue;unsigned id=half(db.data+db.dependencies+ix*12);if(id==first.region)continue;assert(world_streaming_plan(&db,&ix,1,ids,147,&count)==WORLD_STREAMING_OK);unsigned added=0;for(size_t i=0;i<count;++i){bool exists=false;for(size_t j=0;j<old_n;++j)exists|=ids[i]==old_ids[j];added+=!exists;}if(added>=2){found=true;x=cx;y=cy;region=id;}}
 assert(found);
 for(unsigned pass=0;pass<40;++pass){
  reader.fail=true;reader.section_reads=0;assert(streamed_world_prepare(w,x,y,&view)==STREAMED_WORLD_IO);assert(reader.section_reads==2);reader.fail=false;
  StreamedWorldStats failed;streamed_world_stats(w,&failed);assert(failed.region==first.region&&failed.draw_runs==first.draw_runs&&failed.visible_instances==first.visible_instances&&failed.normal_used==first.normal_used&&failed.linear_used==first.linear_used);assert(draw(w)==original);
  assert(streamed_world_prepare(w,360,2410,&view)==STREAMED_WORLD_OK);StreamedWorldStats recovered;streamed_world_stats(w,&recovered);assert(recovered.normal_used==first.normal_used&&recovered.linear_used==first.linear_used);assert(draw(w)==original);
 }
 streamed_world_destroy(w);assert(mock_linear_used==0);free(bytes);printf("Changed-region section IO rollback: 40 fail/recover cycles region%u -> staged%u; partial section allocations and borrowed owners released; old ordered GPU stream %016" PRIx64 " preserved; GPU resources zero after destroy.\n",first.region,region,original);return 0;
}
