/* Validates a private expanded native roster through the production readers. */
#include "mw_vehicle_catalog.h"
#include "nfs_scene.h"
#include "wheel_motion.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
static unsigned char *load(const char *path,size_t *bytes){
 FILE *f=fopen(path,"rb");assert(f&&!fseek(f,0,SEEK_END));long n=ftell(f);assert(n>0);rewind(f);
 unsigned char *p=malloc((size_t)n);assert(p&&fread(p,1,(size_t)n,f)==(size_t)n&&!fclose(f));*bytes=(size_t)n;return p;
}
static uint32_t word(const unsigned char*p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
int main(int argc,char**argv){
 assert(argc==2);char path[1024];size_t bytes;snprintf(path,sizeof(path),"%s/catalog.nvc",argv[1]);unsigned char*raw=load(path,&bytes);
 MwVehicleCatalog catalog;assert(mw_vehicle_catalog_open(&catalog,raw,bytes));
 unsigned player=0,triangles=0,textures=0;
 for(uint32_t i=0;i<catalog.count;i++){
  MwVehicleSpec car,again;assert(mw_vehicle_catalog_get(&catalog,i,&car));
  assert(mw_vehicle_catalog_find_id(&catalog,car.id,&again)&&again.ecar_key==car.ecar_key);
  player+=car.player_usable;
  snprintf(path,sizeof(path),"%s/%s/body.nfm",argv[1],car.id);unsigned char*body=load(path,&bytes);
  assert(word(body+24)==car.body_crc);NfsScene scene;assert(nfs_scene_decode(body,bytes,&scene));free(body);triangles+=scene.vertex_count/3;
  snprintf(path,sizeof(path),"%s/%s/wheels.nwa",argv[1],car.id);unsigned char*wheels=load(path,&bytes);
  assert(word(wheels+20)==car.wheel_crc);WheelRig rig;assert(wheel_rig_decode(wheels,bytes,scene.batch_count,car.body_crc,&rig));free(wheels);
  WheelMotion motion={0};DriveState start={0},next={.z=5};assert(wheel_motion_update(&rig,&motion,&start,&next));
  for(unsigned j=0;j<4;j++)assert(isfinite(motion.angle[j]));
  for(uint32_t t=0;t<scene.texture_count;t++){
   snprintf(path,sizeof(path),"%s/%s/textures/%08x.t3x",argv[1],car.id,scene.textures[t].key);
   FILE*f=fopen(path,"rb");assert(f&&!fseek(f,0,SEEK_END)&&ftell(f)>16&&!fclose(f));textures++;
  }
  wheel_rig_free(&rig);nfs_scene_free(&scene);
 }
 printf("Native roster: %u models, %u source PlayerUsable, %u triangles, %u texture dependencies validated.\n",catalog.count,player,triangles,textures);
 free(raw);return 0;
}
