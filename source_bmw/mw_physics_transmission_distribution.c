#include "mw_physics_transmission_distribution.h"
#include <math.h>
#include <string.h>
static float f32(float value){volatile float rounded=value;return rounded;}
static float bounded01(float v){if(v>1)v=1;if(v<0)v=0;return v;}
bool mw_physics_transmission_distribute(const MwPhysicsTransmissionDistribution *p,
    MwPhysicsTransmissionWheel wheels[4],float (*angle)(float,float))
{
    if(!p||!wheels||!isfinite(p->engine_output_torque)||!isfinite(p->torque_split)||
       !isfinite(p->body_local_lateral_velocity)||!isfinite(p->body_local_forward_velocity)||
       !isfinite(p->steering)||!isfinite(p->assist_strength))return false;
    for(unsigned i=0;i<3;++i)if(!isfinite(p->differential[i]))return false;
    for(unsigned i=0;i<4;++i) {
        const MwPhysicsTransmissionWheel *w=wheels+i;
        if(!isfinite(w->angular_speed)||!isfinite(w->spring_compression)||
           !isfinite(w->longitudinal_slip)||!isfinite(w->last_lateral_velocity)||
           !isfinite(w->drive_torque)||!isfinite(w->grip_factor))return false;
    }
    if(p->engine_output_torque==0)return true;
    MwPhysicsTransmissionWheel result[4];memcpy(result,wheels,sizeof result);
    float axle[2]={p->torque_split,f32(1.0f-p->torque_split)};
    if(p->differential[2]>0) {
        MwPhysicsTransmissionDifferentialInput center={
            .angular_speed={f32(wheels[0].angular_speed+wheels[1].angular_speed),
                            f32(wheels[2].angular_speed+wheels[3].angular_speed)},
            .contacted={wheels[0].spring_compression>0||wheels[1].spring_compression>0,
                        wheels[2].spring_compression>0||wheels[3].spring_compression>0},
            .base_ratio=p->torque_split,.locking=p->differential[2]};
        if(!mw_physics_transmission_differential(&center,false,axle))return false;
    }
    for(unsigned a=0;a<2;++a) {
        float torque=f32(p->engine_output_torque*axle[a]);
        if(fabsf(torque)<=0.0000009999999974752427f)continue;
        unsigned first=a*2;float slip=0,lateral=0;
        float grip_multiplier[2]={1,1},drive_multiplier[2]={1,1};
        float base=0.5f;bool override=false;
        for(unsigned j=0;j<2;++j) {
            const MwPhysicsTransmissionWheel *w=wheels+first+j;
            slip=fmaf(f32(axle[a]*w->longitudinal_slip),0.5f,slip);
            lateral=fmaf(f32(axle[a]*w->last_lateral_velocity),0.5f,lateral);
        }
        if(p->assist_flags&1) {
            grip_multiplier[1]=p->assist_strength;
            base=f32(p->assist_strength*0.5f);override=true;
        } else if(p->assist_flags&2) {
            grip_multiplier[0]=p->assist_strength;
            base=f32(1.0f-f32(p->assist_strength*0.5f));override=true;
        } else {
            float delta=f32(lateral-p->body_local_lateral_velocity);
            if(f32(delta*p->steering)>0 && f32(torque*slip)>0) {
                float forward=f32(slip-p->body_local_forward_velocity);
                float strength=bounded01(f32(f32(forward-1.0f)/19.0f));
                if(strength>0) {
                    if(!angle)return false;
                    float turns=angle(delta,fabsf(forward));if(!isfinite(turns))return false;
                    float degrees=f32(turns*360.0f);
                    float steer_angle=fabsf(f32(p->steering*degrees));
                    float angular=bounded01(f32(f32(steer_angle-1.0f)/15.0f));
                    strength=f32(strength*angular);
                    if(strength>0) {
                        float reduced=f32(1.0f-strength),half_reduced=f32(1.0f-f32(strength*0.5f));
                        if(delta>0) {
                            drive_multiplier[0]=half_reduced;drive_multiplier[1]=reduced;
                            grip_multiplier[0]=f32(strength+1.0f);
                        } else {
                            drive_multiplier[0]=reduced;drive_multiplier[1]=half_reduced;
                            grip_multiplier[1]=f32(strength+1.0f);
                        }
                    }
                }
            }
        }
        MwPhysicsTransmissionDifferentialInput differential={
            .angular_speed={wheels[first].angular_speed,wheels[first+1].angular_speed},
            .contacted={wheels[first].spring_compression>0,wheels[first+1].spring_compression>0},
            .base_ratio=base,.locking=p->differential[a]};float share[2];
        if(!mw_physics_transmission_differential(&differential,override,share))return false;
        for(unsigned j=0;j<2;++j) {
            MwPhysicsTransmissionWheel *w=result+first+j;
            if(w->spring_compression>0) {
                float applied=f32(f32(torque*share[j])*drive_multiplier[j]);
                if(!w->locked)w->drive_torque=f32(w->drive_torque+applied);
                w->grip_factor=f32(w->grip_factor*grip_multiplier[j]);
            }
        }
    }
    memcpy(wheels,result,sizeof result);return true;
}
