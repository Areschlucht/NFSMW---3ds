#include "mw_original_player_input.h"
#include "mw_physics_grip.h"
#include <math.h>
#include <string.h>
static float f32(float v){volatile float rounded=v;return rounded;}
static const float raw_curve[21]={-1,-.736f,-.542f,-.4f,-.292f,-.214f,-.16f,-.123f,-.078f,-.036f,0,.036f,.078f,.123f,.16f,.214f,.292f,.4f,.542f,.736f,1};
static const float speed_curve[10]={40,20,10,5.5f,4.5f,3.25f,2.9f,2.9f,2.9f,2.9f};
static const float mode1_curve[10]={45,15,11,8,7,7,7,7,7,7};
static const float steer_curve[6]={1,1,1.1f,1.2f,1.25f,1.35f};
static const float throttle_curve[10]={1,1,1,.56f,.5f,.35f,.3f,.3f,.3f,.3f};
static const float rate_curve[6]={1,1.05f,1.1f,1.5f,2.2f,3.1f};
static const float rate_steer_curve[6]={1,1.05f,1.1f,1.2f,1.3f,1.4f};
static float uniform(const float *v,unsigned count,float minimum,float inverse,float x)
{
    float position=f32(inverse*f32(x-minimum));
    if(position<0)return v[0];
    if(position>=(float)(count-1))return v[count-1];
    unsigned at=(unsigned)position;float fraction=f32(position-(float)at);
    return fmaf(f32(1-fraction),v[at],f32(fraction*v[at+1]));
}
static float pair_fade(float x)
{
    static const float points[4][2]={{0,.2f},{.2f,.5f},{.5f,.7f},{.7f,1}};
    if(x<=points[0][0])return points[0][1];
    if(x>=points[3][0])return points[3][1];
    for(unsigned i=0;i<3;i++)if(x>=points[i][0]&&x<points[i+1][0]){
        float divisor=f32(points[i+1][0]-points[i][0]);
        float fraction=f32(f32(x-points[i][0])/divisor);
        return fmaf(fraction,f32(points[i+1][1]-points[i][1]),points[i][1]);
    }
    return points[0][1];
}
static bool average_valid(const MwPlayerInputAverage *s)
{
    if(!s->capacity||s->capacity>MW_PLAYER_INPUT_HISTORY||s->count>s->capacity||
       s->cursor>=s->capacity||s->oldest>=s->capacity||!isfinite(s->sum)||
       !isfinite(s->average)||!isfinite(s->seconds)||s->seconds<=0)return false;
    for(unsigned i=0;i<s->capacity;i++)if(!isfinite(s->values[i])||!isfinite(s->times[i]))return false;
    return true;
}
static bool average_step(MwPlayerInputAverage *s,float value,float time)
{
    unsigned index=s->cursor;
    if(s->values[index]==0&&s->times[index]==0)s->count++;
    else s->sum=f32(s->sum-s->values[index]);
    s->sum=f32(s->sum+value);s->values[index]=value;s->times[index]=time;
    unsigned visits=0;
    while(f32(time-s->times[s->oldest])>s->seconds){
        if(++visits>s->capacity)return false;
        if(s->times[s->oldest]>0){
            s->sum=f32(s->sum-s->values[s->oldest]);s->values[s->oldest]=0;s->times[s->oldest]=0;
            if(!s->count)return false;
            s->count--;
        }
        if(++s->oldest>=s->capacity)s->oldest=0;
    }
    if(!s->count||s->count>s->capacity)return false;
    s->average=f32(s->sum/(float)s->count);
    if(++s->cursor>=s->capacity)s->cursor=0;
    return average_valid(s);
}
bool mw_player_steering_init(MwPlayerSteeringState *out)
{
    if(!out)return false;
    MwPlayerSteeringState s={.gain_history=45};
    s.input_average.seconds=.55f;s.input_average.capacity=33;
    s.rate_average.seconds=.15f;s.rate_average.capacity=9;*out=s;return true;
}
bool mw_player_yaw_control(const float *samples,uint32_t count,float speed,
    bool present,float max_speed,float *out)
{
    if(!samples||!count||count>64||!out||!isfinite(speed)||!isfinite(max_speed))return false;
    for(uint32_t i=0;i<count;i++)if(!isfinite(samples[i]))return false;
    float result=samples[0];
    if(present){
        if(max_speed<=0){*out=0;return true;}
        float fraction=f32(fabsf(speed)/max_speed);if(fraction>1)fraction=1;
        if(count>1){
            float position=f32((float)(count-1)*fraction);uint32_t index=(uint32_t)position;
            float remainder=f32(position-(float)index);uint32_t next=index+1;if(next>=count)next=count-1;
            result=fmaf(f32(samples[next]-samples[index]),remainder,samples[index]);
        }
    }
    if(!isfinite(result))return false;
    *out=result;return true;
}
static float gain(MwPlayerSteeringState *s,const MwPlayerSteeringInput *i)
{
    if(i->interface_mode==2)return 45;
    float result=uniform(i->interface_mode==1?mode1_curve:speed_curve,10,0,9.f/160,i->forward_speed);
    float blend=f32(f32(i->brake+i->handbrake)*.5f);
    blend=f32(f32(f32(i->throttle+1)-blend)*.5f);blend=f32(1-blend);
    float effect=f32(1.4500000476837158f*blend);
    effect=fmaf(effect,uniform(throttle_curve,10,0,9.f/160,i->forward_speed),1);
    result=f32(result*effect);
    result=f32(result*uniform(steer_curve,6,0,5,fabsf(s->input_average.average)));
    if(i->effect_present)result=f32(result*fmaf(i->effect_0,.2f,1));
    float fade=i->fade_1ac;
    if(fade>0){
        fade=f32(1-fade);
        if(fade<1&&fade>0){
            float divisor=f32(f32(170*.4470300078392029f)*.699999988079071f);
            float fraction=f32(i->forward_speed/divisor);if(fraction>1)fraction=1;
            fraction=f32(1-fraction);float y=pair_fade(fade);
            result=f32(result*fmaf(f32(1-y),fraction,y));
        }
    }
    float left=f32(i->rear_slip_angle_turns[0]*360),right=f32(i->rear_slip_angle_turns[1]*360),limit=0;
    bool cap=false;
    if(i->raw_steering>0&&right>0){limit=right;cap=true;}
    else if(i->raw_steering<0&&left<0){limit=-left;cap=true;}
    if(cap){if(result<limit)result=limit;if(result>45)result=45;}
    else if(fabsf(s->input_average.average)>=.5f&&result<s->gain_history)result=s->gain_history;
    if(result>45)result=45;
    s->gain_history=result;return result;
}
bool mw_player_steering_step(MwPlayerSteeringState *state,const MwPlayerSteeringInput *i,float *turns)
{
    if(!state||!i||!turns||i->interface_mode>2||i->seconds<=0||i->time<0||
       !average_valid(&state->input_average)||!average_valid(&state->rate_average))return false;
    const float values[]={state->angle_degrees,state->previous_input,state->gain_history,
        i->raw_steering,i->forward_speed,i->throttle,i->brake,i->handbrake,i->seconds,i->time,
        i->tire_steering,i->rear_slip_angle_turns[0],i->rear_slip_angle_turns[1],i->blend_100,i->fade_1ac,i->effect_0};
    for(unsigned n=0;n<sizeof(values)/sizeof(*values);n++)if(!isfinite(values[n]))return false;
    MwPlayerSteeringState s=*state;float previous=s.angle_degrees;
    if(previous>=180)previous=f32(previous-360);
    float requested=f32(f32(i->raw_steering*gain(&s,i))*i->tire_steering);
    if(requested< -45)requested=-45;
    if(requested>45)requested=45;
    float remembered=i->raw_steering;
    if(!i->interface_mode){
        remembered=uniform(raw_curve,21,-1,10,i->raw_steering);
        float rate=fabsf(f32(f32(i->raw_steering-s.previous_input)/i->seconds));
        rate=uniform(rate_curve,6,0,.5f,rate);
        if(!average_step(&s.rate_average,rate,i->time))return false;
        float speed=uniform(throttle_curve,10,0,9.f/160,i->forward_speed);
        rate=f32(f32(speed*180)*s.rate_average.average);
        rate=f32(rate*uniform(rate_steer_curve,6,0,5,fabsf(s.input_average.average)));
        float step=f32(f32(rate*i->tire_steering)*i->seconds);
        float low=f32(previous-step),high=f32(previous+step);
        if(requested<low)requested=low;
        if(requested>high)requested=high;
    }
    s.previous_input=remembered;s.angle_degrees=requested;
    float output=requested;
    if(i->blend_100>0)output=fmaf(fmaf(i->raw_steering,60,-requested),i->blend_100,requested);
    if(!average_step(&s.input_average,remembered,i->time)||!isfinite(output))return false;
    output=f32(output*.0027777778450399637f);
    if(!isfinite(output))return false;
    *state=s;*turns=output;return true;
}

