#include "mw_physics_transmission_engine.h"
#include <math.h>
#include <string.h>
static float f32(float v){volatile float r=v;return r;}
static float fraction(float value,float minimum,float maximum)
{
    float range=f32(maximum-minimum),r=0;
    if(range>0.0000009999999974752427f)r=f32(f32(value-minimum)/range);
    if(r>1)r=1;
    if(r<0)r=0;
    return r;
}
static float launch_curve(float x)
{
    /* Original initialized8048A0EC, source8041F65C, count5 at80265EE0. */
    static const float xs[]={-10,-7.5f,-3.5f,-.30000001192092896f,-.05000000074505806f};
    static const float ys[]={1,.9599999785423279f,.925000011920929f,.875f,0};
    if(x<=xs[0])return ys[0];
    if(x>=xs[4])return ys[4];
    for(unsigned i=0;i<4;++i)if(x>=xs[i]&&x<xs[i+1]) {
        float f=f32(f32(x-xs[i])/f32(xs[i+1]-xs[i]));
        return fmaf(ys[i+1],f,f32(ys[i]*f32(1-f)));
    }
    return NAN;
}
static float driven_slip(const float slip[4],float split)
{
    float total=0;unsigned count=0;
    if(split<1){total=f32(slip[2]+slip[3]);count=2;}
    if(split>0){total=f32(total+f32(slip[0]+slip[1]));count+=2;}
    return f32(total/(float)count);
}
bool mw_physics_transmission_sabotage_stage(float *omega,MwStoryEngine *story,float clock,float (*sine)(float),bool *event)
{
    if(!omega||!story||!event||!isfinite(*omega)||!isfinite(story->deadline)||!isfinite(clock)||story->blown>1)return false;
    MwStoryEngine e=*story;float value=*omega;bool blew=false;
    if(e.deadline>0){
        float remaining=f32(e.deadline-clock);
        if(remaining>0){
            if(!sine)return false;
            float angle=f32(f32(remaining*12.0f)*6.2831854820251465f);
            float wave=sine(angle);if(!isfinite(wave))return false;
            value=fmaf(wave,f32(value*.5f),value);
        }else{e.deadline=0;if(!e.blown){e.blown=1;blew=true;}}
    }
    if(!isfinite(value))return false;
    *omega=value;*story=e;*event=blew;return true;
}
static bool mechanical_step(
    const MwPhysicsTransmissionEngineParams *p,const MwPhysicsTransmissionEngineInput *in,
    MwPhysicsTransmissionEngineState *state,MwPhysicsTransmissionSpeedWheel wheels[4],
    MwStoryEngine *story,float clock,float (*sine)(float),bool *blown_event)
{
    if(!p||!in||!state||!wheels||!p->ratios||!p->gear_efficiency||!p->shift_tables||
       p->gear_count<3||p->gear_count>MW_PHYSICS_TRANSMISSION_MAX_GEARS||
       state->gear_slot>=p->gear_count||state->clutch.mode>2||
       !isfinite(in->seconds)||in->seconds<=0||in->contact_count>4||
       !isfinite(state->rev_modulation_deadline)||(!story&&state->rev_modulation_deadline>0))return false;
    const float scalars[]={p->flywheel_mass,p->final_gear,p->torque_split,p->torque_converter,
        p->clutch_slip,p->peak_raw_torque,p->peak_torque_rpm,in->applied_throttle,in->boost_9c,
        in->scale_100,in->vehicle_scalar_58,in->vehicle_speed_128,in->boost_interface_scalar,
        state->shift_delay,state->engine_omega,state->shaft_omega,state->slip_rpm,state->reported_rpm};
    for(unsigned i=0;i<sizeof scalars/sizeof *scalars;++i)if(!isfinite(scalars[i]))return false;
    for(unsigned i=0;i<4;++i)if(!isfinite(in->longitudinal_slip[i]))return false;
    MwPhysicsTransmissionEngineState s=*state;MwPhysicsTransmissionSpeedWheel w[4];memcpy(w,wheels,sizeof w);
    unsigned gear=s.gear_slot;float throttle=in->applied_throttle;
    float minimum=f32(p->torque.idle_rpm*.10471976548433304f);
    float maximum=f32(p->torque.red_line_rpm*.10471976548433304f);
    float inertia=mw_physics_transmission_inertia(p->flywheel_mass,gear);
    float abs_driven=mw_physics_transmission_driven_omega(w,p->torque_split,gear,false);
    float directed=mw_physics_transmission_driven_omega(w,p->torque_split,gear,true);
    if(!isfinite(abs_driven)||!isfinite(directed)||!isfinite(inertia)||inertia<=0||maximum<=0)return false;
    float contact_fraction=f32((float)in->contact_count*.25f);
    if(contact_fraction<.25f)contact_fraction=.25f;
    float coupling;
    /* Engagement uses old engine/shaft state, and coupling precedes transition. */
    if(!mw_physics_transmission_clutch_update(&s.clutch,gear,in->seconds,
        s.engine_omega,s.shaft_omega,throttle,p->torque.idle_rpm,&coupling))return false;
    float sign=gear==0?-1.0f:1.0f;
    float ratio=f32(f32(p->ratios[gear]*p->final_gear)*sign);
    float rpm=f32(s.engine_omega*9.549296379089355f);
    if(p->torque_converter>0) {
        float scale=f32(f32(p->torque_converter*throttle)*f32(1-fraction(rpm,p->torque.idle_rpm,p->peak_torque_rpm)));
        if(s.shift_delay>0)scale=f32(scale*coupling);
        ratio=f32(ratio*f32(scale+1));
    }
    if(!isfinite(ratio)||(ratio==0&&gear!=1))return false;
    float torque=mw_physics_transmission_output_torque_nm(&p->torque,rpm,in->boost_9c,in->scale_100,in->vehicle_mode_b8);
    float braking=mw_physics_transmission_engine_braking(&p->engine_braking,torque,rpm);
    if(!in->vehicle_gate_48&&in->vehicle_scalar_58>0&&throttle>0) {
        throttle=1;braking=0;
        torque=f32(f32(p->peak_raw_torque*1.3558000326156616f)*in->scale_100);
    }
    float new_shaft=f32(minimum+f32(f32(f32(directed*ratio)*f32(maximum-minimum))/maximum));
    float shaft_accel=f32(f32(new_shaft-s.shaft_omega)/in->seconds);s.shaft_omega=new_shaft;
    if(gear!=1&&s.clutch.mode==0&&f32(f32(braking*abs_driven)*sign)>0)braking=-braking;
    float net=fmaf(torque,throttle,f32(braking*f32(1-throttle)));
    MwPhysicsTransmissionClutchInput ci={gear,s.clutch.mode,s.engine_omega,s.shaft_omega,
        shaft_accel,inertia,net,ratio,p->torque_split,contact_fraction,coupling,s.slip_rpm};
    MwPhysicsTransmissionClutchResult cr;
    if(!mw_physics_transmission_clutch_core(&ci,300,20,&cr))return false;
    s.slip_rpm=cr.slip_rpm;s.negative_engine_torque=cr.negative_engine_torque;
    float reaction=cr.engine_reaction_torque,wheel_torque=cr.wheel_torque;
    if(gear!=1) {
        if(s.clutch.mode==0&&in->contact_count>0) {
            float difference=f32(s.shaft_omega-s.engine_omega);
            float slip=driven_slip(in->longitudinal_slip,p->torque_split);
            if(throttle>.10000000149011612f&&f32(slip*sign)>.10000000149011612f&&gear<=2&&difference<0) {
                s.shaft_omega=s.engine_omega;
                if(!mw_physics_transmission_sync_wheels(w,p->torque_split,gear,f32(s.engine_omega/ratio),in->vehicle_speed_128))return false;
            } else {
                float correction=f32(difference*20),limit=fabsf(net);
                if(correction< -limit)correction= -limit;
                if(correction>limit)correction=limit;
                reaction=f32(reaction+correction);
            }
        }
        if(gear==0||gear==2) {
            float total=f32(net+reaction);
            if(reaction<net&&total<0) {
                float curve=launch_curve(f32(total*1000.0f));
                reaction=fmaf(f32(curve*total),p->clutch_slip,reaction);
            }
        }
    }
    /* Original80258148 changes source engine omega+F0, after torque/reaction
       construction but before shaft integration. Earlier sampled RPM retained. */
    if(story){if(!mw_physics_transmission_sabotage_stage(&s.engine_omega,story,clock,sine,blown_event))return false;s.rev_modulation_deadline=story->deadline;}
    MwPhysicsTransmissionShaftInput si={gear,s.clutch.mode,in->seconds,s.engine_omega,rpm,
        net,reaction,inertia,throttle,p->clutch_slip,p->torque.idle_rpm,p->peak_torque_rpm,minimum,maximum};
    MwPhysicsTransmissionShaftResult sr;
    if(!mw_physics_transmission_shaft_step(&si,&sr))return false;
    s.engine_omega=sr.angular_speed;s.angular_acceleration=sr.angular_acceleration;
    if(ratio!=0&&!mw_physics_transmission_cap_airborne_wheels(w,p->torque_split,f32(maximum/ratio)))return false;
    if(s.shaft_omega>maximum&&ratio!=0) {
        if(f32(wheel_torque*ratio)>0)wheel_torque=0;
        s.shaft_omega=maximum;
        if(!mw_physics_transmission_sync_wheels(w,p->torque_split,gear,f32(maximum/ratio),in->vehicle_speed_128))return false;
    }
    if(wheel_torque>0&&in->boost_interface_present)
        wheel_torque=f32(wheel_torque*fmaf(in->boost_interface_scalar,.5f,1));
    s.output_torque=f32(f32(wheel_torque*ratio)*p->gear_efficiency[gear]);
    s.reported_rpm=mw_physics_transmission_reported_rpm(s.shift_delay>0||s.clutch.mode==2,
        gear,in->seconds,s.reported_rpm,f32(s.engine_omega*9.549296379089355f),inertia);
    s.shift_request=s.clutch.mode==0&&!in->vehicle_gate_48?
        mw_physics_transmission_shift_request(p->shift_tables,p->ratios,p->gear_count,
            gear,f32(s.shaft_omega*9.549296379089355f),throttle,p->torque.idle_rpm):0;
    s.applied_throttle=throttle;
    if(!isfinite(s.engine_omega)||!isfinite(s.angular_acceleration)||!isfinite(s.output_torque)||!isfinite(s.reported_rpm))return false;
    *state=s;memcpy(wheels,w,sizeof w);return true;
}


