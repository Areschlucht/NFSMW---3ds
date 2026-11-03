#include "mw_physics_transmission.h"
#include <math.h>
static float f32(float value){volatile float rounded=value;return rounded;}
float mw_physics_transmission_output_torque_nm(const MwPhysicsEngineCurve *curve,
    float rpm,float boost,float scale,unsigned mode)
{
    if(!isfinite(boost)||!isfinite(scale))return NAN;
    float result=f32(mw_physics_engine_curve_raw(curve,rpm)*1.3558000326156616f);
    result=f32(result*f32(boost+1.0f));
    if(mode!=6)result=f32(result*scale);
    return result;
}
float mw_physics_transmission_engine_braking(const MwPhysicsEngineCurve *curve,
    float torque,float rpm)
{
    if(!curve||!curve->count||!curve->torque||!isfinite(torque)||!isfinite(rpm))return NAN;
    float factor;
    if(curve->count==1){factor=curve->torque[0];if(!isfinite(factor))return NAN;}
    else {
        factor=mw_physics_engine_curve_raw(curve,rpm);
        if(!isfinite(factor))return NAN;
        if(factor>1.0f)factor=1.0f;
        if(factor<0.0f)factor=0.0f;
    }
    return f32(-torque*factor);
}

float mw_physics_transmission_reported_rpm(unsigned mode,unsigned gear,
    float seconds,float previous,float target,float inertia)
{
    if(!isfinite(seconds)||seconds<0||!isfinite(previous)||!isfinite(target)||
       !isfinite(inertia)||inertia<=0)return NAN;
    float rate=((mode && gear>2)||gear==1)?15.0f:2.5f;
    rate=f32(f32(-rate*1000.0f)/inertia);
    if(seconds>0.0f && f32(f32(target-previous)/seconds)<rate) {
        float limited=fmaf(rate,seconds,previous);
        if(limited>target)target=limited;
    }
    return fmaf(target,0.550000011920929f,f32(previous*0.44999998807907104f));
}

bool mw_physics_transmission_commit_gear(MwPhysicsTransmissionShiftState *state,
    int requested,const float *ratios,size_t count,float shift_speed)
{
    if(!state||!ratios||!count||count>65535||state->gear_slot>=count||requested<0||
       (size_t)requested>=count||(unsigned)requested==state->gear_slot||
       !isfinite(shift_speed)||!isfinite(ratios[requested]))return false;
    float delay=f32(shift_speed*ratios[requested]);
    if((unsigned)requested<state->gear_slot)delay=f32(delay*0.25f);
    state->shift_delay=delay;state->gear_slot=(unsigned)requested;
    if(state->clutch_state==0)state->clutch_state=2;
    return true;
}

float mw_physics_transmission_inertia(float mass,unsigned gear)
{
    if(!isfinite(mass))return NAN;
    return f32(fmaf(mass,0.02500000037252903f,0.25f)*(gear!=1?1.0f:0.3499999940395355f));
}
bool mw_physics_transmission_clutch_core(const MwPhysicsTransmissionClutchInput *p,
    float maximum_difference,float coupling,MwPhysicsTransmissionClutchResult *out)
{
    if(!p||!out||p->clutch_state>2||!isfinite(p->engine_omega)||
       !isfinite(p->shaft_omega)||!isfinite(p->shaft_acceleration)||
       !isfinite(p->engine_inertia)||p->engine_inertia<=0||
       !isfinite(p->net_engine_torque)||!isfinite(p->driveline_ratio)||
       !isfinite(p->torque_split)||!isfinite(p->contact_fraction)||
       !isfinite(p->shift_coupling)||!isfinite(p->previous_slip_rpm)||
       !isfinite(maximum_difference)||maximum_difference<0||!isfinite(coupling))return false;
    float wheel=0,reaction=0,slip=p->previous_slip_rpm;
    if(p->gear_slot!=1) {
        if(p->clutch_state==0) {
            slip=0;wheel=p->net_engine_torque;
            reaction=f32(0.0f-f32(wheel*p->contact_fraction));
            float acceleration=f32(f32(p->net_engine_torque+reaction)/p->engine_inertia);
            float denominator=f32(1.0f/p->engine_inertia);
            float rear_fraction=f32(1.0f-p->torque_split),ratio=fabsf(p->driveline_ratio);
            if(p->torque_split>0) {
                float a=f32(f32(1.0f-rear_fraction)*0.10000000149011612f);
                a=f32(a*ratio);a=f32(a*ratio);
                denominator=fmaf(a,0.5f,denominator);
            }
            if(p->torque_split<1) {
                float a=f32(rear_fraction*0.10000000149011612f);
                a=f32(a*ratio);a=f32(a*ratio);
                denominator=fmaf(a,0.5f,denominator);
            }
            float correction=f32(f32(acceleration-p->shaft_acceleration)/denominator);
            wheel=f32(wheel+(correction<0?correction:0));
            reaction=f32(reaction-f32(correction*p->contact_fraction));
        } else if(p->clutch_state==1) {
            float difference=f32(p->engine_omega-p->shaft_omega);
            if(difference>maximum_difference)difference=maximum_difference;
            else if(difference< -maximum_difference)difference=-maximum_difference;
            slip=f32(f32(p->shaft_omega-p->engine_omega)*9.549296379089355f);
            float gain=coupling;
            if(p->previous_slip_rpm!=0 && f32(slip*p->previous_slip_rpm)<0 &&
               fabsf(slip)>2000.0f && fabsf(p->previous_slip_rpm)>2000.0f)gain=f32(gain*0.5f);
            wheel=f32(f32(difference*gain)*p->shift_coupling);
            reaction=f32(0.0f-f32(wheel*p->contact_fraction));
        } else slip=0;
    }
    *out=(MwPhysicsTransmissionClutchResult){wheel,reaction,slip,p->net_engine_torque<0};return true;
}

