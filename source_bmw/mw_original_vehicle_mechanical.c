#include "mw_original_vehicle_mechanical.h"
#include "mw_original_power.h"
#include <math.h>
#include <string.h>
static float f32(float x){volatile float out=x;return out;}
static uint32_t word(const unsigned char *p){return p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned j=0;j<8;j++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
bool mw_vehicle_mechanical_profile_open(MwVehicleMechanicalProfile *out,const void *data,size_t bytes)
{
    if(!out||!data||bytes!=156)return false;
    const unsigned char *p=data;
    if(memcmp(p,"MMP1",4)||word(p+4)!=1||word(p+8)!=bytes||word(p+12)!=crc(p+16,bytes-16)||!word(p+16)||!word(p+20)||word(p+24)!=128||word(p+28)!=7)return false;
    for(unsigned i=32;i<64;i++)if(p[i])return false;
    static const unsigned char attr[32]={91,105,196,79,252,252,112,19,163,242,73,0,179,54,23,0,43,31,104,242,72,74,145,8,218,165,191,229,215,42,210,12};
    static const unsigned char dol[32]={51,197,234,230,153,248,113,190,172,5,155,105,50,71,92,173,94,159,97,11,178,178,41,142,4,109,4,55,87,185,65,102};
    if(memcmp(p+64,attr,32)||memcmp(p+96,dol,32))return false;
    float values[7];for(unsigned i=0;i<7;i++){uint32_t bits=word(p+128+i*4);memcpy(values+i,&bits,4);if(!isfinite(values[i]))return false;}
    MwVehicleMechanicalProfile profile={.physical_key=word(p+16),.chassis_key=word(p+20),
        .params={values[0],values[1],values[2],values[3],values[4],values[5],values[6]}};
    *out=profile;return true;
}
static bool vector_valid(MwPhysicsContactVector v){return isfinite(v.x)&&isfinite(v.y)&&isfinite(v.z);}
static MwPhysicsContactVector rotate(const float *m,MwPhysicsContactVector v)
{
    return (MwPhysicsContactVector){
        fmaf(m[8],v.z,fmaf(m[4],v.y,f32(m[0]*v.x))),
        fmaf(m[9],v.z,fmaf(m[5],v.y,f32(m[1]*v.x))),
        fmaf(m[10],v.z,fmaf(m[6],v.y,f32(m[2]*v.x)))};
}
static MwPhysicsContactVector point(const float *m,MwPhysicsContactVector v)
{
    v=rotate(m,v);return (MwPhysicsContactVector){f32(v.x+m[12]),f32(v.y+m[13]),f32(v.z+m[14])};
}
void mw_vehicle_mechanical_calibration(MwVehicleMechanicalParams *p)
{
    if(!p)return;
    p->off_throttle_drag_multiplier=2.0f;p->off_throttle_drag_height=-.10000000149011612f;
    p->aero_direction_exponent=.5f;p->aero_direction_minimum=.4000000059604645f;
}
bool mw_vehicle_mechanical(const MwVehicleMechanicalParams *p,const MwVehicleMechanicalInput *in,
    MwVehicleMechanicalOutput *out,const MwVehicleMechanicalMath *math)
{
    if(!p||!in||!out)return false;
    const float parameters[]={p->drag_coefficient,p->aero_coefficient,p->aero_cg_percent,
        p->off_throttle_drag_multiplier,p->off_throttle_drag_height,p->aero_direction_exponent,p->aero_direction_minimum};
    const float inputs[]={in->speed,in->throttle,in->contact_fraction,in->drag_scale,in->downforce_scale,
        in->front_mount_z,in->rear_mount_z};
    for(unsigned i=0;i<sizeof(parameters)/sizeof(*parameters);i++)if(!isfinite(parameters[i]))return false;
    for(unsigned i=0;i<sizeof(inputs)/sizeof(*inputs);i++)if(!isfinite(inputs[i]))return false;
    for(unsigned i=0;i<16;i++)if(!isfinite(in->body_matrix[i]))return false;
    if(!vector_valid(in->world_velocity)||!vector_valid(in->local_cg)||(in->effect_present&&!isfinite(in->effect_value)))return false;
    MwVehicleMechanicalOutput result={0};
    if(in->drag_scale>0){
        float multiplier=f32(f32(in->speed*in->drag_scale)*p->drag_coefficient);
        float off_throttle=f32(1-in->throttle);
        multiplier=fmaf(f32(multiplier*f32(p->off_throttle_drag_multiplier-1)),off_throttle,multiplier);
        if(in->effect_present)multiplier=fmaf(multiplier,f32(in->effect_value*.25f),multiplier);
        multiplier=-multiplier;
        MwPhysicsContactVector force={f32(in->world_velocity.x*multiplier),f32(in->world_velocity.y*multiplier),f32(in->world_velocity.z*multiplier)};
        MwPhysicsContactVector cg=in->local_cg;
        if(in->contact_fraction>=.5f)cg.y=fmaf(p->off_throttle_drag_height,off_throttle,cg.y);
        result.forces[result.count++]=(MwVehicleMechanicalForce){force,point(in->body_matrix,cg),1};
    }
    if(in->downforce_scale>0){
        float vertical=in->body_matrix[5]>0?in->body_matrix[5]:0;
        if(in->contact_fraction>=.5f)vertical=1;
        MwPhysicsContactVector forward={in->body_matrix[8],in->body_matrix[9],in->body_matrix[10]},direction=forward;
        if(in->speed>.00009999999747378752f){
            float inv=f32(1/in->speed);
            direction=(MwPhysicsContactVector){f32(in->world_velocity.x*inv),f32(in->world_velocity.y*inv),f32(in->world_velocity.z*inv)};
        }
        float dot=fmaf(direction.z,forward.z,f32(f32(direction.x*forward.x)+f32(direction.y*forward.y)));
        if(dot<0)dot=0;
        double alignment=math&&math->power?math->power(dot,p->aero_direction_exponent,math->context):mw_original_power_callback(dot,p->aero_direction_exponent,NULL);
        if(!isfinite(alignment))return false;
        if(alignment<p->aero_direction_minimum)alignment=p->aero_direction_minimum;
        float aero=f32(f32(f32(in->speed+in->speed)*p->aero_coefficient)*1000);
        float force=f32((double)f32(in->downforce_scale*vertical)*alignment);
        force=f32(force*aero);
        if(in->contact_fraction==0)force=f32(force*.80000001192092896f);
        if(in->effect_present)force=fmaf(force,f32(in->effect_value*.25f),force);
        if(force>0){
            MwPhysicsContactVector cg=in->local_cg;
            if(in->contact_fraction!=0)cg.z=fmaf(f32(f32(in->front_mount_z-in->rear_mount_z)*.0099999997764825821f),p->aero_cg_percent,in->rear_mount_z);
            MwPhysicsContactVector local_force={0,-force,0};
            result.forces[result.count++]=(MwVehicleMechanicalForce){rotate(in->body_matrix,local_force),point(in->body_matrix,cg),2};
        }
    }
    for(uint32_t i=0;i<result.count;i++)if(!vector_valid(result.forces[i].force)||!vector_valid(result.forces[i].world_point))return false;
    *out=result;return true;
}
