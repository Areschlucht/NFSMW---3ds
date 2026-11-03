#include "mw_body_collision_response.h"
#include "mw_body_collision.h"
#include "mw_gekko_math.h"
#include <math.h>
#include <string.h>
static float f32(float v){volatile float f=v;return f;}
static void add(const float a[3],const float b[3],float o[3]){for(unsigned k=0;k<3;k++)o[k]=f32(a[k]+b[k]);}
static void scale(const float a[3],float s,float o[3]){for(unsigned k=0;k<3;k++)o[k]=f32(a[k]*s);}
static float dot(const float a[3],const float b[3]){return fmaf(a[2],b[2],f32(f32(a[0]*b[0])+f32(a[1]*b[1])));}
static void cross(const float a[3],const float b[3],float o[3]){
    float r[3]={fmaf(a[1],b[2],-f32(a[2]*b[1])),-fmaf(a[0],b[2],-f32(a[2]*b[0])),-fmaf(a[1],b[0],-f32(a[0]*b[1]))};memcpy(o,r,sizeof r);
}
static void transform(const float a[3],const float m[16],float o[3]){
    float r[3];for(unsigned k=0;k<3;k++)r[k]=fmaf(m[8+k],a[2],fmaf(m[4+k],a[1],f32(m[k]*a[0])));memcpy(o,r,sizeof r);
}
static void multiply(const float a[16],const float b[16],float o[16]){
    for(unsigned r=0;r<4;r++)for(unsigned c=0;c<4;c++)o[r*4+c]=fmaf(a[r*4+3],b[12+c],fmaf(a[r*4+2],b[8+c],fmaf(a[r*4],b[c],f32(a[r*4+1]*b[4+c]))));
}
static int finite(const float *v,unsigned n){for(unsigned k=0;k<n;k++)if(!isfinite(v[k]))return 0;return 1;}
int mw_body_collision_response(const MwBodyCollisionState *s,const MwBodyCollisionInput *c,MwBodyCollisionResponse *out){
    if(!s||!c||!out||!isfinite(s->mass)||s->mass<=0||!isfinite(s->extra_normal_accumulation)||
       !finite(s->inertia,3)||!finite(s->moment_scale,3)||!finite(s->local_cg,3)||!finite(s->position,3)||
       !finite(s->orientation,16)||!finite(s->velocity,3)||!finite(s->angular_velocity,3)||
       !finite(c->point,3)||!finite(c->normal,3)||!finite(c->friction,2)||c->friction[0]<0||c->friction[1]<0||c->passes<1||c->passes>64)return -1;
    MwBodyCollisionResponse result={0};memcpy(result.velocity,s->velocity,12);memcpy(result.angular_velocity,s->angular_velocity,12);
    float n[3],lever[3],center[3],inverse_mass=f32(1.0f/s->mass),diagonal[16]={0},tmp[16],transpose[16],inverse[16];
    float length=mw_gekko_sqrt_newton1(dot(c->normal,c->normal));if(!isfinite(length))return -1;
    memcpy(n,c->normal,12);if(length!=0)scale(n,f32(1.0f/length),n);
    transform(s->local_cg,s->orientation,center);add(s->position,center,center);
    for(unsigned k=0;k<3;k++){
        lever[k]=f32(c->point[k]-center[k]);float inertia=f32(s->inertia[k]*s->moment_scale[k]);
        diagonal[k*5]=inertia>1.0e-6f?f32(1.0f/inertia):inertia;
    }
    diagonal[15]=1;
    for(unsigned r=0;r<4;r++)for(unsigned col=0;col<4;col++)transpose[r*4+col]=s->orientation[col*4+r];
    multiply(diagonal,s->orientation,tmp);multiply(transpose,tmp,inverse);
    float working_v[3],working_w[3],sum_v[3]={0},sum_w[3]={0},normal_sum=0;
    memcpy(working_v,s->velocity,12);memcpy(working_w,s->angular_velocity,12);
    for(unsigned i=0;i<c->passes;i++){
        float velocity[3],momentum[3],normal_j[3],tangent_j[3],v_n[3],v_t[3],w_n[3],w_t[3],dv[3],dw[3],extra[3];
        cross(working_w,lever,velocity);add(working_v,velocity,velocity);scale(velocity,s->mass,momentum);
        float component=dot(n,momentum);if(!isfinite(component))return -1;if(component>=0)break;
        scale(n,-component,normal_j);
        int branch=mw_body_collision_tangent_response(c->friction,momentum,n,component,tangent_j);if(branch<0)return -1;
        result.iterations=i+1;
        if(i==0){
            scale(n,dot(velocity,n),result.initial_normal_velocity);
            for(unsigned k=0;k<3;k++)result.initial_tangent_velocity[k]=f32(velocity[k]-result.initial_normal_velocity[k]);
            memcpy(result.initial_friction_impulse,tangent_j,12);result.friction_branch=(unsigned)branch;continue;
        }
        float fraction=f32((float)i/(float)c->passes);scale(normal_j,fraction,normal_j);scale(tangent_j,fraction,tangent_j);
        normal_sum=f32(normal_sum-f32(component*fraction));
        scale(normal_j,inverse_mass,v_n);cross(lever,normal_j,w_n);transform(w_n,inverse,w_n);
        scale(tangent_j,inverse_mass,v_t);cross(lever,tangent_j,w_t);transform(w_t,inverse,w_t);
        add(w_n,w_t,dw);add(v_n,v_t,dv);add(working_v,dv,working_v);add(working_w,dw,working_w);
        scale(v_n,s->extra_normal_accumulation,extra);add(dv,extra,extra);add(sum_v,extra,sum_v);
        scale(w_n,s->extra_normal_accumulation,extra);add(dw,extra,extra);add(sum_w,extra,sum_w);
    }
    if(result.iterations){scale(n,normal_sum,result.normal_impulse);add(s->velocity,sum_v,result.velocity);add(s->angular_velocity,sum_w,result.angular_velocity);}
    if(!finite(result.velocity,3)||!finite(result.angular_velocity,3)||!finite(result.normal_impulse,3))return -1;
    *out=result;return result.iterations?1:0;
}
