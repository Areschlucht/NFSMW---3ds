#include "mw_vehicle_catalog.h"
#include "nfs_scene.h"
#include "wheel_motion.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned word(const unsigned char *p){return p[0]|(unsigned)p[1]<<8|(unsigned)p[2]<<16|(unsigned)p[3]<<24;}
static void put(unsigned char *p,unsigned x){for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(x>>(8*i));}
static void *load(const char *path,size_t *bytes){FILE *f=fopen(path,"rb");assert(f&&!fseek(f,0,SEEK_END));long n=ftell(f);assert(n>0);rewind(f);void *p=malloc((size_t)n);assert(p&&fread(p,1,(size_t)n,f)==(size_t)n);assert(!fclose(f));*bytes=(size_t)n;return p;}
static void checksum(unsigned char *p,size_t n){unsigned c=~0u;for(size_t i=16;i<n;i++){c^=p[i];for(unsigned j=0;j<8;j++)c=(c>>1)^(0xedb88320u&-(c&1u));}put(p+12,~c);}
static void rejected(void *raw,size_t n){MwVehicleCatalog out={.bytes=123};assert(!mw_vehicle_catalog_open(&out,raw,n));assert(!out.data&&out.bytes==123);}
int main(int argc,char **argv){
    assert(argc==3);size_t bytes;unsigned char *raw=load(argv[1],&bytes);MwVehicleCatalog catalog;
    assert(mw_vehicle_catalog_open(&catalog,raw,bytes)&&catalog.count==5);unsigned starters=0,traffic=0,triangles=0,old_crcs[5]={0};
    for(uint32_t i=0;i<catalog.count;i++){
        MwVehicleSpec s,by_id,by_front;assert(mw_vehicle_catalog_get(&catalog,i,&s));assert(mw_vehicle_catalog_find_id(&catalog,s.id,&by_id)&&by_id.body_crc==s.body_crc);
        if(s.frontend_key){assert(mw_vehicle_catalog_find_frontend(&catalog,s.frontend_key,&by_front)&&!strcmp(by_front.id,s.id));starters++;}else{assert(!strcmp(s.id,"TRAFHA"));traffic++;}
        char path[512];snprintf(path,sizeof(path),"%s/%s/body.nfm",argv[2],s.id);size_t n;unsigned char *body=load(path,&n);NfsScene scene;assert(nfs_scene_decode(body,n,&scene)&&word(body+24)==s.body_crc);assert(scene.vertex_count>1000&&scene.texture_count>3);triangles+=scene.vertex_count/3;
        for(unsigned j=0;j<i;j++){assert(old_crcs[j]!=s.body_crc);}old_crcs[i]=s.body_crc;
        snprintf(path,sizeof(path),"%s/%s/wheels.nwa",argv[2],s.id);size_t wn;unsigned char *wheels=load(path,&wn);assert(word(wheels+20)==s.wheel_crc);WheelRig rig;assert(wheel_rig_decode(wheels,wn,scene.batch_count,s.body_crc,&rig));
        WheelMotion motion={0};DriveState before={0},after={.z=3};assert(wheel_motion_update(&rig,&motion,&before,&after));for(unsigned j=0;j<4;j++)assert(isfinite(motion.angle[j])&&motion.angle[j]!=0);wheel_rig_free(&rig);
        assert(!wheel_rig_decode(wheels,wn,scene.batch_count,s.body_crc^1,&rig));
        for(unsigned j=0;j<scene.texture_count;j++){snprintf(path,sizeof(path),"%s/%s/textures/%08x.t3x",argv[2],s.id,scene.textures[j].key);FILE *f=fopen(path,"rb");assert(f&&!fseek(f,0,SEEK_END)&&ftell(f)>16);assert(!fclose(f));}
        printf("%s: %u triangles, %u source texture bindings, extent %.6f\n",s.id,scene.vertex_count/3,scene.texture_count,(double)s.half_extent);nfs_scene_free(&scene);free(body);free(wheels);
    }
    assert(starters==4&&traffic==1&&triangles>25000);MwVehicleSpec unchanged={.id="SENTINEL"},out=unchanged;assert(!mw_vehicle_catalog_find_id(&catalog,"NOT_A_CAR",&out)&&out.id==unchanged.id);assert(!mw_vehicle_catalog_find_frontend(&catalog,0,&out));assert(!mw_vehicle_catalog_get(&catalog,5,&out));
    rejected(raw,0);rejected(raw,95);rejected(raw,bytes-1);rejected(raw,bytes+1);unsigned char *bad=malloc(bytes);assert(bad);
    const unsigned at[]={0,4,8,12,16,20,24,28,32,96+16,96+20,96+24,96+56,96+120,96+152};
    for(unsigned i=0;i<sizeof(at)/sizeof(*at);i++){memcpy(bad,raw,bytes);bad[at[i]]^=1;rejected(bad,bytes);}
    memcpy(bad,raw,bytes);memcpy(bad+96+24,"../BAD",7);checksum(bad,bytes);rejected(bad,bytes);
    memcpy(bad,raw,bytes);float nan=NAN;memcpy(bad+96+16,&nan,4);checksum(bad,bytes);rejected(bad,bytes);
    memcpy(bad,raw,bytes);put(bad+96+160+4,word(bad+96+4));checksum(bad,bytes);rejected(bad,bytes);
    memcpy(bad,raw,bytes);put(bad+16,0xffffffffu);checksum(bad,bytes);rejected(bad,bytes);
    memcpy(bad,raw,bytes);bad[64]^=1;checksum(bad,bytes);rejected(bad,bytes);
    free(bad);free(raw);puts("Four genuine starter candidates and one traffic car decode; rigs, texture dependencies, uniqueness and catalog corruption guards pass.");return 0;
}
