/* Private staged-asset integration: checks every model through native readers,
 * including cross-pack catalog identities and renderer texture dependencies. */
#include "mw_vehicle_catalog.h"
#include "nfs_scene.h"
#include "wheel_motion.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void *load(const char *path,size_t *bytes)
{
    FILE *f=fopen(path,"rb");assert(f&&!fseek(f,0,SEEK_END));long n=ftell(f);
    assert(n>0);rewind(f);void *p=malloc((size_t)n);
    assert(p&&fread(p,1,(size_t)n,f)==(size_t)n&&!fclose(f));*bytes=(size_t)n;return p;
}
int main(int argc,char **argv)
{
    assert(argc==2||argc==3);unsigned expected=argc==3?(unsigned)strtoul(argv[2],NULL,10):12;assert(expected&&expected<=128);char path[1024];size_t bytes;
    snprintf(path,sizeof(path),"%s/cars/catalog.nvc",argv[1]);void *raw=load(path,&bytes);
    MwVehicleCatalog catalog;assert(mw_vehicle_catalog_open(&catalog,raw,bytes)&&catalog.count==expected);
    unsigned selectable=0,police=0,traffic=0,opponents=0,triangles=0,textures=0;
    for(unsigned i=0;i<catalog.count;i++){
        MwVehicleSpec car,found;assert(mw_vehicle_catalog_get(&catalog,i,&car));
        assert(mw_vehicle_catalog_find_id(&catalog,car.id,&found)&&found.ecar_key==car.ecar_key);
        if(car.frontend_key){
            selectable++;assert(mw_vehicle_catalog_find_frontend(&catalog,car.frontend_key,&found));
            assert(!strcmp(found.id,car.id));
        }else if(!strcmp(car.id,"COPMIDSIZE"))police++;
        else if(!strcmp(car.id,"TRAFHA"))traffic++;
        else opponents++;
        snprintf(path,sizeof(path),"%s/cars/%s/body.nfm",argv[1],car.id);
        void *body=load(path,&bytes);NfsScene scene;assert(nfs_scene_decode(body,bytes,&scene));
        triangles+=scene.vertex_count/3;
        snprintf(path,sizeof(path),"%s/cars/%s/wheels.nwa",argv[1],car.id);
        void *wheel=load(path,&bytes);WheelRig rig;
        assert(wheel_rig_decode(wheel,bytes,scene.batch_count,car.body_crc,&rig));
        WheelMotion motion={0};DriveState start={0},next={.z=3};
        assert(wheel_motion_update(&rig,&motion,&start,&next));
        for(unsigned t=0;t<scene.texture_count;t++){
            snprintf(path,sizeof(path),"%s/cars/%s/textures/%08x.t3x",argv[1],car.id,scene.textures[t].key);
            FILE *f=fopen(path,"rb");assert(f&&!fseek(f,0,SEEK_END)&&ftell(f)>16&&!fclose(f));textures++;
        }
        printf("%s: %u source triangles, %u texture bindings\n",car.id,scene.vertex_count/3,scene.texture_count);
        wheel_rig_free(&rig);nfs_scene_free(&scene);free(wheel);free(body);
    }
    if(expected==12)assert(selectable==4&&police==1&&traffic==1&&opponents==6);
    printf("%u actual models validated: %u triangles, %u texture bindings.\n",catalog.count,triangles,textures);
    free(raw);return 0;
}