bool mw_physics_transmission_engine_mechanical_step(const MwPhysicsTransmissionEngineParams *p,
    const MwPhysicsTransmissionEngineInput *in,MwPhysicsTransmissionEngineState *state,
    MwPhysicsTransmissionSpeedWheel wheels[4]){return mechanical_step(p,in,state,wheels,NULL,0,NULL,NULL);}

bool mw_physics_transmission_induction_step(const MwPhysicsTransmissionEngineStepParams *p,
    const MwPhysicsTransmissionInductionTiming *timing,float dt,float throttle,MwPhysicsTransmissionEngineStepState *state)
{
    if(!p||!state||!isfinite(dt)||dt<=0||!isfinite(throttle))return false;
    if(p->induction.low_boost<=0&&p->induction.high_boost<=0){state->induction_amount=0;state->induction_display=0;state->induction_boost=0;return true;}
    if(!timing||!isfinite(timing->spool_up)||!isfinite(timing->spool_down)||!isfinite(timing->psi)||!isfinite(timing->tuning_18))return false;
    MwPhysicsTransmissionEngineStepState s=*state;MwPhysicsTransmissionInduction adjusted=p->induction;
    float desired=f32(throttle/.5f);if(desired>1)desired=1;if(desired<0)desired=0;
    float rpm=f32(s.mechanical.engine_omega*9.549296379089355f);
    if(s.mechanical.shift_delay>0)desired=0;
    if(timing->tuning_present&&adjusted.spool>0){float change=timing->tuning_18<0?f32(adjusted.spool*.25f):f32(f32(1-adjusted.spool)*.25f);adjusted.spool=fmaf(change,timing->tuning_18,adjusted.spool);}
    float threshold=fmaf(adjusted.spool,f32(p->mechanical.torque.red_line_rpm-p->mechanical.torque.idle_rpm),p->mechanical.torque.idle_rpm);
    if(p->induction.spool>0&&rpm<threshold)desired=0;
    if(s.induction_amount>desired){
        if(timing->spool_down>9.999999974752427e-7f){float next=f32(s.induction_amount-f32(dt/timing->spool_down));s.induction_amount=next<desired?desired:next;}else s.induction_amount=desired;
    }else if(s.induction_amount<desired){
        if(timing->spool_up>9.999999974752427e-7f){float next=f32(s.induction_amount+f32(dt/timing->spool_up));s.induction_amount=next>desired?desired:next;}else s.induction_amount=desired;
    }
    if(s.induction_amount>1)s.induction_amount=1;
    if(s.induction_amount<0)s.induction_amount=0;
    if(timing->tuning_present){adjusted.low_boost=f32(adjusted.low_boost-f32(f32(adjusted.low_boost*timing->tuning_18)*.25f));adjusted.high_boost=fmaf(f32(adjusted.high_boost*timing->tuning_18),.25f,adjusted.high_boost);}
    s.induction_boost=mw_physics_transmission_induction_raw(&p->mechanical.torque,&adjusted,rpm,s.induction_amount);
    float target=0,maximum=adjusted.high_boost>adjusted.low_boost?adjusted.high_boost:adjusted.low_boost;
    if(adjusted.high_boost>0||adjusted.low_boost>0){
        if(rpm>=threshold){
            float fraction_rpm=fraction(rpm,threshold,p->mechanical.torque.red_line_rpm);
            float raw=fmaf(fraction_rpm,adjusted.high_boost,f32(f32(1-fraction_rpm)*adjusted.low_boost));
            float proportion=maximum>9.999999974752427e-7f?fraction(raw,0,maximum):0;
            target=f32(f32(s.induction_amount*timing->psi)*proportion);
        }else if(adjusted.vacuum<0){
            float fraction_rpm=fraction(rpm,p->mechanical.torque.idle_rpm,threshold),raw=f32(fraction_rpm*adjusted.vacuum);
            float proportion=maximum>9.999999974752427e-7f?fraction(-raw,0,maximum):0;
            target=f32(f32(fraction_rpm*-timing->psi)*proportion);
        }
    }
    if(s.induction_display>target){float next=f32(s.induction_display-f32(dt*20));s.induction_display=next<target?target:next;}
    else if(s.induction_display<target){float next=fmaf(dt,20,s.induction_display);s.induction_display=next>target?target:next;}
    if(!isfinite(s.induction_amount)||!isfinite(s.induction_boost)||!isfinite(s.induction_display))return false;
    *state=s;return true;
}

