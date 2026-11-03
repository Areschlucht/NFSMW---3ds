#include "mw_physics_contact.h"
#include "mw_gekko_math.h"
#include "mw_physics_friction.h"
#include <math.h>
#include <stdint.h>
#include <string.h>
static float f32(float v){volatile float f=v;return f;}
static const uint16_t angle_table[257]={
#include "mw_physics_atan_table.inc"
};
static unsigned angle_lookup(float smaller,float larger)
{
    unsigned fixed=(unsigned)f32(f32(smaller/larger)*65536.0f);
    unsigned index=fixed>>8,fraction=fixed&255;
    return angle_table[index]+(((int)angle_table[index+1]-angle_table[index])*(int)fraction>>8);
}
float mw_physics_contact_angle_turns(float lateral,float longitudinal)
{
    float x=fabsf(longitudinal)>0.000001f?longitudinal:0;
    float y=fabsf(lateral)>0.000001f?lateral:0;
    unsigned quadrant=0,angle;
    if(x<0){quadrant=1;x=-x;}
    if(y<0){quadrant^=3;y=-y;}
    if(x>y)angle=angle_lookup(y,x);
    else if(y>x)angle=(16384-angle_lookup(x,y))&65535;
    else angle=y==0?0:8192;
    if(quadrant==3)angle=(-angle)&65535;
    else if(quadrant==1)angle=(-32768-(int)angle)&65535;
    else if(quadrant==2)angle=(angle-32768)&65535;
    int signed_angle=angle>=32768?(int)angle-65536:(int)angle;
    return f32((float)signed_angle*(1.0f/65536.0f));
}
static float square_root(const MwPhysicsContactMath *m,float v)
{return m&&m->sqrt_raw?m->sqrt_raw(v,m->context):mw_gekko_sqrt_newton1(v);}
static float angle(const MwPhysicsContactMath *m,float lateral,float longitudinal)
{return m&&m->angle_turns?m->angle_turns(lateral,longitudinal,m->context):mw_physics_contact_angle_turns(lateral,longitudinal);}
static float sine(const MwPhysicsContactMath *m,float radians)
{return m&&m->sine?m->sine(radians,m->context):sinf(radians);}
void mw_physics_contact_wheel_init(MwPhysicsContactWheel *s,unsigned index,float radius)
{
    if(!s)return;
    memset(s,0,sizeof(*s));s->wheel_index=index;s->brake.axle=index>>1;
    s->brake.radius_m=radius>0.1f?radius:0.1f;s->brake.direction=1;
    s->lateral_grip_factor=s->grip_factor=s->traction_factor=1;
    s->lateral_scale=s->longitudinal_scale=s->curve_scale=s->combined_factor=1;
    s->slip_budget=0.5f;
}
void mw_physics_contact_prepare(MwPhysicsContactWheel *s,float budget,float curve,float grip,float coupling)
{
    if(!s)return;
    s->brake.drive_torque=s->brake.accumulated_brake_torque=0;
    s->lateral_force=s->longitudinal_force=0;s->lateral_scale=s->longitudinal_scale=1;
    s->slip_budget=budget;s->curve_scale=curve;s->grip_factor=grip;s->combined_factor=1;s->coupling_13c=coupling;
}
static float speed_factor(const MwPhysicsContactWheel *s,float argument)
{
    if(s->brake.locked||s->brake.angular_speed<0||s->wheel_index<=1)return 1;
    float position=f32(f32(argument-f32(30.0f*0.44703f))/f32(20.0f*0.44703f));
    if(position>1)position=1;
    if(position<0)position=0;
    return fmaf(position,f32(1.0f-0.85f),0.85f);
}
bool mw_physics_contact_step(MwPhysicsContactWheel *s,const MwPhysicsContactInput *in,const MwPhysicsContactParameters *p,const MwPhysicsContactMath *math)
{
    if(!s||!in||!p||!isfinite(in->lateral_velocity)||!isfinite(in->longitudinal_velocity)||!isfinite(in->vehicle_speed_mps)||!isfinite(in->normal_force)||s->brake.axle>1||s->wheel_index>3||!(s->brake.radius_m>0)||!(in->seconds>0)||!isfinite(in->seconds))return false;
    MwPhysicsWheelBrakeState *b=&s->brake;unsigned axle=b->axle;
    float lateral=in->lateral_velocity,longitudinal=in->longitudinal_velocity,dt=in->seconds;
    float brake_torque=f32(f32(p->brakes.normal_raw[axle]*1.3558f)*p->calibration.normal_scale);
    float hand_torque=f32(f32(p->brakes.handbrake_raw*1.3558f)*p->calibration.handbrake_scale);
    if(s->normal_load<=0&&!b->locked)b->angular_speed=f32(longitudinal/b->radius_m);
    float linear_acceleration=f32(f32(longitudinal-s->previous_longitudinal_velocity)/dt);
    s->previous_longitudinal_velocity=longitudinal;
    s->normal_load=in->normal_force>0?in->normal_force:0;
    s->last_lateral_velocity=lateral;
    float normal_moment=f32(b->normal_input*brake_torque),hand_moment=f32(b->handbrake_input*hand_torque);
    float absolute_speed=fabsf(longitudinal);
    if(absolute_speed<1){
        float normal=f32(f32(f32(-b->normal_input*in->normal_force)*longitudinal)/b->radius_m);
        float hand=f32(f32(f32(-b->handbrake_input*in->normal_force)*longitudinal)/b->radius_m);
        float hand_drive=f32(-b->drive_torque*b->handbrake_input);
        if(!b->locked){
            b->drive_torque=f32(b->drive_torque+hand_drive);
            b->accumulated_brake_torque=f32(f32(b->accumulated_brake_torque+normal)+hand);
        }
    }else{
        if(b->angular_speed>0)normal_moment=-normal_moment;
        if(!b->locked)b->accumulated_brake_torque=f32(b->accumulated_brake_torque+normal_moment);
        if(b->angular_speed>0)hand_moment=-hand_moment;
        if(!b->locked)b->accumulated_brake_torque=f32(b->accumulated_brake_torque+hand_moment);
    }
    s->slip_angle_turns=angle(math,lateral,absolute_speed);
    float lateral_squared=f32(lateral*lateral);
    float slip=fmaf(b->angular_speed,b->radius_m,-longitudinal);s->longitudinal_slip=slip;
    float slip_magnitude=square_root(math,fmaf(slip,slip,lateral_squared));
    float speed_grip=speed_factor(s,in->vehicle_speed_mps),dynamic_factor=1,dynamic_multiplier=0;
    if(slip_magnitude>0.000001f&&(lateral!=0||longitudinal!=0)){
        dynamic_factor=f32(f32(p->dynamic_grip[axle]*s->grip_factor)*speed_grip);
        dynamic_multiplier=f32(f32(s->normal_load*dynamic_factor)/slip_magnitude);
        float velocity_magnitude=square_root(math,fmaf(longitudinal,longitudinal,lateral_squared));
        float lock_argument=f32(absolute_speed*f32(f32(s->normal_load*dynamic_factor)/velocity_magnitude));
        mw_physics_brake_lock_raw(&p->brakes,&p->calibration,b,lock_argument);
    }
    if(s->traction_factor<1||b->locked){
        s->lateral_force=f32(-dynamic_multiplier*lateral);
        s->longitudinal_force=f32(dynamic_multiplier*slip);
        if(in->vehicle_speed_mps<0.44703f&&dynamic_factor>0.1f){
            s->longitudinal_force=f32(s->longitudinal_force/dynamic_factor);
            s->lateral_force=f32(s->lateral_force/dynamic_factor);
        }
        float torque_force=f32(f32(b->drive_torque+b->accumulated_brake_torque)/b->radius_m);
        if(f32(s->longitudinal_force*torque_force)>0){
            if(s->longitudinal_force<=0){if(s->longitudinal_force<torque_force)s->longitudinal_force=torque_force;}
            else if(s->longitudinal_force>torque_force)s->longitudinal_force=torque_force;
        }
    }else{
        b->locked=0;s->longitudinal_force=f32(f32(b->drive_torque+b->accumulated_brake_torque)/b->radius_m);
        s->lateral_force=mw_physics_lateral_curve_raw(p->lateral_curves?p->lateral_curves:&mw_physics_original_lateral_curves,s->normal_load,fabsf(s->slip_angle_turns),p->grip_scale[axle],s->curve_scale);
        if(lateral>0)s->lateral_force=-s->lateral_force;
    }
    s->lateral_force=f32(s->lateral_force*s->lateral_grip_factor);
    if(s->traction_factor>=1&&!b->locked){
        float correction=fmaf(b->angular_acceleration,b->radius_m,-linear_acceleration);
        correction=f32(f32(correction*p->calibration.inertia)/b->radius_m);
        s->longitudinal_force=f32(s->longitudinal_force+correction);
    }
    int torque_boost=0;
    if(f32(f32(b->drive_torque+b->accumulated_brake_torque)*longitudinal)>0&&!b->locked){
        torque_boost=1;s->longitudinal_force=f32(s->longitudinal_force*1.5f);
    }
    s->longitudinal_force=f32(s->longitudinal_force*s->longitudinal_scale);
    s->lateral_force=f32(s->lateral_force*s->lateral_scale);
    float magnitude=square_root(math,fmaf(s->lateral_force,s->lateral_force,f32(s->longitudinal_force*s->longitudinal_force)));
    MwPhysicsFrictionState friction={.longitudinal_force=s->longitudinal_force,.lateral_force=s->lateral_force,.normal_load=s->normal_load,.static_grip=p->static_grip[axle],.grip_factor=s->grip_factor,.combined_factor=s->combined_factor,.speed_factor=speed_grip,.slip_budget=s->slip_budget,.slip_speed=slip,.undo_torque_boost=torque_boost};
    mw_physics_friction_limit_given_magnitude(&friction,magnitude);
    s->lateral_force=f32(friction.lateral_force*p->surface_lateral_grip);
    s->longitudinal_force=f32(friction.longitudinal_force*p->surface_drive_grip);s->traction_factor=friction.traction_factor;
    if(longitudinal>1){
        float coupling=f32(sine(math,f32(s->slip_angle_turns*6.2831854820251465f))*s->lateral_force);
        coupling=f32(f32(coupling*s->coupling_13c)/p->grip_scale[axle]);
        s->longitudinal_force=f32(s->longitudinal_force-coupling);
    }else{
        float factor=fabsf(lateral);if(factor>1)factor=1;
        s->lateral_force=f32(s->lateral_force*factor);
    }
    if(b->locked)b->angular_acceleration=0;
    else{
        if(s->traction_factor<1){
            float radius_dt=f32(b->radius_m*dt);
            float torque=f32(f32(b->drive_torque+b->accumulated_brake_torque)-f32(s->longitudinal_force*b->radius_m));
            torque=f32(f32(torque+s->residual_torque)*0.5f);s->residual_torque=torque;
            float damping=f32(b->angular_speed*f32(2.0f*p->surface_rolling_resistance));
            float inertia_term=f32(f32(torque-damping)/p->calibration.inertia);
            float slip_term=f32(f32(s->traction_factor*s->longitudinal_slip)/radius_dt);
            b->angular_acceleration=f32(inertia_term-slip_term);
        }
        float acceleration=f32(linear_acceleration/b->radius_m);
        b->angular_acceleration=fmaf(f32(acceleration-b->angular_acceleration),s->traction_factor,b->angular_acceleration);
    }
    b->angular_speed=fmaf(b->angular_acceleration,dt,b->angular_speed);
    mw_physics_wheel_spin_transition(b);
    return true;
}

bool mw_physics_contact_free_step(MwPhysicsContactWheel *s,const MwPhysicsContactParameters *p,float dt)
{
    if(!s||!p||s->brake.axle>1||!(dt>0)||!isfinite(dt))return false;
    s->normal_load=s->longitudinal_slip=s->traction_factor=s->slip_angle_turns=0;
    mw_physics_free_wheel_brake_step(&p->brakes,&p->calibration,&s->brake,dt);
    s->lateral_force=s->longitudinal_force=0;
    return true;
}
