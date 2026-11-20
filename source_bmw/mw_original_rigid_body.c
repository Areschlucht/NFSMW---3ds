#include "mw_original_rigid_body.h"
#include "mw_gekko_math.h"
#include <math.h>
#include <string.h>

static bool finite_vector(const float *p,unsigned n)
{for(unsigned i=0;i<n;i++)if(!isfinite(p[i]))return false;return true;}
static bool valid(const MwOriginalRigidBody *s)
{
    return s&&s->status<=2&&finite_vector(s->quaternion,4)&&finite_vector(s->position,3)&&
        finite_vector(s->velocity,3)&&finite_vector(s->angular_velocity,3)&&finite_vector(s->orientation,16)&&
        finite_vector(s->world_inverse_inertia,16)&&finite_vector(s->force,3)&&finite_vector(s->torque,3)&&
        finite_vector(s->local_cg,3)&&finite_vector(s->inertia,3)&&isfinite(s->inverse_mass)&&s->inverse_mass>=0;
}
static float mul_add_separate(float a,float b,float c){float p=a*b;return p+c;}
static float clamp_source(float x,float hi){return x>hi?hi:x < -hi?-hi:x;}
static void transform(const float p[3],const float m[16],float out[3])
{
    float r[3];for(unsigned i=0;i<3;i++){float x=p[0]*m[i];x=fmaf(p[1],m[4+i],x);r[i]=fmaf(p[2],m[8+i],x);}memcpy(out,r,sizeof(r));
}
static void multiply(const float a[16],const float b[16],float out[16])
{
    float r[16];for(unsigned row=0;row<4;row++)for(unsigned col=0;col<4;col++){
        float x=a[row*4+1]*b[4+col];x=fmaf(a[row*4],b[col],x);
        x=fmaf(a[row*4+2],b[8+col],x);r[row*4+col]=fmaf(a[row*4+3],b[12+col],x);
    }memcpy(out,r,sizeof(r));
}
static void quaternion_matrix(const float q[4],float m[16])
{
    float x=q[0],y=q[1],z=q[2],w=q[3];
    float xx=x*x,yy=y*y,zz=z*z,zw=z*w,xw=x*w,xy=x*y,yw=y*w,xz=x*z,yz=y*z;
    xx=xx+xx;yy=yy+yy;zz=zz+zz;xy=xy+xy;xz=xz+xz;xw=xw+xw;yz=yz+yz;yw=yw+yw;zw=zw+zw;
    memset(m,0,16*sizeof(*m));m[15]=1;
    m[0]=1-(yy+zz);m[1]=xy+zw;m[2]=xz-yw;
    m[4]=xy-zw;m[5]=1-(xx+zz);m[6]=yz+xw;
    m[8]=xz+yw;m[9]=yz-xw;m[10]=1-(xx+yy);
}
bool mw_original_rigid_body_set_orientation(MwOriginalRigidBody *state,const float m[16])
{
    if(!valid(state)||!m||!finite_vector(m,16))return false;
    MwOriginalRigidBody s=*state;float *q=s.quaternion;
    float xy=m[0]+m[5],trace=xy+m[10],root,scale;
    if(trace>0){
        root=mw_gekko_sqrt_newton1(trace+1);scale=.5f/root;
        q[3]=root*.5f;q[0]=(m[6]-m[9])*scale;
        q[1]=(m[8]-m[2])*scale;q[2]=(m[1]-m[4])*scale;
    }else{
        unsigned largest=m[5]>m[0]?5:0;
        if(m[10]>m[largest]){
            root=mw_gekko_sqrt_newton1((m[10]-xy)+1);scale=root==0?root:.5f/root;
            q[2]=root*.5f;q[3]=(m[1]-m[4])*scale;
            q[0]=(m[8]+m[2])*scale;q[1]=(m[9]+m[6])*scale;
        }else if(largest){
            root=mw_gekko_sqrt_newton1((m[5]-(m[10]+m[0]))+1);scale=root==0?root:.5f/root;
            q[1]=root*.5f;q[3]=(m[8]-m[2])*scale;
            q[2]=(m[6]+m[9])*scale;q[0]=(m[4]+m[1])*scale;
        }else{
            root=mw_gekko_sqrt_newton1((m[0]-(m[5]+m[10]))+1);scale=root==0?root:.5f/root;
            q[0]=root*.5f;q[3]=(m[6]-m[9])*scale;
            q[1]=(m[1]+m[4])*scale;q[2]=(m[2]+m[8])*scale;
        }
    }
    memcpy(s.orientation,m,sizeof(s.orientation));
    float diagonal[16]={0},transpose[16],product[16];diagonal[15]=1;
    for(unsigned i=0;i<3;i++)diagonal[i*5]=s.inertia[i]>1e-6f?1/s.inertia[i]:s.inertia[i];
    for(unsigned i=0;i<4;i++)for(unsigned j=0;j<4;j++)transpose[i*4+j]=m[j*4+i];
    multiply(diagonal,m,product);multiply(transpose,product,s.world_inverse_inertia);
    if(!valid(&s))return false;
    *state=s;return true;
}
bool mw_original_rigid_body_parameters(float mass,const int16_t extent[3],
    const float tensor[3],MwOriginalRigidBodyParameters *out)
{
    if(!extent||!tensor||!out||!isfinite(mass)||mass<=0||!finite_vector(tensor,3))return false;
    MwOriginalRigidBodyParameters p={0};p.mass=mass;p.inverse_mass=1/mass;
    float squared[3];
    for(unsigned i=0;i<3;i++){
        if(extent[i]<=0||tensor[i]<=0)return false;
        p.halfextent[i]=(float)extent[i]*0.0010000000474974513f;
        float side=p.halfextent[i]+p.halfextent[i];squared[i]=side*side;
    }
    for(unsigned i=0;i<3;i++){
        /* 80278BC0: additions then 1/12, then mass, then TENSOR_SCALE.
           No factor of two and no generic-prop extent clamp. */
        float x=squared[(i+1)%3]+squared[(i+2)%3];
        x=x*0.0833333358168602f;x=x*mass;p.inertia[i]=x*tensor[i];
    }
    if(!isfinite(p.inverse_mass)||!finite_vector(p.inertia,3))return false;
    *out=p;return true;
}
bool mw_original_rigid_body_integrate(MwOriginalRigidBody *state,float dt)
{
    if(!valid(state)||!isfinite(dt)||dt<0)return false;
    MwOriginalRigidBody s=*state;
    if(s.status){memset(s.velocity,0,sizeof(s.velocity));memset(s.angular_velocity,0,sizeof(s.angular_velocity));*state=s;return true;}
    float old_cg[3],new_cg[3];transform(s.local_cg,s.orientation,old_cg);
    float scale=dt*s.inverse_mass;
    for(unsigned i=0;i<3;i++)s.velocity[i]=mul_add_separate(s.force[i],scale,s.velocity[i]);
    for(unsigned i=0;i<3;i++)s.torque[i]=s.torque[i]*dt;
    for(unsigned i=0;i<3;i++)s.position[i]=mul_add_separate(s.velocity[i],dt,s.position[i]);
    transform(s.torque,s.world_inverse_inertia,s.torque);
    for(unsigned i=0;i<3;i++)s.angular_velocity[i]=s.angular_velocity[i]+s.torque[i];
    for(unsigned i=0;i<3;i++)s.velocity[i]=clamp_source(s.velocity[i],300);
    for(unsigned i=0;i<3;i++)s.angular_velocity[i]=clamp_source(s.angular_velocity[i],30);
    float speed2=s.angular_velocity[0]*s.angular_velocity[0];speed2=speed2+s.angular_velocity[1]*s.angular_velocity[1];
    speed2=fmaf(s.angular_velocity[2],s.angular_velocity[2],speed2);
    if(speed2!=0){
        float ax=s.angular_velocity[0]*dt,ay=s.angular_velocity[1]*dt,az=s.angular_velocity[2]*dt;
        const float *q=s.quaternion;float derivative[4];
        derivative[0]=fmaf(ax,q[3],fmaf(ay,q[2],-(az*q[1])));
        derivative[1]=fmaf(ay,q[3],fmaf(az,q[0],-(ax*q[2])));
        derivative[2]=fmaf(az,q[3],fmaf(ax,q[1],-(ay*q[0])));
        float w=-(ax*q[0]);w=w-ay*q[1];derivative[3]=w-az*q[2];
        for(unsigned i=0;i<4;i++)s.quaternion[i]=mul_add_separate(derivative[i],.5f,s.quaternion[i]);
        float a=s.quaternion[0]*s.quaternion[0],b=s.quaternion[1]*s.quaternion[1];
        a=fmaf(s.quaternion[2],s.quaternion[2],a);b=fmaf(s.quaternion[3],s.quaternion[3],b);
        float norm=sqrtf(a+b);if(!(norm>0)||!isfinite(norm))return false;
        float inverse=1/norm;for(unsigned i=0;i<4;i++)s.quaternion[i]=s.quaternion[i]*inverse;
        quaternion_matrix(s.quaternion,s.orientation);
    }
    float diagonal[16]={0},transpose[16],product[16];diagonal[15]=1;
    for(unsigned i=0;i<3;i++)diagonal[i*5]=s.inertia[i]>1e-6f?1/s.inertia[i]:s.inertia[i];
    for(unsigned i=0;i<4;i++)for(unsigned j=0;j<4;j++)transpose[i*4+j]=s.orientation[j*4+i];
    multiply(diagonal,s.orientation,product);multiply(transpose,product,s.world_inverse_inertia);
    transform(s.local_cg,s.orientation,new_cg);
    for(unsigned i=0;i<3;i++)s.position[i]=s.position[i]+(old_cg[i]-new_cg[i]);
    if(!valid(&s))return false;
    *state=s;return true;
}
bool mw_original_rigid_body_add_force(MwOriginalRigidBody *state,const float force[3],const float point[3],bool *wake)
{
    if(!valid(state)||!force||!point||!finite_vector(force,3)||!finite_vector(point,3))return false;
    MwOriginalRigidBody s=*state;bool notify=false;
    if(s.status!=2){
        s.status=0;s.flags|=0x40u;notify=!!(s.flags&2u);s.flags&=~2u;
        float center[3],lever[3];transform(s.local_cg,s.orientation,center);
        for(unsigned i=0;i<3;i++){center[i]=center[i]+s.position[i];lever[i]=point[i]-center[i];}
        /* Original80193010 scalar multiply followed by fused subtraction. */
        float moment[3]={fmaf(lever[1],force[2],-(lever[2]*force[1])),
            -fmaf(lever[0],force[2],-(lever[2]*force[0])),-fmaf(lever[1],force[0],-(lever[0]*force[1]))};
        for(unsigned i=0;i<3;i++){s.torque[i]=s.torque[i]+moment[i];s.force[i]=s.force[i]+force[i];}
    }
    if(!valid(&s))return false;
    *state=s;if(wake)*wake=notify;return true;
}