bool mw_player_route_wheels(MwPlayerRouteState *state,const MwPlayerRouteInput *i,
    MwPhysicsGroundWheel wheels[4],MwPlayerRouteResult *out)
{
    if(!state||!i||!wheels||!out||i->seconds<=0||i->wheel_disable_mask>15)return false;
    const float values[]={state->handbrake_history_1b8,i->forward_speed,i->slip_angle_9c,i->handbrake,
        i->brake,i->throttle,i->seconds,i->blend_100,i->disable_110,i->steering,i->body_24,
        i->source_speed_bc,i->grip_d0,i->grip_d4,i->source_e4_70,i->yaw_control,i->effect_4,i->effect_8};
    for(unsigned n=0;n<sizeof(values)/sizeof(*values);n++)if(!isfinite(values[n]))return false;
    MwPhysicsGroundWheel next[4];memcpy(next,wheels,sizeof(next));MwPlayerRouteState s=*state;
    float mph=f32(i->forward_speed*2.236989974975586f),angular=f32(i->slip_angle_9c*6.2831854820251465f);
    float history=s.handbrake_history_1b8;
    if(i->handbrake>=.5f){history=f32(history-f32(20*i->seconds));if(history<.5f)history=.5f;}
    else{history=fmaf(1,i->seconds,history);if(history>1)history=1;}
    s.handbrake_history_1b8=history;history=f32(history*f32(1-i->disable_110));
    float brakes[2]={i->brake,i->brake};
    if(i->effect_present){
        brakes[0]=fmaf(f32(i->effect_8*i->brake),.5f,i->brake);
        brakes[1]=f32(i->brake-f32(f32(i->effect_8*i->brake)*.5f));
    }
    float yaw=i->mode_c8==1?.1f:i->yaw_control;
    if(i->mode_c8!=1&&i->controller_present&&i->settings_present&&!i->controller_byte_2a)yaw=f32(yaw+2.5f);
    MwPlayerRouteResult result={0};
    for(unsigned n=0;n<4;n++){
        MwPhysicsContactWheel *w=&next[n].tire;
        if(!isfinite(w->grip_factor)||!isfinite(w->longitudinal_slip))return false;
        bool reverse_brake=n>1?i->source_e4_70<1:i->source_e4_70>0;
        w->brake.normal_input=i->throttle>.8f&&i->brake>.5f&&fabsf(mph)<10&&reverse_brake?f32(fabsf(mph)*.05f):brakes[n/2];
        float hand=0;
        if(n>1){hand=i->handbrake;if(hand>.2f&&angular>.3f&&mph<80)hand=f32(hand+.5f);}
        w->brake.handbrake_input=hand;
        float grip=1,lateral=1;
        if(n>1){float assist=mw_physics_rear_grip_assist_raw(angular,hand,i->source_speed_bc,yaw,i->body_24);grip=fmaf(history,f32(assist-1),1);}
        if(i->blend_100>0&&n<=1){lateral=fmaf(f32(i->blend_100*fabsf(i->steering)),.75f,1);grip=f32(grip*lateral);}
        w->grip_factor=f32(w->grip_factor*grip);w->lateral_grip_factor=lateral;
        if(i->effect_present){w->lateral_scale=fmaf(i->effect_4,.2f,1);w->longitudinal_scale=f32(1-f32(i->effect_4*.2f));}
        w->grip_factor=f32(w->grip_factor*f32(i->grip_d0*i->grip_d4));
        if(i->wheel_disable_mask&(1u<<n)){w->brake.handbrake_input=0;w->brake.normal_input=1;w->grip_factor=f32(w->grip_factor*.3f);}
        if(w->longitudinal_slip>result.maximum_positive_slip){result.maximum_positive_slip=w->longitudinal_slip;result.maximum_slip_wheel=n;}
        if(!isfinite(w->grip_factor)||!isfinite(w->brake.normal_input)||!isfinite(w->brake.handbrake_input))return false;
    }
    *state=s;memcpy(wheels,next,sizeof(next));*out=result;return true;
}
static float points(const float (*v)[2],unsigned n,float x)
{
    if(x<=v[0][0])return v[0][1];
    if(x>=v[n-1][0])return v[n-1][1];
    for(unsigned k=0;k<n-1;k++)if(x>=v[k][0]&&x<v[k+1][0])
        {float t=f32(f32(x-v[k][0])/f32(v[k+1][0]-v[k][0]));return fmaf(v[k+1][1],t,f32(v[k][1]*f32(1-t)));}
    return v[0][1];
}
static void traction_reset(MwPlayerTractionState *s){*s=(MwPlayerTractionState){.scale=1};}
static void traction_step(MwPlayerTractionState *s,float dt,float mph,float slip,float angle,unsigned wheel)
{
    if(s->stage){
        if(mph>5&&fabsf(f32(angle*6.2831854820251465f))>.5f){traction_reset(s);return;}
        if(slip<.5f){s->quiet_time=f32(s->quiet_time+dt);if(s->quiet_time>1)traction_reset(s);}
        else{s->timer=f32(s->timer-dt);s->quiet_time=0;if(s->timer<0){s->stage--;s->timer=2;}}
    }else if(mph<20&&slip>.5f){
        static const float curve[6][2]={{0,1},{5,.8f},{9,.9f},{12.6f,.833f},{17.1f,.72f},{25,.65f}};
        float value=points(curve,6,slip);s->scale=f32(value*.7142857313156128f);s->timer=2;s->quiet_time=0;
        s->stage=(uint32_t)fmaf(6,f32(1.5f-value),(float)(wheel&1));
    }
}
static void yaw_step(MwPlayerYawState *s,const MwPlayerAssistInput *a,MwPhysicsGroundWheel wheels[4],MwPlayerAssistOutput *out)
{
    const MwPlayerRouteInput *i=&a->routing;
    if(s->stage&&((i->flags_c4&1)||i->mode_c8==1)){*s=(MwPlayerYawState){0};return;}
    float change=s->stage==1||s->stage==2?8:-2;
    s->ramp=fmaf(change,i->seconds,s->ramp);
    if(s->ramp<=0){s->ramp=0;s->stage=0;}
    else if(s->ramp>=1){s->ramp=1;s->stage=2;}
    float slip=i->slip_angle_9c,omega=a->local_angular_y,average=a->averaged_steering;
    float threshold=f32(12*.0027777778450399637f),speed=f32(30*.4470300078392029f);
    if(s->stage>1){
        if(f32(slip*omega)<0&&fabsf(slip)<=.25f&&i->source_speed_bc>speed&&f32(average*slip)<=0&&fabsf(slip)>threshold)s->stage=2;
        else if(f32(f32(i->throttle*i->steering)*slip)>threshold&&i->source_speed_bc>speed)s->stage=2;
        else s->stage=f32(i->throttle*fabsf(slip))>threshold?1:3;
    }else if(i->source_speed_bc>speed&&(i->handbrake>.5f||fabsf(slip)>threshold))s->stage=1;
    if(s->ramp<=0)return;
    float radians=f32(slip*6.2831854820251465f);
    if(i->blend_100<=0&&i->source_speed_bc>f32(35*.4470300078392029f)&&fabsf(radians)>f32(30*.01745299994945526f)&&i->controller_present){
        out->controller_a4_present=true;out->controller_a4_argument=f32(i->seconds*f32(s->ramp*.5f));
    }
    if(f32(radians*omega)<0&&a->contact_count>1){
        const float degrees=.01745329424738884f;
        float curve[7][2]={{0,0},{f32(15*degrees),.1f},{f32(30*degrees),.45f},{f32(45*degrees),.85f},
            {f32(60*degrees),.95f},{f32(89*degrees),1.15f},{f32(90*degrees),0}};
        float multiplier=f32(points((const float (*)[2])curve,7,fabsf(radians))*4);
        float torque=f32(f32(f32(s->ramp*-omega)*multiplier)*a->source_a4);
        out->torque_present=true;
        for(unsigned n=0;n<3;n++)out->torque_world[n]=f32(a->body_up[n]*torque);
    }
    float input=f32(i->steering*radians)>0?fabsf(i->steering):0;
    float coordinate=f32(input*4);coordinate=fmaf(fabsf(radians),.5f,coordinate);coordinate=fmaf(fabsf(omega),.5f,coordinate);coordinate=f32(coordinate*s->ramp);
    static const float curve[10]={1.1f,.95f,.87f,.77f,.67f,.6f,.51f,.43f,.37f,.34f};
    float combined=uniform(curve,10,0,9,coordinate);
    wheels[2].tire.combined_factor=combined;wheels[3].tire.combined_factor=combined;
}
bool mw_player_input_route(MwPlayerAssistState *state,const MwPlayerAssistInput *input,
    MwPhysicsGroundWheel wheels[4],MwPlayerAssistOutput *out)
{
    if(!state||!input||!wheels||!out||state->yaw.stage>3||input->contact_count>4)return false;
    const float values[]={state->traction.timer,state->traction.scale,state->traction.quiet_time,state->yaw.ramp,
        input->engine_max_speed,input->averaged_steering,input->local_angular_y,input->body_up[0],input->body_up[1],input->body_up[2],input->source_a4};
    for(unsigned n=0;n<sizeof(values)/sizeof(*values);n++)if(!isfinite(values[n]))return false;
    MwPlayerAssistState s=*state;MwPlayerAssistInput i=*input;MwPhysicsGroundWheel next[4];memcpy(next,wheels,sizeof(next));MwPlayerAssistOutput result={0};
    i.routing.disable_110=s.yaw.ramp;
    if(!mw_player_yaw_control(i.yaw_samples,i.yaw_count,i.routing.source_speed_bc,i.engine_interface_present,i.engine_max_speed,&i.routing.yaw_control)||
       !mw_player_route_wheels(&s.route,&i.routing,next,&result.route))return false;
    if(i.routing.mode_c8!=1&&i.routing.mode_cc==2&&i.routing.throttle>=1)
        traction_step(&s.traction,i.routing.seconds,f32(i.routing.forward_speed*2.236989974975586f),result.route.maximum_positive_slip,i.routing.slip_angle_9c,result.route.maximum_slip_wheel);
    else traction_reset(&s.traction);
    if(i.routing.flags_c4&1)for(unsigned n=0;n<4;n++)next[n].tire.grip_factor=f32(next[n].tire.grip_factor*.25f);
    yaw_step(&s.yaw,&i,next,&result);
    for(unsigned n=0;n<3;n++)if(!isfinite(result.torque_world[n]))return false;
    if(!isfinite(result.controller_a4_argument))return false;
    *state=s;memcpy(wheels,next,sizeof(next));*out=result;return true;
}

