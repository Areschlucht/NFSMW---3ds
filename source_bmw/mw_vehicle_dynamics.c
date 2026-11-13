#include "mw_vehicle_dynamics.h"
#include "mw_physics_tires.h"
#include <math.h>
#include <string.h>
static float f32(float v){volatile float r=v;return r;}
static uint32_t word(const unsigned char *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static float real(const unsigned char *p){uint32_t b=word(p);float f;memcpy(&f,&b,4);return f;}
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned j=0;j<8;j++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
static bool vector(const MwPhysicsContactVector *v){return isfinite(v->x)&&isfinite(v->y)&&isfinite(v->z);}
static bool wheel_valid(const MwPhysicsGroundWheel *w,unsigned index){
    const MwPhysicsContactWheel *t=&w->tire;const MwPhysicsWheelBrakeState *b=&t->brake;
    const float scalars[]={b->radius_m,b->normal_input,b->handbrake_input,b->angular_speed,b->drive_torque,b->accumulated_brake_torque,b->angular_acceleration,t->normal_load,t->lateral_force,t->longitudinal_force,t->lateral_grip_factor,t->grip_factor,t->residual_torque,t->previous_longitudinal_velocity,t->longitudinal_slip,t->traction_factor,t->slip_angle_turns,t->last_lateral_velocity,t->lateral_scale,t->longitudinal_scale,t->slip_budget,t->curve_scale,t->combined_factor,t->coupling_13c,w->compression,w->air_seconds};
    for(unsigned i=0;i<sizeof(scalars)/sizeof(*scalars);i++)if(!isfinite(scalars[i]))return false;
    return t->wheel_index==index&&b->axle==(index>>1)&&b->locked<=1&&b->direction<=2&&b->radius_m>0&&w->compression>=0&&w->air_seconds>=0;
}
bool mw_vehicle_dynamics_params_open(MwVehicleDynamicsParams *out,const void *data,size_t n){
    if(!out||!data||n!=336)return false;
    const unsigned char *p=data;
    if(memcmp(p,"NDP1",4)||word(p+4)!=1||word(p+8)!=n||word(p+12)!=crc(p+16,n-16)||word(p+36)!=128||word(p+40)!=52)return false;
    for(unsigned i=44;i<64;i++)if(p[i])return false;
    static const unsigned char attr[32]={91,105,196,79,252,252,112,19,163,242,73,0,179,54,23,0,43,31,104,242,72,74,145,8,218,165,191,229,215,42,210,12};
    static const unsigned char dol[32]={51,197,234,230,153,248,113,190,172,5,155,105,50,71,92,173,94,159,97,11,178,178,41,142,4,109,4,55,87,185,65,102};
    if(memcmp(p+64,attr,32)||memcmp(p+96,dol,32))return false;
    MwVehicleDynamicsParams s={.physical_key=word(p+16),.tires_key=word(p+20),.brakes_key=word(p+24),.chassis_key=word(p+28),.transmission_key=word(p+32)};
    if(!s.physical_key||!s.tires_key||!s.brakes_key||!s.chassis_key||!s.transmission_key)return false;
    float v[52];for(unsigned i=0;i<52;i++){v[i]=real(p+128+i*4);if(!isfinite(v[i]))return false;}unsigned at=0;
    s.mass=v[at++];if(s.mass<=0)return false;
    for(unsigned i=0;i<2;i++)s.dimensions.section_width_mm[i]=v[at++];
    for(unsigned i=0;i<2;i++)s.dimensions.aspect_ratio_percent[i]=v[at++];
    for(unsigned i=0;i<2;i++)s.dimensions.rim_size_inches[i]=v[at++];
    for(unsigned i=0;i<2;i++){MwPhysicsSuspensionAxle a={v[at],v[at+1],v[at+2],v[at+3],v[at+4],v[at+5],v[at+6],v[at+7],v[at+8]};s.axles[i]=a;at+=9;}
    for(unsigned i=0;i<2;i++)s.contact.static_grip[i]=v[at++];
    for(unsigned i=0;i<2;i++)s.contact.dynamic_grip[i]=v[at++];
    for(unsigned i=0;i<2;i++)s.contact.grip_scale[i]=v[at++];
    for(unsigned i=0;i<2;i++){s.contact.brakes.normal_raw[i]=v[at++];}
    s.contact.brakes.handbrake_raw=v[at++];
    for(unsigned i=0;i<2;i++)s.contact.brakes.lock_multiplier[i]=v[at++];
    s.contact.calibration=(MwPhysicsBrakeCalibration){v[at],v[at+1],v[at+2],v[at+3],v[at+4]};at+=5;
    s.contact.lateral_curves=&mw_physics_original_lateral_curves;
    for(unsigned i=0;i<2;i++){s.track_width[i]=v[at++];}
    s.front_axle=v[at++];s.wheel_base=v[at++];
    for(unsigned i=0;i<2;i++){s.swaybar[i]=v[at++];}
    s.steering=v[at++];
    s.torque_split=v[at++];for(unsigned i=0;i<3;i++)s.differential[i]=v[at++];
    if(at!=52||s.wheel_base<=0||s.track_width[0]<=0||s.track_width[1]<=0||s.torque_split<0||s.torque_split>1||s.contact.calibration.inertia<=0)return false;
    for(unsigned i=0;i<2;i++)if(s.dimensions.section_width_mm[i]<=0||s.dimensions.aspect_ratio_percent[i]<=0||s.dimensions.rim_size_inches[i]<=0||s.axles[i].travel_inches<0||s.axles[i].spring_stiffness<0||s.contact.static_grip[i]<0||s.contact.dynamic_grip[i]<0)return false;
    *out=s;return true;
}
bool mw_vehicle_dynamics_init(MwVehicleDynamicsState *out,const MwVehicleDynamicsParams *p){
    if(!out||!p||!p->physical_key)return false;
    MwVehicleDynamicsState s={.physical_key=p->physical_key};
    for(unsigned i=0;i<4;i++){float radius=f32(mw_physics_tire_diameter_m(&p->dimensions,i<2)*.5f);if(!isfinite(radius)||radius<=0)return false;mw_physics_contact_wheel_init(&s.wheels[i].tire,i,radius);}
    *out=s;return true;
}
bool mw_vehicle_dynamics_steer_fallback(float steering,int mode,float input,float *out){
    if(!out||!isfinite(steering)||!isfinite(input))return false;
    float maximum=mode==1?45:f32(steering*45);
    *out=f32(f32(maximum*input)*.0027777778450399637f);return true;
}
bool mw_vehicle_dynamics_ackermann(float turns,float track,float base,float out[2]){
    if(!out||!isfinite(turns)||!isfinite(track)||!isfinite(base)||track<=0||base<=0||turns<-.5f||turns>1)return false;
    float a=f32(turns*6.2831854820251465f);if(a>3.1415927410125732f)a=f32(a-6.2831854820251465f);
    bool positive=a>=0;float inner=positive?a:-a,denominator=fmaf(track,inner,base),outer=f32(f32(base*inner)/denominator);
    if(!isfinite(outer))return false;
    out[0]=positive?outer:-inner;out[1]=positive?inner:-outer;return true;
}
bool mw_vehicle_dynamics_step(const MwVehicleDynamicsParams *p,const MwVehicleDynamicsInput *in,MwVehicleDynamicsState *state,MwVehicleDynamicsOutput *out,const MwVehicleDynamicsHooks *h){
    if(!p||!in||!state||!out||!h||!h->mechanical||!h->route_inputs||!h->query||state->physical_key!=p->physical_key||!isfinite(p->mass)||p->mass<=0||!isfinite(in->seconds)||in->seconds<=0||!isfinite(in->speed_mps)||in->speed_mps<0||!isfinite(in->body_half_extent_y)||in->body_half_extent_y<0||!isfinite(in->additional_ride_height_inches)||!vector(&in->world_cg_offset)||!vector(&in->linear_velocity)||!vector(&in->angular_velocity))return false;
    for(unsigned i=0;i<16;i++)if(!isfinite(in->body_matrix[i]))return false;
    for(unsigned i=0;i<4;i++)if(!vector(&in->wheel_direction[i])||!wheel_valid(state->wheels+i,i))return false;
    MwVehicleDynamicsState s=*state;MwVehicleDynamicsOutput result={0};MwPhysicsContactScales scales;
    MwPhysicsContactScaleInput si=in->scales;si.speed_mps=in->speed_mps;mw_physics_contact_scales(&si,&scales);
    if(!isfinite(scales.slip_budget)||!isfinite(scales.curve_scale)||!isfinite(scales.grip_factor)||!isfinite(scales.coupling_13c))return false;
    for(unsigned i=0;i<4;i++)mw_physics_contact_prepare(&s.wheels[i].tire,scales.slip_budget,scales.curve_scale,scales.grip_factor,scales.coupling_13c);
    if(!h->mechanical(h->context,in,s.wheels))return false;
    for(unsigned i=0;i<4;i++)if(!wheel_valid(s.wheels+i,i))return false;
    MwPhysicsTransmissionWheel distribution[4];
    for(unsigned i=0;i<4;i++){MwPhysicsContactWheel *w=&s.wheels[i].tire;distribution[i]=(MwPhysicsTransmissionWheel){w->brake.angular_speed,s.wheels[i].compression,w->longitudinal_slip,w->last_lateral_velocity,w->brake.drive_torque,w->grip_factor,w->brake.locked};}
    MwPhysicsTransmissionDistribution drive=in->distribution;drive.torque_split=p->torque_split;memcpy(drive.differential,p->differential,sizeof(drive.differential));
    if(!mw_physics_transmission_distribute(&drive,distribution,mw_physics_contact_angle_turns))return false;
    for(unsigned i=0;i<4;i++){s.wheels[i].tire.brake.drive_torque=distribution[i].drive_torque;s.wheels[i].tire.grip_factor=distribution[i].grip_factor;}
    if(!h->route_inputs(h->context,in,s.wheels))return false;
    for(unsigned i=0;i<4;i++)if(!wheel_valid(s.wheels+i,i))return false;
    float antiroll[4];mw_physics_ground_antiroll(s.wheels,p->swaybar,antiroll);
    mw_physics_contact_mounts(&p->dimensions,p->track_width,p->front_axle,p->wheel_base,in->body_half_extent_y,result.mounts);
    MwPhysicsContactVector up={in->body_matrix[4],in->body_matrix[5],in->body_matrix[6]};
    for(unsigned i=0;i<4;i++){
        mw_physics_contact_point_velocity(in->body_matrix,result.mounts+i,&in->world_cg_offset,&in->linear_velocity,&in->angular_velocity,result.query_point+i,result.point_velocity+i);
        MwVehicleDynamicsQuery q={0};if(!h->query(h->context,i,result.query_point+i,result.point_velocity+i,&q))return false;
        MwPhysicsContactParameters contact=p->contact;
        if(!isfinite(q.surface_lateral_grip)||!isfinite(q.surface_drive_grip)||!isfinite(q.surface_rolling_resistance))return false;
        contact.surface_lateral_grip=q.surface_lateral_grip;contact.surface_drive_grip=q.surface_drive_grip;contact.surface_rolling_resistance=q.surface_rolling_resistance;
        if(q.present){
            if(!vector(&q.normal)||!isfinite(q.relative_plane_w))return false;
            MwPhysicsGroundInput ground={q.normal,in->wheel_direction[i],result.point_velocity[i],up,q.relative_plane_w,in->speed_mps,p->mass,in->seconds,in->additional_ride_height_inches,antiroll[i]};
            if(!mw_physics_ground_wheel_step(s.wheels+i,&ground,p->axles+(i>>1),&contact,result.ground+i,h->suspension_math,h->contact_math))return false;
            float height=f32(f32(p->axles[i>>1].ride_height_inches+in->additional_ride_height_inches)*.0254f);
            mw_physics_contact_force_moment(in->body_matrix,result.mounts+i,s.wheels[i].compression,height,&in->world_cg_offset,&result.ground[i].world_force,result.application_point+i,result.world_moment+i);
        }else{
            if(!mw_physics_contact_free_step(&s.wheels[i].tire,&contact,in->seconds))return false;
            s.wheels[i].compression=0;s.wheels[i].air_seconds=f32(s.wheels[i].air_seconds+in->seconds);
        }
        if(!wheel_valid(s.wheels+i,i)||!vector(&result.ground[i].world_force)||!vector(result.world_moment+i))return false;
    }
    *state=s;*out=result;return true;
}