bool mw_original_rigid_body_add_torque(MwOriginalRigidBody *state,const float torque[3],bool *wake)
{
    if(!valid(state)||!torque||!finite_vector(torque,3))return false;
    MwOriginalRigidBody s=*state;bool notify=false;
    if(s.status!=2){
        s.status=0;s.flags|=0x40u;notify=!!(s.flags&2u);s.flags&=~2u;
        for(unsigned i=0;i<3;i++)s.torque[i]=s.torque[i]+torque[i];
    }
    if(!valid(&s))return false;
    *state=s;if(wake)*wake=notify;return true;
}

bool mw_original_rigid_body_add_wrench(MwOriginalRigidBody *state,const float force[3],
    const float torque[3],bool *wake)
{
    if(!valid(state)||!force||!torque||!finite_vector(force,3)||!finite_vector(torque,3))return false;
    MwOriginalRigidBody s=*state;bool notify=false;
    if(s.status!=2){
        s.status=0;s.flags|=0x40u;notify=!!(s.flags&2u);s.flags&=~2u;
        for(unsigned i=0;i<3;i++)s.force[i]=s.force[i]+force[i];
        for(unsigned i=0;i<3;i++)s.torque[i]=s.torque[i]+torque[i];
    }
    if(!valid(&s))return false;
    *state=s;if(wake)*wake=notify;return true;
}
bool mw_original_rigid_body_raise_position(MwOriginalRigidBody *state,float amount)
{
    if(!valid(state)||!isfinite(amount))return false;
    float y=state->position[1]+amount;if(!isfinite(y))return false;
    state->position[1]=y;return true;
}