static bool engine_step(const MwPhysicsTransmissionEngineStepParams *p,
    const MwPhysicsTransmissionEngineStepInput *in,MwPhysicsTransmissionEngineStepState *state,
    MwPhysicsTransmissionSpeedWheel wheels[4],MwPhysicsTransmissionGearEvent *event,
    MwStoryEngine *story,float clock,float (*sine)(float),bool *blown_event,const MwPhysicsTransmissionInductionTiming *timing)
{
    if(!p||!in||!state||!wheels||!event)return false;
    if(!in->input_present){*event=(MwPhysicsTransmissionGearEvent){0};return true;}
    if(p->speed_limiter_count||!isfinite(p->induction.low_boost)||
       !isfinite(p->induction.high_boost)||((p->induction.low_boost>0||p->induction.high_boost>0)&&!timing)||
       !isfinite(in->raw_throttle)||!isfinite(in->external.seconds)||in->external.seconds<=0)return false;
    MwPhysicsTransmissionEngineStepState s=*state;
    MwPhysicsTransmissionSpeedWheel w[4];memcpy(w,wheels,sizeof w);
    MwPhysicsTransmissionEngineInput mechanical=in->external;
    mechanical.applied_throttle=in->rev_block||(story&&story->blown)?0:in->raw_throttle;
    MwPhysicsTransmissionNosInput nos=in->nos;
    nos.seconds=mechanical.seconds;nos.applied_throttle=mechanical.applied_throttle;
    nos.gear_slot=s.mechanical.gear_slot;nos.vehicle_mode_b8=mechanical.vehicle_mode_b8;
    nos.vehicle_speed_128=mechanical.vehicle_speed_128;nos.rev_block=in->rev_block;
    nos.boost_interface_present=mechanical.boost_interface_present;
    nos.boost_interface_scalar=mechanical.boost_interface_scalar;
    if(!mw_physics_transmission_nos_step(&p->nos,&nos,&s.nos,&s.scale_100))return false;
    /* Original80223BCC classifies zero/negative LOW_BOOST/HIGH_BOOST as type0;
     * original8025723C..80257250 clears94/98/9C for that class. */
    if(!mw_physics_transmission_induction_step(p,timing,mechanical.seconds,mechanical.applied_throttle,&s))return false;
    MwPhysicsTransmissionAutomaticParams ap={p->mechanical.shift_tables,
        p->mechanical.ratios,p->mechanical.gear_count,p->shift_speed,p->mechanical.torque.idle_rpm};
    MwPhysicsTransmissionAutomaticState as={{s.mechanical.gear_slot,s.mechanical.clutch.mode,
        s.mechanical.shift_delay},s.cooldown,s.mechanical.shift_request,s.committed};
    MwPhysicsTransmissionAutomaticInput ai={.seconds=mechanical.seconds,
        .raw_throttle=in->raw_throttle,.applied_throttle=mechanical.applied_throttle,
        .shaft_omega=s.mechanical.shaft_omega,.input_present=1,
        .automatic_enabled=in->automatic_enabled,.vehicle_gate_48=mechanical.vehicle_gate_48};
    for(unsigned i=0;i<4;++i){ai.contacted[i]=w[i].spring_compression>0;ai.longitudinal_slip[i]=mechanical.longitudinal_slip[i];}
    MwPhysicsTransmissionGearEvent e;
    if(!mw_physics_transmission_automatic_step(&ap,&ai,&as,&e))return false;
    s.mechanical.gear_slot=as.shift.gear_slot;s.mechanical.clutch.mode=as.shift.clutch_state;
    s.mechanical.shift_delay=as.shift.shift_delay;s.mechanical.shift_request=as.request;
    s.cooldown=as.cooldown;s.committed=as.committed;
    mechanical.boost_9c=s.induction_boost;mechanical.scale_100=s.scale_100;
    if(!mechanical_step(&p->mechanical,&mechanical,&s.mechanical,w,story,clock,sine,blown_event))return false;
    *state=s;memcpy(wheels,w,sizeof w);*event=e;return true;
}