bool mw_player_charge_gamebreaker(float *charge,float amount)
{
    if(!charge||!isfinite(*charge)||!isfinite(amount))return false;
    float next=f32(*charge+amount);
    if(next<0)next=0;else if(next>1)next=1;
    *charge=next;return true;
}

static uint32_t float_word(float x){uint32_t u;memcpy(&u,&x,4);return u;}
static float word_float(uint32_t u){float x;memcpy(&x,&u,4);return x;}
static float source_kernel_cos(float x,float y)
{
    uint32_t ix=float_word(x)&0x7fffffff;
    if(ix<=0x31ffffff)return 1;
    float z=f32(x*x);
    float p=fmaf(z,-1.135964759757524e-11f,2.087572337217125e-9f);
    p=fmaf(z,p,-2.7557314297155244e-7f);p=fmaf(z,p,2.4801587642286904e-5f);
    p=fmaf(z,p,-.0013888889225199819f);p=fmaf(z,p,.0416666679084301f);
    float r=f32(z*p),xy=f32(x*y),correction=fmaf(z,r,-xy);
    if(ix<=0x3e999999)return f32(1-fmaf(z,.5f,-correction));
    float q=ix>0x3f480000?.28125f:word_float(ix-0x01000000);
    float a=f32(1-q),hz=fmaf(z,.5f,-q);
    return f32(a-f32(hz-correction));
}
static float source_kernel_sin(float x,float y,bool tail)
{
    if((float_word(x)&0x7fffffff)<=0x31ffffff)return x;
    float z=f32(x*x),v=f32(z*x);
    float p=fmaf(z,1.5896910177115586e-10f,-2.5050759688838298e-8f);
    p=fmaf(z,p,2.7557314297155244e-6f);p=fmaf(z,p,-.00019841270113829523f);
    p=fmaf(z,p,.008333333767950535f);
    if(!tail)return fmaf(v,fmaf(z,p,-.1666666716337204f),x);
    float t=fmaf(y,.5f,-f32(v*p));t=fmaf(z,t,-y);
    t=f32(t-f32(v*-.1666666716337204f));return f32(x-t);
}
/*
 * ====================================================
 * Copyright (C) 1993 by Sun Microsystems, Inc. All rights reserved.
 *
 * Developed at SunPro, a Sun Microsystems, Inc. business.
 * Permission to use, copy, modify, and distribute this
 * software is freely granted, provided that this notice
 * is preserved.
 * ====================================================
 */

