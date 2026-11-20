#include "mw_original_vehicle_mechanical.h"
#include <assert.h>
#include <float.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned j=0;j<8;j++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
static void put(unsigned char *p,uint32_t n){for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(n>>(i*8));}
static void near(float a,float b){assert(fabsf(a-b)<.0001f);}
int main(int argc,char **argv)
{
    MwVehicleMechanicalParams p={.drag_coefficient=.25f,.aero_coefficient=.125f,.aero_cg_percent=50};
    mw_vehicle_mechanical_calibration(&p);
    MwVehicleMechanicalInput in={.body_matrix={1,0,0,0,0,1,0,0,0,0,1,0,10,20,30,1},
        .world_velocity={0,0,16},.local_cg={.125f,.375f,-.25f},.speed=16,.throttle=1,
        .contact_fraction=1,.drag_scale=1,.downforce_scale=1,.front_mount_z=1.5f,.rear_mount_z=-1.25f};
    MwVehicleMechanicalOutput out;
    assert(mw_vehicle_mechanical(&p,&in,&out,NULL)&&out.count==2);
    assert(out.forces[0].kind==1&&out.forces[1].kind==2);
    assert(out.forces[0].force.z==-64&&out.forces[1].force.y==-4000);
    near(out.forces[0].world_point.x,10.125f);near(out.forces[0].world_point.y,20.375f);near(out.forces[0].world_point.z,29.75f);
    near(out.forces[1].world_point.z,30.125f);
    in.throttle=0;assert(mw_vehicle_mechanical(&p,&in,&out,NULL));assert(out.forces[0].force.z==-128);near(out.forces[0].world_point.y,20.275f);
    in.throttle=1;in.effect_present=true;in.effect_value=4;
    assert(mw_vehicle_mechanical(&p,&in,&out,NULL));assert(out.forces[0].force.z==-128&&out.forces[1].force.y==-8000);
    in.effect_present=false;in.effect_value=NAN;in.contact_fraction=0;in.world_velocity.z=-16;
    assert(mw_vehicle_mechanical(&p,&in,&out,NULL));assert(out.forces[1].force.y==-1280);near(out.forces[1].world_point.z,29.75f);
    in.body_matrix[5]=-1;in.body_matrix[10]=-1;assert(mw_vehicle_mechanical(&p,&in,&out,NULL));assert(out.count==1);
    in.contact_fraction=1;assert(mw_vehicle_mechanical(&p,&in,&out,NULL)&&out.count==2&&out.forces[1].force.y==4000);
    in.drag_scale=0;in.downforce_scale=0;assert(mw_vehicle_mechanical(&p,&in,&out,NULL)&&!out.count);
    memset(&out,0xa5,sizeof(out));MwVehicleMechanicalOutput before=out;
    in.drag_scale=NAN;assert(!mw_vehicle_mechanical(&p,&in,&out,NULL)&&!memcmp(&out,&before,sizeof(out)));
    in.drag_scale=FLT_MAX;in.speed=FLT_MAX;assert(!mw_vehicle_mechanical(&p,&in,&out,NULL)&&!memcmp(&out,&before,sizeof(out)));
    assert(!mw_vehicle_mechanical(NULL,&in,&out,NULL)&&!mw_vehicle_mechanical(&p,NULL,&out,NULL)&&!mw_vehicle_mechanical(&p,&in,NULL,NULL));
    if(argc==2){
        unsigned char raw[156],bad[156];FILE *f=fopen(argv[1],"rb");assert(f);assert(fread(raw,1,sizeof(raw),f)==sizeof(raw)&&fgetc(f)==EOF);fclose(f);
        MwVehicleMechanicalProfile profile;assert(mw_vehicle_mechanical_profile_open(&profile,raw,sizeof(raw)));
        assert(profile.physical_key==0x39dae0f8&&profile.chassis_key);
        near(profile.params.drag_coefficient,.3f);near(profile.params.aero_coefficient,.24f);near(profile.params.aero_cg_percent,47.5f);
        MwVehicleMechanicalProfile original=profile;
        for(unsigned i=0;i<sizeof(raw);i++){
            memcpy(bad,raw,sizeof(raw));bad[i]^=1;
            assert(!mw_vehicle_mechanical_profile_open(&profile,bad,sizeof(bad))&&!memcmp(&profile,&original,sizeof(profile)));
        }
        const unsigned positions[]={0,4,8,16,20,24,28,32,64,96};
        for(unsigned i=0;i<sizeof(positions)/sizeof(*positions);i++){
            memcpy(bad,raw,sizeof(raw));unsigned at=positions[i];
            if(at==16||at==20)put(bad+at,0);else bad[at]^=1;
            put(bad+12,crc(bad+16,sizeof(bad)-16));
            assert(!mw_vehicle_mechanical_profile_open(&profile,bad,sizeof(bad)));
        }
        memcpy(bad,raw,sizeof(raw));put(bad+128,0x7fc00000);put(bad+12,crc(bad+16,sizeof(bad)-16));assert(!mw_vehicle_mechanical_profile_open(&profile,bad,sizeof(bad)));
        assert(!mw_vehicle_mechanical_profile_open(&profile,raw,sizeof(raw)-1)&&!mw_vehicle_mechanical_profile_open(&profile,raw,sizeof(raw)+1));
    }
    puts("Mechanical: ordered drag/downforce, throttle/effect/contact/air/inversion, rollback and source-profile corruption checks pass.");
}
