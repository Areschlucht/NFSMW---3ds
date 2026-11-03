#include "world_collision_runtime.h"
#include <assert.h>
#include <math.h>
static WorldCollisionRuntime world;
static unsigned char arena[4096];
static void test_queries(void){
    WorldCollisionContact c;float p[3]={101.2f,5,203.2f};
    assert(world_collision_runtime_ground(&world,p,0,&c)==1);
    assert(c.kind==1&&fabsf(c.point_native[1]-4)<.00001f&&c.material_key==0x19db2f1e);
    assert(c.normal_native[1]==.9999f&&c.primitive_flags==0&&c.collision_id==101);
    assert(c.instance_flags==0); /* original mixed mesh+wall keeps CI flags */
    float a[3]={101,4,199},b[3]={101,4,201};
    assert(world_collision_runtime_wall(&world,a,b,0,&c)==1);
    assert(c.kind==2&&c.point_native[2]==200&&c.normal_native[2]==-1);
    assert(c.primitive_flags==0xc2&&c.material_key==0x19db2f1e); /* original loader mutation */
    assert(world_collision_runtime_wall(&world,a,b,64,&c)==0);
    assert(world_collision_runtime_wall(&world,a,b,2,&c)==0);
}
int main(int argc,char **argv){
    assert(argc==5);WorldCollisionAdmission a;WorldCollisionContact c;
    uint16_t first[]={141},second[]={142},both[]={141,142},aliases[]={141,143},alias[]={143},reverse[]={142,141};
    assert(world_collision_runtime_open(&world,argv[1],arena,sizeof arena)==0);
    assert(world_collision_runtime_open(&world,argv[1],arena,sizeof arena)==WORLD_COLLISION_INVALID);
    assert(world.package_count==2&&world.association_count==3);
    float old[3]={101.2f,5,203.2f},other[3]={111.2f,5,203.2f};
    assert(world_collision_runtime_ground(&world,old,0,&c)==WORLD_COLLISION_NOT_READY);
    assert(world_collision_runtime_admit(&world,both,2,&a)==0&&a.unique_packages==2);
    world.arena_capacity=world.packages[0].bytes;
    assert(world_collision_runtime_activate(&world,first,1,&a)==0&&world.active_count==1);
    assert(a.retained_packages==0&&a.required_read_bytes==world.arena_used);test_queries();
    assert(world_collision_runtime_ground(&world,old,0,&c)==1&&c.source_ci_offset==256&&c.source_asset_offset==128);
    assert(world_collision_runtime_activate(&world,both,2,&a)==WORLD_COLLISION_BUDGET);
    assert(world.ready&&world.active_count==1);test_queries();
    world.arena_capacity=sizeof arena;
    assert(world_collision_runtime_activate(&world,aliases,2,&a)==0&&a.unique_packages==1&&a.retained_packages==1&&a.required_read_bytes==0);
    assert(world_collision_runtime_activate(&world,alias,1,&a)==0&&a.required_read_bytes==0);
    assert(world_collision_runtime_ground(&world,old,0,&c)==1&&c.section_id==143&&c.source_ci_offset==896&&c.source_asset_offset==768);
    assert(world_collision_runtime_activate(&world,second,1,&a)==0&&a.retained_packages==0);
    assert(world_collision_runtime_ground(&world,old,0,&c)==0);
    assert(world_collision_runtime_ground(&world,other,0,&c)==1&&c.section_id==142&&c.source_ci_offset==576);
    assert(world_collision_runtime_activate(&world,reverse,2,&a)==0&&a.retained_packages==1);
    assert(world_collision_runtime_activate(&world,first,1,&a)==0&&a.required_read_bytes==0);
    assert(world_collision_runtime_activate(&world,reverse,2,&a)==0&&a.retained_packages==1);
    assert(world_collision_runtime_activate(&world,both,2,&a)==0&&a.retained_packages==2&&a.required_read_bytes==0);
    test_queries();assert(world_collision_runtime_ground(&world,other,0,&c)==1);
    float origin[3]={200,2,100},view[3],native[3];world_collision_native_to_viewer(old,origin,view);
    world_collision_viewer_to_native(view,origin,native);for(unsigned k=0;k<3;k++)assert(native[k]==old[k]);
    world_collision_native_vector_to_viewer((float[3]){1,2,3},view);assert(view[0]==3&&view[1]==2&&view[2]==1);
    assert(world_collision_runtime_activate(&world,NULL,0,&a)==0&&world.ready&&world.active_count==0);
    assert(world_collision_runtime_ground(&world,old,0,&c)==0);
    world_collision_runtime_close(&world);
    assert(world_collision_runtime_open(&world,argv[2],arena,sizeof arena)==0);
    assert(world_collision_runtime_activate(&world,second,1,&a)==WORLD_COLLISION_CORRUPT&&!world.ready&&!world.active_count);
    assert(world_collision_runtime_ground(&world,old,0,&c)==WORLD_COLLISION_NOT_READY);
    assert(world_collision_runtime_activate(&world,first,1,&a)==0);test_queries();world_collision_runtime_close(&world);
    assert(world_collision_runtime_open(&world,argv[3],arena,sizeof arena)==0);
    assert(world_collision_runtime_activate(&world,first,1,&a)==WORLD_COLLISION_CORRUPT&&!world.ready);world_collision_runtime_close(&world);
    assert(world_collision_runtime_open(&world,argv[4],arena,sizeof arena)==WORLD_COLLISION_CORRUPT&&!world.file);
    return 0;
}