/* Adapted float reduction equations; source PPC8031EC3C has three fused
   accumulation loops, represented explicitly below. Source tables verified. */
static const int init_jk[3]={4,7,9};
static const float PIo2[11]={1.5703125f,4.5776367188e-4f,2.5987625122e-5f,7.5437128544e-8f,6.0026650317e-11f,7.3896444519e-13f,5.3845816694e-15f,5.6378512969e-18f,8.3009228831e-20f,3.2756352257e-22f,6.3331015649e-25f};
static const float zero=0,one=1,two8=256,twon8=.00390625f;
static const int32_t source_ipio2[198]={0xa2,0xf9,0x83,0x6e,0x4e,0x44,0x15,0x29,0xfc,0x27,0x57,0xd1,0xf5,0x34,0xdd,0xc0,0xdb,0x62,0x95,0x99,0x3c,0x43,0x90,0x41,0xfe,0x51,0x63,0xab,0xde,0xbb,0xc5,0x61,0xb7,0x24,0x6e,0x3a,0x42,0x4d,0xd2,0xe0,0x6,0x49,0x2e,0xea,0x9,0xd1,0x92,0x1c,0xfe,0x1d,0xeb,0x1c,0xb1,0x29,0xa7,0x3e,0xe8,0x82,0x35,0xf5,0x2e,0xbb,0x44,0x84,0xe9,0x9c,0x70,0x26,0xb4,0x5f,0x7e,0x41,0x39,0x91,0xd6,0x39,0x83,0x53,0x39,0xf4,0x9c,0x84,0x5f,0x8b,0xbd,0xf9,0x28,0x3b,0x1f,0xf8,0x97,0xff,0xde,0x5,0x98,0xf,0xef,0x2f,0x11,0x8b,0x5a,0xa,0x6d,0x1f,0x6d,0x36,0x7e,0xcf,0x27,0xcb,0x9,0xb7,0x4f,0x46,0x3f,0x66,0x9e,0x5f,0xea,0x2d,0x75,0x27,0xba,0xc7,0xeb,0xe5,0xf1,0x7b,0x3d,0x7,0x39,0xf7,0x8a,0x52,0x92,0xea,0x6b,0xfb,0x5f,0xb1,0x1f,0x8d,0x5d,0x8,0x56,0x3,0x30,0x46,0xfc,0x7b,0x6b,0xab,0xf0,0xcf,0xbc,0x20,0x9a,0xf4,0x36,0x1d,0xa9,0xe3,0x91,0x61,0x5e,0xe6,0x1b,0x8,0x65,0x99,0x85,0x5f,0x14,0xa0,0x68,0x40,0x8d,0xff,0xd8,0x80,0x4d,0x73,0x27,0x31,0x6,0x6,0x15,0x56,0xca,0x73,0xa8,0xc9,0x60,0xe2,0x7b,0xc0,0x8c,0x6b};
static int source_kernel_reduce(float *x,float *y,int e0,int nx,int prec,const int32_t *ipio2)
{
	int32_t jz,jx,jv,jp,jk,carry,n,iq[20],i,j,k,m,q0,ih;
	float z,fw,f[20],fq[20]={0},q[20];

    /* initialize jk*/
	jk = init_jk[prec];
	jp = jk;

    /* determine jx,jv,q0, note that 3>q0 */
	jx =  nx-1;
	jv = (e0-3)/8; if(jv<0) jv=0;
	q0 =  e0-8*(jv+1);

    /* set up f[0] to f[jx+jk] where f[jx+jk] = ipio2[jv+jk] */
	j = jv-jx; m = jx+jk;
	for(i=0;i<=m;i++,j++) f[i] = (j<0)? zero : (float) ipio2[j];

    /* compute q[0],q[1],...q[jk] */
	for (i=0;i<=jk;i++) {
	    for(j=0,fw=0.0;j<=jx;j++) fw = fmaf(x[j],f[jx+i-j],fw);
	    q[i] = fw;
	}

	jz = jk;
recompute:
    /* distill q[] into iq[] reversingly */
	for(i=0,j=jz,z=q[jz];j>0;i++,j--) {
	    fw    =  (float)((int32_t)(twon8* z));
	    iq[i] =  (int32_t)(z-two8*fw);
	    z     =  q[j-1]+fw;
	}

    /* compute n */
	z  = scalbnf(z,(int)q0);	/* actual value of z */
	z -= (float)8.0*floorf(z*(float)0.125);	/* trim off integer >= 8 */
	n  = (int32_t) z;
	z -= (float)n;
	ih = 0;
	if(q0>0) {	/* need iq[jz-1] to determine n */
	    i  = (iq[jz-1]>>(8-q0)); n += i;
	    iq[jz-1] -= i<<(8-q0);
	    ih = iq[jz-1]>>(7-q0);
	}
	else if(q0==0) ih = iq[jz-1]>>7;
	else if(z>=(float)0.5) ih=2;

	if(ih>0) {	/* q > 0.5 */
	    n += 1; carry = 0;
	    for(i=0;i<jz ;i++) {	/* compute 1-q */
		j = iq[i];
		if(carry==0) {
		    if(j!=0) {
			carry = 1; iq[i] = 0x100- j;
		    }
		} else  iq[i] = 0xff - j;
	    }
	    if(q0>0) {		/* rare case: chance is 1 in 12 */
	        switch(q0) {
	        case 1:
	    	   iq[jz-1] &= 0x7f; break;
	    	case 2:
	    	   iq[jz-1] &= 0x3f; break;
	        }
	    }
	    if(ih==2) {
		z = one - z;
		if(carry!=0) z -= scalbnf(one,(int)q0);
	    }
	}

    /* check if recomputation is needed */
	if(z==zero) {
	    j = 0;
	    for (i=jz-1;i>=jk;i--) j |= iq[i];
	    if(j==0) { /* need recomputation */
		for(k=1;iq[jk-k]==0;k++);   /* k = no. of terms needed */

		for(i=jz+1;i<=jz+k;i++) {   /* add q[jz+1] to q[jz+k] */
		    f[jx+i] = (float) ipio2[jv+i];
		    for(j=0,fw=0.0;j<=jx;j++) fw = fmaf(x[j],f[jx+i-j],fw);
		    q[i] = fw;
		}
		jz += k;
		goto recompute;
	    }
	}

    /* chop off zero terms */
	if(z==(float)0.0) {
	    jz -= 1; q0 -= 8;
	    while(iq[jz]==0) { jz--; q0-=8;}
	} else { /* break z into 8-bit if necessary */
	    z = scalbnf(z,-(int)q0);
	    if(z>=two8) {
		fw = (float)((int32_t)(twon8*z));
		iq[jz] = (int32_t)(z-two8*fw);
		jz += 1; q0 += 8;
		iq[jz] = (int32_t) fw;
	    } else iq[jz] = (int32_t) z ;
	}

    /* convert integer "bit" chunk to floating-point value */
	fw = scalbnf(one,(int)q0);
	for(i=jz;i>=0;i--) {
	    q[i] = fw*(float)iq[i]; fw*=twon8;
	}

    /* compute PIo2[0,...,jp]*q[jz,...,0] */
	for(i=jz;i>=0;i--) {
	    for(fw=0.0,k=0;k<=jp&&k<=jz-i;k++) fw = fmaf(PIo2[k],q[i+k],fw);
	    fq[jz-i] = fw;
	}

    /* compress fq[] into y[] */
	switch(prec) {
	    case 0:
		fw = 0.0;
		for (i=jz;i>=0;i--) fw += fq[i];
		y[0] = (ih==0)? fw: -fw;
		break;
	    case 1:
	    case 2:
		fw = 0.0;
		for (i=jz;i>=0;i--) fw += fq[i];
		y[0] = (ih==0)? fw: -fw;
		fw = fq[0]-fw;
		for (i=1;i<=jz;i++) fw += fq[i];
		y[1] = (ih==0)? fw: -fw;
		break;
	    case 3:	/* painful */
		for (i=jz;i>0;i--) {
		    fw      = fq[i-1]+fq[i];
		    fq[i]  += fq[i-1]-fw;
		    fq[i-1] = fw;
		}
		for (i=jz;i>1;i--) {
		    fw      = fq[i-1]+fq[i];
		    fq[i]  += fq[i-1]-fw;
		    fq[i-1] = fw;
		}
		for (fw=0.0,i=jz;i>=2;i--) fw += fq[i];
		if(ih==0) {
		    y[0] =  fq[0]; y[1] =  fq[1]; y[2] =  fw;
		} else {
		    y[0] = -fq[0]; y[1] = -fq[1]; y[2] = -fw;
		}
	}
	return n&7;
}