bool mw_physics_transmission_engine_step(const MwPhysicsTransmissionEngineStepParams *p,
    const MwPhysicsTransmissionEngineStepInput *in,MwPhysicsTransmissionEngineStepState *state,
    MwPhysicsTransmissionSpeedWheel wheels[4],MwPhysicsTransmissionGearEvent *event){
    return engine_step(p,in,state,wheels,event,NULL,0,NULL,NULL,NULL);
}
bool mw_physics_transmission_engine_step_with_story(const MwPhysicsTransmissionEngineStepParams *p,
    const MwPhysicsTransmissionEngineStepInput *in,MwPhysicsTransmissionEngineStepState *state,
    MwPhysicsTransmissionSpeedWheel wheels[4],MwPhysicsTransmissionGearEvent *event,
    MwStoryEngine *story,float clock,float (*sine)(float),bool *blown_event){
    if(!state||!wheels||!event||!story||!blown_event||!isfinite(clock)||!isfinite(story->deadline)||story->blown>1)return false;
    MwPhysicsTransmissionEngineStepState s=*state;MwPhysicsTransmissionSpeedWheel w[4];memcpy(w,wheels,sizeof(w));
    MwPhysicsTransmissionGearEvent e={0};MwStoryEngine engine=*story;bool blew=false;
    s.mechanical.rev_modulation_deadline=engine.deadline;
    if(!engine_step(p,in,&s,w,&e,&engine,clock,sine,&blew,NULL))return false;
    *state=s;memcpy(wheels,w,sizeof(w));*event=e;*story=engine;*blown_event=blew;return true;
}

bool mw_physics_transmission_engine_step_complete(const MwPhysicsTransmissionEngineStepParams *p,
    const MwPhysicsTransmissionEngineStepInput *in,MwPhysicsTransmissionEngineStepState *state,
    MwPhysicsTransmissionSpeedWheel wheels[4],MwPhysicsTransmissionGearEvent *event,
    MwStoryEngine *story,float clock,float (*sine)(float),bool *blown_event,const MwPhysicsTransmissionInductionTiming *timing){
    if(!state||!wheels||!event||!story||!blown_event||!isfinite(clock)||!isfinite(story->deadline)||story->blown>1)return false;
    MwPhysicsTransmissionEngineStepState s=*state;MwPhysicsTransmissionSpeedWheel w[4];memcpy(w,wheels,sizeof(w));MwPhysicsTransmissionGearEvent e={0};MwStoryEngine engine=*story;bool blew=false;
    s.mechanical.rev_modulation_deadline=engine.deadline;
    if(!engine_step(p,in,&s,w,&e,&engine,clock,sine,&blew,timing))return false;
    *state=s;memcpy(wheels,w,sizeof(w));*event=e;*story=engine;*blown_event=blew;return true;
}
