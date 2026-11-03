#include "mw_physics_transmission_nos.h"
#include <math.h>
static float f32(float v){volatile float r=v;return r;}
bool mw_physics_transmission_nos_step(const MwPhysicsTransmissionNosParams *p,
    const MwPhysicsTransmissionNosInput *in,MwPhysicsTransmissionNosState *state,float *scale)
{
    if(!p||!in||!state||!scale)return false;
    const float all[]={p->disengage,p->torque_boost,p->capacity,p->recharge_min,p->recharge_max,
        p->recharge_min_speed,p->recharge_max_speed,in->seconds,in->applied_throttle,
        in->vehicle_speed_128,in->boost_interface_scalar,in->tuning_14,state->charge,state->activity};
    for(unsigned i=0;i<sizeof all/sizeof *all;++i)if(!isfinite(all[i]))return false;
    if(in->seconds<0)return false;
    /* Original IEngineNOS.slot60 checks positive raw capacity and torque boost. */
    if(p->capacity<=0||p->torque_boost<=0){*scale=1;return true;}
    float charge=state->charge,activity=state->activity;
    float speed=f32(in->vehicle_speed_128*2.236989974975586f),recharge=0;
    if(!in->recharge_inhibited&&speed>=p->recharge_min_speed&&in->gear_slot>1) {
        float range=f32(p->recharge_max_speed-p->recharge_min_speed),fraction=0;
        if(range>0.0000009999999974752427f) {
            fraction=f32(f32(speed-p->recharge_min_speed)/range);
            if(fraction>1)fraction=1;
            if(fraction<0)fraction=0;
        }
        recharge=fmaf(f32(p->recharge_max-p->recharge_min),fraction,p->recharge_min);
    }
    bool request=in->requested&&in->gear_slot>1&&in->applied_throttle>0&&!in->rev_block;
    bool active=activity>=1;
    if(speed<10&&!active)request=false;
    if(speed<5&&active)request=false;
    float capacity=p->capacity;
    if(in->tuning_present)capacity=f32(capacity-f32(f32(capacity*in->tuning_14)*.25f));
    float result=1;
    if(capacity<=0){activity=0;charge=0;}
    else if(request&&charge>0) {
        float drain=f32(in->seconds/capacity);
        if(in->unlimited_global||in->vehicle_mode_b8==6)drain=0;
        if(in->boost_interface_present)drain=f32(drain*fmaf(in->boost_interface_scalar,-.5f,1));
        charge=f32(charge-drain);
        if(charge<0)charge=0;
        activity=1;
        float boost=p->torque_boost;
        if(in->tuning_present)boost=fmaf(f32(boost*in->tuning_14),.25f,boost);
        result=f32(boost+1);
    } else if(activity>0&&p->disengage>0) {
        activity=f32(activity-f32(in->seconds/p->disengage));
        if(activity<0)activity=0;
    } else if(charge<1&&recharge>0) {
        float refill=f32(in->seconds/recharge);
        if(in->boost_interface_present)refill=f32(refill*f32(in->boost_interface_scalar+1));
        charge=f32(charge+refill);
        if(charge>1)charge=1;
        activity=0;
    } else activity=0;
    state->charge=charge;state->activity=activity;*scale=result;return true;
}