static int source_reduce_angle(float x,float out[2])
{
    uint32_t ix=float_word(x)&0x7fffffff;
    const float p1=1.5707855224609375f,t1=1.0804334124259185e-5f;
    const float p2=1.0804273188114166e-5f,t2=6.07709993438732e-11f;
    if(ix<=0x3f490fd8){out[0]=x;out[1]=0;return 0;}
    if(ix<=0x4016cbe3){
        bool negative=signbit(x);float z=negative?f32(x+p1):f32(x-p1),tail=t1;
        if((ix&0x7ffffff0)==0x3fc90fd0){z=negative?f32(z+p2):f32(z-p2);tail=t2;}
        out[0]=negative?f32(z+tail):f32(z-tail);
        out[1]=negative?f32(f32(z-out[0])+tail):f32(f32(z-out[0])-tail);
        return negative?-1:1;
    }
    if(ix>0x43490f80){
        int e0=(int)(ix>>23)-134;
        float z=word_float(ix-(uint32_t)(e0*0x00800000)),parts[3];
        for(unsigned n=0;n<2;n++){parts[n]=(float)(int32_t)z;z=f32(f32(z-parts[n])*256);}
        parts[2]=z;int count=3;while(count>1&&parts[count-1]==0)count--;
        int n=source_kernel_reduce(parts,out,e0,count,2,source_ipio2);
        if(signbit(x)){out[0]=-out[0];out[1]=-out[1];return -n;}return n;
    }
    static const uint32_t npio2[32]={0x3fc90f00,0x40490f00,0x4096cb00,0x40c90f00,0x40fb5300,0x4116cb00,0x412fed00,0x41490f00,0x41623100,0x417b5300,0x418a3a00,0x4196cb00,0x41a35c00,0x41afed00,0x41bc7e00,0x41c90f00,0x41d5a000,0x41e23100,0x41eec200,0x41fb5300,0x4203f200,0x420a3a00,0x42108300,0x4216cb00,0x421d1400,0x42235c00,0x4229a500,0x422fed00,0x42363600,0x423c7e00,0x4242c700,0x42490f00};
    float t=fabsf(x);int n=(int)fmaf(t,.6366198062896729f,.5f);float fn=(float)n;
    float r=f32(t-f32(fn*p1)),w=f32(fn*t1);out[0]=f32(r-w);
    if(n>31||(ix&0x7fffff00)==npio2[n-1]){
        int exponent=(int)(ix>>23),loss=exponent-(int)((float_word(out[0])>>23)&255);
        if(loss>8){
            t=r;w=f32(fn*p2);r=f32(t-w);w=fmaf(fn,t2,-f32(f32(t-r)-w));out[0]=f32(r-w);
            loss=exponent-(int)((float_word(out[0])>>23)&255);
            if(loss>25){t=r;w=f32(fn*6.077094383272197e-11f);r=f32(t-w);w=fmaf(fn,6.123234262925839e-17f,-f32(f32(t-r)-w));out[0]=f32(r-w);}
        }
    }
    out[1]=f32(f32(r-out[0])-w);
    if(signbit(x)){out[0]=-out[0];out[1]=-out[1];return -n;}return n;
}
bool mw_player_source_sincos(float x,float *sine,float *cosine)
{
    if(!sine||!cosine||!isfinite(x)||fabsf(x)>400)return false;
    float y[2],s,c;int n=source_reduce_angle(x,y);
    if((float_word(x)&0x7fffffff)<=0x3f490fd8){s=source_kernel_sin(x,0,false);c=source_kernel_cos(x,0);}
    else switch((unsigned)n&3){
    case 0:s=source_kernel_sin(y[0],y[1],true);c=source_kernel_cos(y[0],y[1]);break;
    case 1:s=source_kernel_cos(y[0],y[1]);c=-source_kernel_sin(y[0],y[1],true);break;
    case 2:s=-source_kernel_sin(y[0],y[1],true);c=-source_kernel_cos(y[0],y[1]);break;
    default:s=-source_kernel_cos(y[0],y[1]);c=source_kernel_sin(y[0],y[1],true);break;
    }
    *sine=s;*cosine=c;return true;
}
bool mw_player_steer_directions(const float matrix[16],float turns,float track,float base,MwPhysicsContactVector out[4])
{
    if(!matrix||!out||!isfinite(turns)||!isfinite(track)||!isfinite(base)||track<=0||base<=0||turns<-.5f||turns>1)return false;
    for(unsigned n=0;n<16;n++)if(!isfinite(matrix[n]))return false;
    float a=f32(turns*6.2831854820251465f);if(a>3.1415927410125732f)a=f32(a-6.2831854820251465f);
    bool positive=a>=0;float inner=positive?a:-a,outer=f32(f32(base*inner)/fmaf(track,inner,base));
    float angles[2]={positive?outer:-inner,positive?inner:-outer};MwPhysicsContactVector result[4];
    for(unsigned n=0;n<2;n++){
        float s,c;if(!mw_player_source_sincos(angles[n],&s,&c))return false;
        float v[3];for(unsigned j=0;j<3;j++){float t=f32(s*matrix[j]);t=fmaf(0,matrix[4+j],t);v[j]=fmaf(c,matrix[8+j],t);}
        result[n]=(MwPhysicsContactVector){v[0],v[1],v[2]};
    }
    result[2]=result[3]=(MwPhysicsContactVector){matrix[8],matrix[9],matrix[10]};
    memcpy(out,result,sizeof(result));return true;
}
float mw_player_source_sine(float x)
{float s,c;return mw_player_source_sincos(x,&s,&c)?s:NAN;}
float mw_player_source_cosine(float x)
{float s,c;return mw_player_source_sincos(x,&s,&c)?c:NAN;}