bool mw_physics_transmission_clutch_update(MwPhysicsTransmissionClutchState *state,
    unsigned gear,float seconds,float engine,float shaft,float throttle,float idle,float *coupling)
{
    if(!state||!coupling||state->mode>2||!isfinite(state->remaining_seconds)||
       !isfinite(state->duration_seconds)||!isfinite(seconds)||seconds<0||
       !isfinite(engine)||!isfinite(shaft)||!isfinite(throttle)||!isfinite(idle))return false;
    if(state->remaining_seconds>0) {
        state->remaining_seconds=f32(state->remaining_seconds-seconds);
        if(state->remaining_seconds<=0 && state->mode==1)state->mode=0;
    }
    float blend=1;
    if(state->mode==2)blend=0.25f;
    else if(state->mode==1) {
        float fraction=0;
        if(state->duration_seconds>0.0000009999999974752427f) {
            fraction=f32(state->remaining_seconds/state->duration_seconds);
            if(fraction>1)fraction=1;
            if(fraction<0)fraction=0;
        }
        blend=f32(1.0f-f32(fraction*0.75f));
    }
    bool disengage=gear==1;float duration=0.25f;
    if(gear==0||gear==2) {
        float rpm_offset=gear==0?2400.0f:800.0f;
        float idle_omega=f32(idle*0.10471976548433304f);
        float threshold=fmaf(rpm_offset,0.10471976548433304f,idle_omega);
        disengage=engine<=threshold && shaft<=threshold && throttle<0.10000000149011612f;
        duration=0.05000000074505806f;
    }
    if(disengage) {
        if(state->mode==0)state->mode=2;
    } else if(state->mode==2) {
        state->mode=1;state->remaining_seconds=duration;state->duration_seconds=duration;
    }
    *coupling=blend;return true;
}

bool mw_physics_transmission_differential(const MwPhysicsTransmissionDifferentialInput *p,
    bool override_open,float output[2])
{
    if(!p||!output||!isfinite(p->angular_speed[0])||!isfinite(p->angular_speed[1])||
       !isfinite(p->base_ratio)||!isfinite(p->locking))return false;
    float first=p->base_ratio,second=f32(1.0f-first);
    if(p->contacted[0]&&p->contacted[1]&&!override_open&&p->locking>0) {
        float rear=f32(1.0f-p->base_ratio);
        float a=f32(p->angular_speed[0]*rear),b=f32(p->angular_speed[1]*p->base_ratio);
        float sum=fabsf(f32(a+b));
        if(sum>0.000009999999747378752f) {
            float unlocked=f32(1.0f-p->locking);
            first=fmaf(unlocked,p->base_ratio,f32(f32(p->locking*fabsf(b))/sum));
            second=fmaf(unlocked,rear,f32(f32(p->locking*fabsf(a))/sum));
        }
        if(first>1)first=1;
        if(first<0)first=0;
        if(second>1)second=1;
        if(second<0)second=0;
    }
    output[0]=first;output[1]=second;return true;
}

float mw_physics_transmission_engine_wheel_omega(const MwPhysicsTransmissionSpeedWheel *p)
{
    if(!p||!isfinite(p->angular_speed)||!isfinite(p->spring_compression)||
       !isfinite(p->traction_factor)||!isfinite(p->previous_longitudinal_velocity))return NAN;
    if(p->locked)return 0;
    if(p->spring_compression>0 && p->traction_factor>=1) {
        if(!isfinite(p->radius_m)||p->radius_m<=0)return NAN;
        return f32(p->previous_longitudinal_velocity/p->radius_m);
    }
    return p->angular_speed;
}
float mw_physics_transmission_driven_omega(const MwPhysicsTransmissionSpeedWheel wheels[4],
    float split,unsigned gear,bool directional)
{
    if(!wheels||!isfinite(split))return NAN;
    float selected=0;
    for(unsigned axle=0;axle<2;++axle) {
        if((axle==0 && split<=0)||(axle==1 && split>=1))continue;
        float a=mw_physics_transmission_engine_wheel_omega(wheels+axle*2);
        float b=mw_physics_transmission_engine_wheel_omega(wheels+axle*2+1);
        if(!isfinite(a)||!isfinite(b))return NAN;
        float average=f32(f32(a+b)*0.5f);
        if(!directional) {
            if(fabsf(average)>fabsf(selected))selected=average;
        } else if(gear==0) {
            if(average<selected)selected=average;
        } else if(average>selected)selected=average;
    }
    return selected;
}


