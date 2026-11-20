#include "mw_original_player_input.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
int main(void)
{
    MwPlayerSteeringState steering;assert(mw_player_steering_init(&steering));
    assert(steering.gain_history==45&&steering.input_average.capacity==33&&steering.rate_average.capacity==9);
    MwPlayerSteeringInput input={.raw_steering=.5f,.seconds=1.f/60,.time=100,.tire_steering=1,.throttle=1};
    float turns=99;assert(mw_player_steering_step(&steering,&input,&turns));
    /* Actual original first-step fixture: source raw-input curve yields.214,
       rate curve saturates3.1, limiting requested20degrees to9.3degrees. */
    assert(steering.previous_input==.214f&&steering.angle_degrees==9.30000019073486328125f);
    assert(turns==.0258333347737789154052734375f);
    for(unsigned n=0;n<1200;n++){
        input.time+=input.seconds;input.raw_steering=(n/120)%2?-.75f:.75f;
        input.forward_speed=(float)(n%160);input.handbrake=n%2;input.brake=n%3?0:1;
        assert(mw_player_steering_step(&steering,&input,&turns));
        assert(isfinite(turns)&&steering.input_average.count<=33&&steering.rate_average.count<=9);
    }
    MwPlayerSteeringState before=steering;float sentinel=123,out=sentinel;
    input.raw_steering=NAN;assert(!mw_player_steering_step(&steering,&input,&out));
    assert(!memcmp(&steering,&before,sizeof(before))&&out==sentinel);
    input.raw_steering=.5f;input.seconds=0;assert(!mw_player_steering_step(&steering,&input,&out));
    assert(!memcmp(&steering,&before,sizeof(before))&&out==sentinel);
    input.seconds=1.f/60;input.interface_mode=3;assert(!mw_player_steering_step(&steering,&input,&out));
    assert(mw_player_steering_init(&steering));input.interface_mode=2;input.raw_steering=1;input.tire_steering=2;
    assert(mw_player_steering_step(&steering,&input,&turns)&&steering.angle_degrees==45&&turns==.125f);
    assert(steering.rate_average.count==0&&steering.previous_input==1&&steering.gain_history==45);
    MwPhysicsGroundWheel wheels[4]={0};
    for(unsigned n=0;n<4;n++){wheels[n].tire.grip_factor=1;wheels[n].tire.lateral_scale=2;wheels[n].tire.longitudinal_scale=3;}
    MwPlayerRouteState route={1};MwPlayerRouteInput routing={.handbrake=1,.slip_angle_9c=10,.seconds=1.f/60,.grip_d0=1,.grip_d4=1,.yaw_control=1};MwPlayerRouteResult result;
    assert(mw_player_route_wheels(&route,&routing,wheels,&result));
    assert(wheels[0].tire.brake.handbrake_input==0&&wheels[1].tire.brake.handbrake_input==0);
    assert(wheels[2].tire.brake.handbrake_input==1.5f&&wheels[3].tire.brake.handbrake_input==1.5f);
    for(unsigned n=0;n<4;n++)assert(wheels[n].tire.lateral_scale==2&&wheels[n].tire.longitudinal_scale==3);
    routing.wheel_disable_mask=4;assert(mw_player_route_wheels(&route,&routing,wheels,&result));
    assert(wheels[2].tire.brake.handbrake_input==0&&wheels[2].tire.brake.normal_input==1);
    assert(wheels[2].tire.grip_factor==.3f);
    MwPhysicsGroundWheel original[4];memcpy(original,wheels,sizeof(original));MwPlayerRouteState old=route;MwPlayerRouteResult unchanged={123,99};result=unchanged;
    wheels[3].tire.grip_factor=NAN;memcpy(original,wheels,sizeof(original));
    assert(!mw_player_route_wheels(&route,&routing,wheels,&result));
    assert(!memcmp(original,wheels,sizeof(original))&&!memcmp(&route,&old,sizeof(old))&&!memcmp(&result,&unchanged,sizeof(result)));
    const float yaw_samples[4]={.1f,.5f,.7f,.1f};float yaw_value=99;
    assert(mw_player_yaw_control(yaw_samples,4,80,true,80,&yaw_value)&&yaw_value==.1f);
    assert(mw_player_yaw_control(yaw_samples,4,-80,false,80,&yaw_value)&&yaw_value==.1f);
    assert(mw_player_yaw_control(yaw_samples,4,20,true,0,&yaw_value)&&yaw_value==0);
    assert(!mw_player_yaw_control(yaw_samples,0,20,true,80,&yaw_value)&&yaw_value==0);
    memset(wheels,0,sizeof(wheels));
    for(unsigned n=0;n<4;n++){wheels[n].tire.grip_factor=1;wheels[n].tire.longitudinal_slip=10;}
    MwPlayerAssistState assist={.route={1},.traction={.scale=1}};
    MwPlayerAssistInput a={.routing={.throttle=1,.forward_speed=2,.seconds=1.f/60,.grip_d0=1,.grip_d4=1,.mode_cc=2},
        .yaw_samples=yaw_samples,.yaw_count=4,.body_up={0,1,0},.source_a4=1,.contact_count=4};
    MwPlayerAssistOutput commands;
    assert(mw_player_input_route(&assist,&a,wheels,&commands));
    assert(assist.traction.stage>0&&assist.traction.timer==2&&assist.traction.scale<1);
    a.routing.slip_angle_9c=.1f;a.routing.source_speed_bc=30;a.local_angular_y=-1;
    a.routing.controller_present=true;assist.yaw.stage=2;assist.yaw.ramp=.5f;
    assert(mw_player_input_route(&assist,&a,wheels,&commands));
    assert(commands.controller_a4_present&&commands.controller_a4_argument>0);
    assert(commands.torque_present&&commands.torque_world[0]==0&&commands.torque_world[1]>0&&commands.torque_world[2]==0);
    assert(wheels[2].tire.combined_factor>0&&wheels[2].tire.combined_factor==wheels[3].tire.combined_factor);
    MwPlayerAssistState prior_assist=assist;MwPlayerAssistOutput prior_commands=commands;
    memcpy(original,wheels,sizeof(wheels));a.source_a4=NAN;
    assert(!mw_player_input_route(&assist,&a,wheels,&commands));
    assert(!memcmp(&assist,&prior_assist,sizeof(assist))&&!memcmp(wheels,original,sizeof(wheels))&&!memcmp(&commands,&prior_commands,sizeof(commands)));
    float charge=.9f;assert(mw_player_charge_gamebreaker(&charge,.5f)&&charge==1);
    assert(mw_player_charge_gamebreaker(&charge,-2)&&charge==0);
    assert(!mw_player_charge_gamebreaker(&charge,NAN)&&charge==0);
    float sine=99,cosine=99;assert(mw_player_source_sincos(-0.f,&sine,&cosine));
    assert(signbit(sine)&&cosine==1);
    assert(!mw_player_source_sincos(NAN,&sine,&cosine)&&signbit(sine)&&cosine==1);
    assert(isnan(mw_player_source_sine(INFINITY)));
    assert(mw_player_source_sincos(377,&sine,&cosine)&&isfinite(sine)&&isfinite(cosine));
    float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
    MwPhysicsContactVector directions[4];assert(mw_player_steer_directions(identity,0,1.5f,2.7f,directions));
    for(unsigned n=0;n<4;n++)assert(directions[n].x==0&&directions[n].y==0&&directions[n].z==1);
    uint32_t random_word=20051113;
    for(unsigned n=0;n<4096;n++){
        random_word^=random_word<<13;random_word^=random_word>>17;random_word^=random_word<<5;
        float angle;memcpy(&angle,&random_word,4);if(!isfinite(angle)||fabsf(angle)>400)continue;
        assert(mw_player_source_sincos(angle,&sine,&cosine));
        assert(isfinite(sine)&&isfinite(cosine)&&fabsf(sine*sine+cosine*cosine-1)<1e-6f);
    }
    MwPlayerCollisionState collision={0};
    MwPlayerCollisionInput hit={.flags=0x40000000,.collision_body_present=true,.position={0,0,3},.normal={0,0,-1},
        .impulse_a=25,.body_forward={0,0,1},.body_right={1,0,0},.body_dimension={1,1,2},.signed_speed=-1,.source_time=123};
    assert(mw_player_collision_event(&collision,&hit)&&collision.collision_timer==.5f&&collision.wall_nose_turn==-1);
    MwPlayerWallSteeringInput wall={.steering=-1,.throttle=1,.gear=2,.contact_count=4};memcpy(wall.body_matrix,identity,sizeof(identity));
    MwPlayerWallSteeringOutput wall_commands;
    assert(mw_player_wall_steering(&collision,&wall,&wall_commands)&&wall_commands.count==1);
    assert(wall_commands.angular_velocity_world[0][1]==-.125f);
    assert(mw_player_collision_begin(&collision,.1f)&&collision.collision_timer==.4f);
    mw_player_collision_end(&collision);assert(collision.wall_nose_turn==0&&collision.wall_side_turn==0);
    hit.flags=0x60000000;assert(mw_player_collision_event(&collision,&hit)&&collision.last_ground_time==123);
    collision.wall_nose_turn=1;collision.wall_side_turn=1;wall.steering=1;wall.gear=0;
    assert(mw_player_wall_steering(&collision,&wall,&wall_commands)&&wall_commands.count==2);
    assert(wall_commands.angular_velocity_world[0][1]==.125f&&wall_commands.angular_velocity_world[1][1]==-.125f);
    MwPlayerCollisionState collision_before=collision;hit.position[0]=NAN;
    assert(!mw_player_collision_event(&collision,&hit)&&!memcmp(&collision,&collision_before,sizeof(collision)));
    puts("Player input: persistent steering, source wheel routing, burnout, drifting torque, YAW_CONTROL and rollback passed");
}
