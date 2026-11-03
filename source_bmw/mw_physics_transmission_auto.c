#include "mw_physics_transmission_auto.h"
#include <math.h>
static float f32(float v){volatile float r=v;return r;}
bool mw_physics_transmission_automatic_step(const MwPhysicsTransmissionAutomaticParams *p,
    const MwPhysicsTransmissionAutomaticInput *in,MwPhysicsTransmissionAutomaticState *state,
    MwPhysicsTransmissionGearEvent *event)
{
    if(!p||!in||!state||!event||!p->tables||!p->ratios||p->count<3||
       p->count>MW_PHYSICS_TRANSMISSION_MAX_GEARS||p->tables->count!=p->count||
       state->shift.gear_slot>=p->count||state->shift.clutch_state>2||
       !isfinite(in->seconds)||in->seconds<0||!isfinite(in->raw_throttle)||
       !isfinite(in->applied_throttle)||!isfinite(in->shaft_omega)||
       !isfinite(state->cooldown)||!isfinite(state->shift.shift_delay)||
       !isfinite(p->shift_speed)||!isfinite(p->idle_rpm))return false;
    for(size_t i=0;i<p->count;++i)if(!isfinite(p->ratios[i]))return false;
    for(unsigned i=0;i<4;++i)if(!isfinite(in->longitudinal_slip[i]))return false;
    MwPhysicsTransmissionAutomaticState s=*state;MwPhysicsTransmissionGearEvent e={0};
    unsigned gear=s.shift.gear_slot;
    if(in->input_present&&in->automatic_enabled&&gear!=0&&s.shift.shift_delay<=0&&
       !in->vehicle_gate_48&&s.cooldown<=0) {
        if(gear==1)s.shift.gear_slot=2;
        else {
            int requested=-1;
            if(s.request==1) {
                unsigned candidate=gear-1;
                float base=f32(in->shaft_omega*9.549296379089355f);
                while(candidate>2) {
                    float ratio=0;
                    if(p->ratios[candidate]>0 && p->ratios[gear]>0.0000009999999974752427f)
                        ratio=f32(p->ratios[candidate]/p->ratios[gear]);
                    float predicted=f32(base*ratio);
                    if(mw_physics_transmission_shift_request(p->tables,p->ratios,p->count,
                        candidate,predicted,in->applied_throttle,p->idle_rpm)!=1)break;
                    --candidate;
                }
                requested=(int)candidate;
            } else if(s.request==2||s.request==4||s.request==5) {
                bool ready=true;
                for(unsigned i=0;i<4;++i)if(!in->contacted[i]||!(in->longitudinal_slip[i]<4))ready=false;
                if(ready)requested=(int)gear+1;
            }
            if(requested>=0&&mw_physics_transmission_commit_gear(&s.shift,requested,
                p->ratios,p->count,p->shift_speed)) {
                s.committed=1;s.request=0;e=(MwPhysicsTransmissionGearEvent){1,gear,(unsigned)requested,1};
            }
        }
    }
    if(s.shift.shift_delay>0) {
        s.shift.shift_delay=f32(s.shift.shift_delay-in->seconds);
        if(s.shift.shift_delay<=0)s.shift.shift_delay=0;
    }
    if(s.cooldown>0&&s.request!=0) {
        if(in->input_present) {
            s.cooldown=f32(s.cooldown-f32(in->seconds*f32(2-in->raw_throttle)));
            if(s.cooldown<0)s.cooldown=0;
        } else s.cooldown=0;
    }
    *state=s;*event=e;return true;
}