bool mw_physics_transmission_shaft_step(const MwPhysicsTransmissionShaftInput *p,
    MwPhysicsTransmissionShaftResult *out)
{
    if(!p||!out||p->clutch_state>2||!isfinite(p->seconds)||p->seconds<0||
       !isfinite(p->engine_omega)||!isfinite(p->engine_rpm)||
       !isfinite(p->net_engine_torque)||!isfinite(p->reaction_torque)||
       !isfinite(p->engine_inertia)||p->engine_inertia<=0||!isfinite(p->throttle)||
       !isfinite(p->clutch_slip)||!isfinite(p->idle_rpm)||!isfinite(p->optimal_rpm)||
       !isfinite(p->minimum_omega)||!isfinite(p->maximum_omega)||
       p->minimum_omega>p->maximum_omega)return false;
    float reaction=p->reaction_torque;
    if(p->gear_slot!=1 && p->gear_slot<=2 && p->throttle>0 &&
       p->clutch_state==0 && f32(reaction*p->net_engine_torque)<0) {
        float range=f32(p->optimal_rpm-p->idle_rpm),fraction=0;
        float attenuation=f32(p->clutch_slip*p->throttle);
        if(range>0.0000009999999974752427f) {
            fraction=f32(f32(p->engine_rpm-p->idle_rpm)/range);
            if(fraction>1)fraction=1;
            if(fraction<0)fraction=0;
        }
        float inner=f32(1.0f-f32(p->throttle*fraction));
        attenuation=f32(attenuation*inner);
        float factor=f32(1.0f-attenuation);
        reaction=f32(reaction*f32(factor*factor));
    }
    float acceleration=f32(f32(p->net_engine_torque+reaction)/p->engine_inertia);
    float omega=fmaf(acceleration,p->seconds,p->engine_omega);
    if(omega>p->maximum_omega)omega=p->maximum_omega;
    if(omega<p->minimum_omega)omega=p->minimum_omega;
    *out=(MwPhysicsTransmissionShaftResult){omega,acceleration,reaction};return true;
}


bool mw_physics_transmission_sync_wheels(MwPhysicsTransmissionSpeedWheel wheels[4],
    float split,unsigned gear,float target,float vehicle_speed)
{
    if(!wheels||!isfinite(split)||!isfinite(target)||!isfinite(vehicle_speed))return false;
    float driven=mw_physics_transmission_driven_omega(wheels,split,gear,false);
    if(!isfinite(driven))return false;
    float delta=f32(target-driven),updated[4];
    for(unsigned i=0;i<4;++i)updated[i]=wheels[i].angular_speed;
    bool slow=f32(vehicle_speed*2.236989974975586f)<40.0f;
    /* Original processes rear, then front; each uses its own prior state. */
    for(int axle=1;axle>=0;--axle) {
        if((axle==0&&split<=0)||(axle==1&&split>=1))continue;
        unsigned first=(unsigned)axle*2;
        float a=mw_physics_transmission_engine_wheel_omega(wheels+first);
        float b=mw_physics_transmission_engine_wheel_omega(wheels+first+1);
        if(!isfinite(a)||!isfinite(b))return false;
        if(slow || (wheels[first].spring_compression<=0 && wheels[first+1].spring_compression<=0))
            a=b=f32(f32(a+b)*0.5f);
        updated[first]=f32(a+delta);updated[first+1]=f32(b+delta);
    }
    for(unsigned i=0;i<4;++i)wheels[i].angular_speed=updated[i];
    return true;
}
bool mw_physics_transmission_cap_airborne_wheels(MwPhysicsTransmissionSpeedWheel wheels[4],
    float split,float limit)
{
    if(!wheels||!isfinite(split)||!isfinite(limit))return false;
    float updated[4];
    for(unsigned i=0;i<4;++i) {
        updated[i]=wheels[i].angular_speed;
        if(!isfinite(wheels[i].spring_compression))return false;
        if(wheels[i].spring_compression>0 || (i<2&&split<=0)||(i>=2&&split>=1))continue;
        float speed=mw_physics_transmission_engine_wheel_omega(wheels+i);
        if(!isfinite(speed))return false;
        if(f32(speed*limit)<0)speed=0;
        else if(speed>0 && speed>limit)speed=limit;
        else if(speed<0 && speed<limit)speed=limit;
        updated[i]=speed;
    }
    for(unsigned i=0;i<4;++i)wheels[i].angular_speed=updated[i];
    return true;
}