static float collision_dot(const float a[3],const float b[3])
{return fmaf(a[2],b[2],f32(f32(a[0]*b[0])+f32(a[1]*b[1])));}
static bool collision_state_valid(const MwPlayerCollisionState *s)
{return isfinite(s->collision_timer)&&isfinite(s->wall_nose_turn)&&isfinite(s->wall_side_turn)&&isfinite(s->last_ground_time);}
static bool finite_array(const float *p,unsigned n)
{for(unsigned j=0;j<n;j++)if(!isfinite(p[j]))return false;return true;}
bool mw_player_collision_event(MwPlayerCollisionState *state,const MwPlayerCollisionInput *i)
{
    if(!state||!i||!collision_state_valid(state)||
       !finite_array(i->position,3)||!finite_array(i->normal,3)||!finite_array(i->closing_velocity,3)||!finite_array(i->object_a_velocity,3)||
       !finite_array(i->body_position,3)||!finite_array(i->body_forward,3)||!finite_array(i->body_right,3)||!finite_array(i->body_dimension,3)||
       !isfinite(i->impulse_a)||!isfinite(i->impulse_b)||!isfinite(i->signed_speed)||!isfinite(i->source_time))return false;
    MwPlayerCollisionState s=*state;uint32_t type=i->flags>>29;
    if(type==1||type==2){
        float impulse=i->flags&0x10000000?0:i->impulse_a;
        if(i->owner_is_object_b)impulse=i->flags&0x04000000?0:i->impulse_b;
        if(impulse>10){float t=f32(f32(impulse-10)/f32(40.f-10));if(t<0)t=0;else if(t>1)t=1;if(t>s.collision_timer)s.collision_timer=t;}
    }
    if(type==3)s.last_ground_time=i->source_time;
    if(type==2&&fabsf(i->normal[1])<.1f&&i->collision_body_present&&collision_dot(i->closing_velocity,i->closing_velocity)<56.25f){
        float lever[3];for(unsigned n=0;n<3;n++)lever[n]=f32(i->position[n]-i->body_position[n]);
        if(s.wall_nose_turn==0&&collision_dot(i->object_a_velocity,i->object_a_velocity)<6.25f&&collision_dot(i->normal,i->body_forward)<=0&&
           collision_dot(lever,i->body_forward)>f32(i->body_dimension[2]*.75f)){
            float side=collision_dot(i->normal,i->body_right);s.wall_nose_turn=f32((side>0?1.f:-1.f)-side);
        }
        if(s.wall_side_turn==0&&i->signed_speed<0){
            float side=collision_dot(i->normal,i->body_right);
            if(fabsf(side)>9.999999974752427e-7f&&fabsf(collision_dot(lever,i->body_forward))>f32(i->body_dimension[2]*.75f))s.wall_side_turn=side;
        }
    }
    if(!collision_state_valid(&s))return false;
    *state=s;return true;
}
bool mw_player_wall_steering(const MwPlayerCollisionState *s,const MwPlayerWallSteeringInput *i,MwPlayerWallSteeringOutput *out)
{
    if(!s||!i||!out||!collision_state_valid(s)||!finite_array(i->body_matrix,16)||!finite_array(i->angular_velocity_world,3)||
       !isfinite(i->steering)||!isfinite(i->throttle)||i->contact_count>4)return false;
    MwPlayerWallSteeringOutput result={0};float nose=s->wall_nose_turn,side=s->wall_side_turn;
    float deltas[2];unsigned count=0;
    if(nose!=0&&i->contact_count>2&&i->throttle>0){
        float value=f32(f32(i->steering*i->throttle)*.125f);
        if(f32(nose*value)<0){*out=result;return true;}
        deltas[count++]=f32(value*fabsf(nose));
    }
    if(f32(f32(side*i->steering)*i->throttle)>0&&i->contact_count>2&&i->gear==0)
        deltas[count++]=f32(f32(f32(-i->steering*i->throttle)*.125f)*fabsf(side));
    for(unsigned n=0;n<count;n++)for(unsigned j=0;j<3;j++){
        float t=f32(0.f*i->body_matrix[j]);t=fmaf(deltas[n],i->body_matrix[4+j],t);t=fmaf(0.f,i->body_matrix[8+j],t);
        result.angular_velocity_world[n][j]=f32(i->angular_velocity_world[j]+t);
        if(!isfinite(result.angular_velocity_world[n][j]))return false;
    }
    result.count=count;*out=result;return true;
}
bool mw_player_collision_begin(MwPlayerCollisionState *s,float seconds)
{
    if(!s||!collision_state_valid(s)||!isfinite(seconds)||seconds<=0)return false;
    float timer=f32(s->collision_timer-seconds);s->collision_timer=timer>0?timer:0;return true;
}
void mw_player_collision_end(MwPlayerCollisionState *s)
{if(s){s->wall_nose_turn=0;s->wall_side_turn=0;}}
