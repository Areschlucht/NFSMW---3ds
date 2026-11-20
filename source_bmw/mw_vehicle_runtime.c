#include "mw_vehicle_runtime.h"
#include "mw_gekko_math.h"
#include "mw_original_power.h"
#include <math.h>
#include <string.h>
static float f32(float x){volatile float r=x;return r;}
typedef struct {const MwPhysicsSuspensionMath *source;bool failed;} PowerContext;
static float source_power(float base,float exponent,void *context){PowerContext *c=context;float v=c->source&&c->source->power?c->source->power(base,exponent,c->source->context):mw_original_power_callback_float(base,exponent,NULL);if(!isfinite(v))c->failed=true;return v;}
static float source_sine(float x,void *context){(void)context;return mw_player_source_sine(x);}
static float clamp(float x,float lo,float hi){return x<lo?lo:x>hi?hi:x;}
static uint32_t word(const unsigned char *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static float real(const unsigned char *p){uint32_t b=word(p);float x;memcpy(&x,&b,4);return x;}
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned j=0;j<8;j++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
static bool bind(MwVehicleRuntimeParams *p){
    MwPhysicsTransmissionEngineParams *e=&p->powertrain.mechanical;
    e->torque.torque=p->torque;e->engine_braking.torque=p->braking;e->ratios=p->ratios;e->gear_efficiency=p->efficiency;e->shift_tables=&p->shifts;
    return mw_physics_transmission_shift_tables(&e->torque,&p->powertrain.induction,p->ratios,e->gear_count,&p->shifts)&&mw_physics_transmission_peak_torque(&e->torque,&p->powertrain.induction,&e->peak_raw_torque,&e->peak_torque_rpm);
}
bool mw_vehicle_runtime_params_open(MwVehicleRuntimeParams *out,const void *data,size_t size){
    if(!out||!data||size!=1084)return false;
    const unsigned char *p=data;
    uint32_t version=word(p+4);
    if(memcmp(p,"NVR1",4)||(version!=1&&version!=2)||word(p+8)!=size||word(p+12)!=crc(p+16,size-16)||word(p+20)!=620||word(p+24)!=684||word(p+28)!=812)return false;
    static const unsigned char bank[32]={0xda,0x02,0x35,0x3d,0xe7,0x0d,0xea,0x3a,0x8a,0x51,0xd6,0x23,0x1e,0x4e,0xfd,0xe1,0x5a,0xb8,0xc5,0xc7,0x2e,0xed,0x61,0x19,0xa4,0x9b,0xc9,0xda,0xd2,0x0b,0x77,0x0b};
    if(memcmp(p+32,bank,32)||memcmp(p+64,p+192,64)||memcmp(p+64,p+528,64))return false;
    MwVehicleRuntimeParams q={0};
    if(!mw_vehicle_dynamics_params_open(&q.wheels,p+128,336)||!mw_vehicle_mechanical_profile_open(&q.mechanical,p+464,156)||word(p+16)!=q.wheels.physical_key||q.mechanical.physical_key!=q.wheels.physical_key||q.mechanical.chassis_key!=q.wheels.chassis_key)return false;
    const unsigned char *b=p+620,*e=p+684,*a=p+812;int16_t extents[3];float tensor[3];
    for(unsigned i=0;i<3;i++){extents[i]=(int16_t)((unsigned)b[i*2]|(unsigned)b[i*2+1]<<8);tensor[i]=real(b+12+i*4);q.local_cg[i]=real(b+36+i*4);}
    if(b[6]||b[7]||word(b+28)!=1)return false;
    for(unsigned i=52;i<64;i++)if(b[i])return false;
    if(!mw_original_rigid_body_parameters(real(b+8),extents,tensor,&q.body)||q.body.mass!=q.wheels.mass)return false;
    q.gravity=real(b+24);q.yaw_speed=real(b+32);q.yaw_count=word(b+48);q.body_bound=true;
    if(!isfinite(q.gravity)||!isfinite(q.yaw_speed)||!q.yaw_count||q.yaw_count>16)return false;
    q.engine_key=word(e);q.transmission_key=word(e+4);q.induction_key=word(e+8);q.nos_key=word(e+12);
    if(!q.engine_key||q.transmission_key!=q.wheels.transmission_key||!q.induction_key||!q.nos_key||(version==1&&word(e+36)))return false;
    if(version==1)for(unsigned i=120;i<128;i++)if(e[i])return false;
    unsigned nt=word(e+16),nb=word(e+20),ng=word(e+24),ne=word(e+28);
    if(nt<2||nt>16||!nb||nb>16||ng<3||ng>10||ne<ng||ne>10)return false;
    float *arrays[]={q.torque,q.braking,q.ratios,q.efficiency,q.yaw_samples};unsigned caps[]={16,16,10,10,16},counts[]={nt,nb,ng,ne,q.yaw_count};unsigned pos=0;
    for(unsigned k=0;k<5;k++)for(unsigned i=0;i<caps[k];i++,pos+=4){float v=real(a+pos);if(!isfinite(v)||(i>=counts[k]&&v!=0))return false;arrays[k][i]=v;}
    MwPhysicsTransmissionEngineParams *m=&q.powertrain.mechanical;
    m->torque=(MwPhysicsEngineCurve){q.torque,nt,real(e+40),real(e+44),real(e+48)};m->engine_braking=(MwPhysicsEngineCurve){q.braking,nb,real(e+40),real(e+44),real(e+48)};
    m->gear_count=ng;m->flywheel_mass=real(e+52);m->final_gear=real(e+56);m->torque_split=real(e+60);m->torque_converter=real(e+64);m->clutch_slip=real(e+68);
    q.powertrain.shift_speed=real(e+72);q.powertrain.speed_limiter_count=word(e+32);
    q.powertrain.nos=(MwPhysicsTransmissionNosParams){real(e+76),real(e+80),real(e+84),real(e+88),real(e+92),real(e+96),real(e+100)};
    q.powertrain.induction=(MwPhysicsTransmissionInduction){real(e+104),real(e+108),real(e+112),real(e+116)};
    if(version==2){
        q.induction_timing=(MwPhysicsTransmissionInductionTiming){.spool_up=real(e+120),.spool_down=real(e+124),.psi=real(e+36)};
        if(!isfinite(q.induction_timing.spool_up)||!isfinite(q.induction_timing.spool_down)||!isfinite(q.induction_timing.psi))return false;
    }else if(q.powertrain.induction.low_boost>0||q.powertrain.induction.high_boost>0)return false;
    for(unsigned i=40;i<120;i+=4)if(!isfinite(real(e+i)))return false;
    if(m->torque_split!=q.wheels.torque_split||!bind(&q))return false;
    *out=q;return bind(out);
}
bool mw_vehicle_runtime_init(MwVehicleRuntimeState *out,const MwVehicleRuntimeParams *p,const MwOriginalRigidBody *body,const MwPhysicsTransmissionEngineStepState *engine){
    if(!out||!p||!body||!engine||!p->body_bound||body->inverse_mass!=p->body.inverse_mass||memcmp(body->inertia,p->body.inertia,sizeof(body->inertia))||memcmp(body->local_cg,p->local_cg,sizeof(body->local_cg)))return false;
    MwVehicleRuntimeState s={.physical_key=p->wheels.physical_key,.body=*body,.engine=*engine};
    if(!mw_vehicle_dynamics_init(&s.wheels,&p->wheels)||!mw_player_steering_init(&s.steering))return false;
    s.story_engine.deadline=engine->mechanical.rev_modulation_deadline;
    s.assists.route.handbrake_history_1b8=1;s.assists.traction.scale=1;
    *out=s;return true;
}
typedef struct {const MwVehicleRuntimeParams *p;MwVehicleRuntimeState *s;MwVehicleRuntimeProduced *v;MwVehicleRuntimeOutput *o;const MwVehicleRuntimeHooks *h;} Bridge;
static bool mechanical(void *ctx,const MwVehicleDynamicsInput *in,MwPhysicsGroundWheel wheels[4]){
    Bridge *b=ctx;(void)in;(void)wheels;
    if(!mw_vehicle_mechanical(&b->p->mechanical.params,&b->v->mechanical,&b->o->mechanical,b->h->mechanical_math))return false;
    for(unsigned i=0;i<b->o->mechanical.count;i++){MwVehicleMechanicalForce *f=b->o->mechanical.forces+i;bool wake;
        float force[3]={f->force.x,f->force.y,f->force.z},point[3]={f->world_point.x,f->world_point.y,f->world_point.z};
        if(!mw_original_rigid_body_add_force(&b->s->body,force,point,&wake))return false;
        if(wake)b->o->wake_event=true;
        b->o->body_force_calls++;
    }return true;
}
static bool route(void *ctx,const MwVehicleDynamicsInput *in,MwPhysicsGroundWheel wheels[4]){
    Bridge *b=ctx;(void)in;
    if(!mw_player_steering_step(&b->s->steering,&b->v->steering,&b->o->steering_turns))return false;
    bool directions_ok=b->h->steer_directions?b->h->steer_directions(b->h->context,b->v->wheels.body_matrix,b->o->steering_turns,b->p->wheels.track_width[0],b->p->wheels.wheel_base,b->v->wheels.wheel_direction):mw_player_steer_directions(b->v->wheels.body_matrix,b->o->steering_turns,b->p->wheels.track_width[0],b->p->wheels.wheel_base,b->v->wheels.wheel_direction);
    if(!directions_ok)return false;
    MwPlayerWallSteeringInput wall={.steering=b->v->steering.raw_steering,.throttle=b->v->steering.throttle,.gear=b->s->engine.mechanical.gear_slot,.contact_count=b->s->previous_contact_count};
    memcpy(wall.body_matrix,b->v->wheels.body_matrix,sizeof(wall.body_matrix));wall.angular_velocity_world[0]=b->v->wheels.angular_velocity.x;wall.angular_velocity_world[1]=b->v->wheels.angular_velocity.y;wall.angular_velocity_world[2]=b->v->wheels.angular_velocity.z;
    MwPlayerWallSteeringOutput commands;if(!mw_player_wall_steering(&b->s->collision,&wall,&commands))return false;
    for(unsigned i=0;i<commands.count;i++)memcpy(b->s->body.angular_velocity,commands.angular_velocity_world[i],sizeof(b->s->body.angular_velocity));
    b->v->assists.averaged_steering=b->s->steering.input_average.average;
    if(!mw_player_input_route(&b->s->assists,&b->v->assists,wheels,&b->o->assists))return false;
    if(b->o->assists.torque_present){bool wake;if(!mw_original_rigid_body_add_torque(&b->s->body,b->o->assists.torque_world,&wake))return false;if(wake)b->o->wake_event=true;}
    return true;
}
static bool query(void *ctx,unsigned i,const MwPhysicsContactVector *p,const MwPhysicsContactVector *v,MwVehicleDynamicsQuery *q){Bridge *b=ctx;return b->h->query(b->h->context,i,p,v,q);}
static float local(const float *m,const float *v,unsigned axis){return fmaf(m[axis+2],v[2],f32(f32(m[axis]*v[0])+f32(m[axis+1]*v[1])));}
bool mw_vehicle_runtime_step(const MwVehicleRuntimeParams *p,const MwVehicleRuntimeInput *raw,MwVehicleRuntimeState *state,MwVehicleRuntimeOutput *out,const MwVehicleRuntimeHooks *h){
    if(!p||!raw||!state||!out||!h||!h->produce||!h->before_body_tick||!h->after_body_tick||!h->query||state->physical_key!=p->wheels.physical_key||!p->body_bound||!isfinite(raw->seconds)||raw->seconds<=0||!isfinite(raw->source_time)||!isfinite(raw->steering)||!isfinite(raw->throttle)||!isfinite(raw->brake)||!isfinite(raw->handbrake))return false;
    MwVehicleRuntimeState s=*state;MwVehicleRuntimeOutput o={0};MwVehicleRuntimeProduced v={0};
    /* Source SimStart integrates previous interval, then world collision phase.
       Producer is called after that phase, as source Physics task is later. */
    if(!h->before_body_tick(h->context,&s.body,raw->seconds))return false;
    MwOriginalRigidBody previous=s.body;
    /* Original OnBeginFrame80234A44 skips DoIntegration for state2. The
       integrator's own nonzero-state branch clears velocity, so calling it
       unconditionally changes an immobile body's retained source state. */
    if(s.body.status!=2&&!mw_original_rigid_body_integrate(&s.body,raw->seconds))return false;
    if(!h->after_body_tick(h->context,&previous,&s.body,raw->seconds))return false;
    if(!h->produce(h->context,p,&s,raw,&v)||(v.present&MW_RUNTIME_REQUIRED_PRODUCERS)!=MW_RUNTIME_REQUIRED_PRODUCERS||!v.body_before_engine||!v.engine_before_suspension)return false;
    if(v.collision_event_count&&!v.collision_events)return false;
    for(size_t event_index=0;event_index<v.collision_event_count;event_index++)if(!mw_player_collision_event(&s.collision,v.collision_events+event_index))return false;
    /* Manual request acceptance still requires its actual original policy. */
    if(raw->gear_requested)return false;
    float throttle=clamp(raw->throttle,0,1),brake=clamp(raw->brake,0,1),handbrake=clamp(raw->handbrake,0,1);
    float *m=v.wheels.body_matrix;memcpy(m,s.body.orientation,64);for(unsigned i=0;i<3;i++)m[12+i]=s.body.position[i];
    float speed=mw_gekko_sqrt_newton1(fmaf(s.body.velocity[2],s.body.velocity[2],f32(f32(s.body.velocity[0]*s.body.velocity[0])+f32(s.body.velocity[1]*s.body.velocity[1]))));
    float forward=local(m,s.body.velocity,8),lateral=local(m,s.body.velocity,0);
    unsigned contacts=s.previous_contact_count;if(contacts>4)return false;MwPhysicsTransmissionSpeedWheel ew[4];
    for(unsigned i=0;i<4;i++){MwPhysicsContactWheel *w=&s.wheels.wheels[i].tire;ew[i]=(MwPhysicsTransmissionSpeedWheel){w->brake.angular_speed,s.wheels.wheels[i].compression,w->traction_factor,w->previous_longitudinal_velocity,w->brake.radius_m,w->brake.locked};v.engine.external.longitudinal_slip[i]=w->longitudinal_slip;}
    v.engine.raw_throttle=throttle;v.engine.external.seconds=raw->seconds;v.engine.external.contact_count=contacts;v.engine.nos.requested=raw->nos_requested;
    MwPhysicsTransmissionInductionTiming induction_timing=p->induction_timing;
    induction_timing.tuning_present=v.induction_tuning_present;induction_timing.tuning_18=v.induction_tuning_18;
    if(!mw_physics_transmission_engine_step_complete(&p->powertrain,&v.engine,&s.engine,ew,&o.gear_event,&s.story_engine,raw->source_time,mw_player_source_sine,&o.engine_blown_event,&induction_timing))return false;
    for(unsigned i=0;i<4;i++)s.wheels.wheels[i].tire.brake.angular_speed=ew[i].angular_speed;
    if(!mw_player_collision_begin(&s.collision,raw->seconds))return false;
    v.steering.fade_1ac=s.collision.collision_timer;
    v.steering.raw_steering=clamp(raw->steering,-1,1);v.steering.forward_speed=forward;v.steering.throttle=throttle;v.steering.brake=brake;v.steering.handbrake=handbrake;v.steering.seconds=raw->seconds;v.steering.time=raw->source_time;v.steering.tire_steering=p->wheels.steering;
    for(unsigned i=0;i<2;i++)v.steering.rear_slip_angle_turns[i]=s.wheels.wheels[i+2].tire.slip_angle_turns;
    v.wheels.linear_velocity=(MwPhysicsContactVector){s.body.velocity[0],s.body.velocity[1],s.body.velocity[2]};v.wheels.angular_velocity=(MwPhysicsContactVector){s.body.angular_velocity[0],s.body.angular_velocity[1],s.body.angular_velocity[2]};
    MwPhysicsContactVector cg={s.body.local_cg[0],s.body.local_cg[1],s.body.local_cg[2]};mw_physics_contact_rotate_vector(m,&cg,&v.wheels.world_cg_offset);
    v.wheels.body_half_extent_y=p->body.halfextent[1];v.wheels.seconds=raw->seconds;v.wheels.speed_mps=speed;
    v.wheels.scales.gear_slot=s.engine.mechanical.gear_slot;
    v.wheels.distribution.engine_output_torque=s.engine.mechanical.output_torque;v.wheels.distribution.body_local_lateral_velocity=lateral;v.wheels.distribution.body_local_forward_velocity=forward;v.wheels.distribution.steering=v.steering.raw_steering;
    memcpy(v.mechanical.body_matrix,m,64);v.mechanical.world_velocity=v.wheels.linear_velocity;v.mechanical.local_cg=cg;v.mechanical.speed=speed;v.mechanical.throttle=throttle;v.mechanical.contact_fraction=f32((float)contacts*.25f);
    MwPhysicsContactVector mounts[4];mw_physics_contact_mounts(&p->wheels.dimensions,p->wheels.track_width,p->wheels.front_axle,p->wheels.wheel_base,p->body.halfextent[1],mounts);v.mechanical.front_mount_z=mounts[0].z;v.mechanical.rear_mount_z=mounts[2].z;
    MwPlayerAssistInput *a=&v.assists;MwPlayerRouteInput *r=&a->routing;
    r->forward_speed=forward;r->slip_angle_9c=forward<1?0:mw_physics_contact_angle_turns(lateral,forward);r->throttle=throttle;r->brake=brake;r->handbrake=handbrake;r->seconds=raw->seconds;r->steering=v.steering.raw_steering;r->body_24=m[9];r->source_speed_bc=speed;r->source_e4_70=p->wheels.torque_split;r->mode_cc=s.engine.mechanical.gear_slot;r->grip_d0=s.engine.scale_100;
    a->yaw_samples=p->yaw_samples;a->yaw_count=p->yaw_count;a->local_angular_y=local(m,s.body.angular_velocity,4);a->source_a4=s.body.inertia[1];a->contact_count=contacts;for(unsigned i=0;i<3;i++)a->body_up[i]=m[4+i];
    PowerContext power_context={h->suspension_math,false};MwPhysicsSuspensionMath suspension_math={source_power,&power_context};
    MwPhysicsContactMath contact_math={.sine=source_sine};
    Bridge bridge={p,&s,&v,&o,h};MwVehicleDynamicsHooks dh={mechanical,route,query,&bridge,&suspension_math,h->contact_math?h->contact_math:&contact_math};
    if(!mw_vehicle_dynamics_step(&p->wheels,&v.wheels,&s.wheels,&o.contacts,&dh)||power_context.failed)return false;
    MwVehicleRuntimeChassisInput ci={.yaw_speed=p->yaw_speed,.driver_style=v.assists.routing.mode_c8,.previous_contact_count=s.previous_contact_count};
    memcpy(ci.body_matrix,m,sizeof(ci.body_matrix));float common_angular[3]={v.wheels.angular_velocity.x,v.wheels.angular_velocity.y,v.wheels.angular_velocity.z};for(unsigned i=0;i<3;i++)ci.local_angular_velocity[i]=local(m,common_angular,i*4);
    MwVehicleRuntimeChassisOutput co;if(!mw_vehicle_runtime_chassis_commands(&ci,&o.contacts,&co))return false;
    if(co.wrench_present){bool wake;if(!mw_original_rigid_body_add_wrench(&s.body,co.force,co.torque,&wake))return false;if(wake)o.wake_event=true;o.body_force_calls++;}
    if(co.raise_present){if(!mw_original_rigid_body_raise_position(&s.body,co.raise_y))return false;for(unsigned i=0;i<4;i++)o.contacts.application_point[i].y=f32(o.contacts.application_point[i].y+co.raise_y);}
    if(co.angular_velocity_present)memcpy(s.body.angular_velocity,co.angular_velocity,sizeof(co.angular_velocity));
    s.previous_contact_count=co.contact_count;
    mw_player_collision_end(&s.collision);
    s.seconds_elapsed=f32(s.seconds_elapsed+raw->seconds);if(!isfinite(s.seconds_elapsed))return false;
    *state=s;*out=o;return true;
}

bool mw_vehicle_runtime_chassis_commands(const MwVehicleRuntimeChassisInput *in,const MwVehicleDynamicsOutput *w,MwVehicleRuntimeChassisOutput *out){
    if(!in||!w||!out||!isfinite(in->yaw_speed)||in->previous_contact_count>4)return false;
    for(unsigned i=0;i<16;i++)if(!isfinite(in->body_matrix[i]))return false;
    for(unsigned i=0;i<3;i++)if(!isfinite(in->local_angular_velocity[i]))return false;
    MwVehicleRuntimeChassisOutput o={0};
    for(unsigned i=0;i<4;i++){
        const MwPhysicsGroundOutput *g=&w->ground[i];
        if(!isfinite(g->suspension.penetration_excess)||g->suspension.penetration_excess<0)return false;
        if(g->suspension.has_contact)o.contact_count++;
        if(g->suspension.penetration_excess>o.raise_y)o.raise_y=g->suspension.penetration_excess;
    }
    o.wrench_present=o.contact_count!=0;o.raise_present=o.raise_y>0;
    if(o.wrench_present){
        for(unsigned i=0;i<4;i++){
            float f[3]={w->ground[i].world_force.x,w->ground[i].world_force.y,w->ground[i].world_force.z};float t[3]={w->world_moment[i].x,w->world_moment[i].y,w->world_moment[i].z};
            for(unsigned j=0;j<3;j++){o.force[j]=f32(o.force[j]+f[j]);o.torque[j]=f32(o.torque[j]+t[j]);}
        }
        const float *up=in->body_matrix+4;
        float projection=fmaf(up[2],o.torque[2],f32(f32(up[0]*o.torque[0])+f32(up[1]*o.torque[1])));
        float scaled=f32(projection*in->yaw_speed);if(in->driver_style==1)scaled=f32(scaled*1.600000023841858f);
        float difference=f32(scaled-projection);
        for(unsigned i=0;i<3;i++)o.torque[i]=f32(f32(up[i]*difference)+o.torque[i]);
    }
    if(o.contact_count&&in->previous_contact_count==0){
        MwPhysicsContactVector v={in->local_angular_velocity[0],f32(in->local_angular_velocity[1]*.5f),f32(in->local_angular_velocity[2]*.5f)},r;
        mw_physics_contact_rotate_vector(in->body_matrix,&v,&r);o.angular_velocity[0]=r.x;o.angular_velocity[1]=r.y;o.angular_velocity[2]=r.z;o.angular_velocity_present=true;
    }
    for(unsigned i=0;i<3;i++)if(!isfinite(o.force[i])||!isfinite(o.torque[i])||!isfinite(o.angular_velocity[i]))return false;
    *out=o;return true;
}
