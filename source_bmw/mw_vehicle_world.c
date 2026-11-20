#include "mw_vehicle_world.h"
#include <math.h>
#include <stddef.h>
#include <string.h>
_Static_assert(sizeof(MwVehicleWorldGeometry)==176,"original geometry size");
_Static_assert(offsetof(MwVehicleWorldGeometry,dimension)==0x90,"original geometry dimension");
_Static_assert(offsetof(MwVehicleWorldGeometry,delta)==0xa0,"original geometry delta");
static bool finite_vec(const float *p,unsigned n)
{for(unsigned i=0;i<n;i++)if(!isfinite(p[i]))return false;return true;}
static void position(const MwOriginalRigidBody *s,const float offset[3],float out[3])
{
    for(unsigned i=0;i<3;i++){
        float x=offset[0]*s->orientation[i];x=fmaf(offset[1],s->orientation[4+i],x);
        x=fmaf(offset[2],s->orientation[8+i],x);out[i]=x+s->position[i];
    }
}
static void matrix(const float q[4],float m[3][4])
{
    float x=q[0],y=q[1],z=q[2],w=q[3];
    float xx=x*x,yy=y*y,zz=z*z,xy=x*y,xz=x*z,yz=y*z,xw=x*w,yw=y*w,zw=z*w;
    xx+=xx;yy+=yy;zz+=zz;xy+=xy;xz+=xz;yz+=yz;xw+=xw;yw+=yw;zw+=zw;
    m[0][0]=1-(yy+zz);m[0][1]=xy+zw;m[0][2]=xz-yw;
    m[1][0]=xy-zw;m[1][1]=1-(xx+zz);m[1][2]=yz+xw;
    m[2][0]=xz+yw;m[2][1]=yz-xw;m[2][2]=1-(xx+yy);
}
int mw_vehicle_world_actor_open(const void *data,size_t bytes,uint32_t model,
    const float pad[3],MwVehicleWorldActor *out)
{
    if(!out||!pad||!finite_vec(pad,3))return MW_BODY_SHAPE_INVALID;
    MwVehicleWorldActor a;memset(&a,0,sizeof(a));
    int r=mw_body_collision_compound_open(data,bytes,model,&a.compound);if(r<0)return r;
    size_t count=0;r=mw_body_collision_static_children(&a.compound,0,pad,a.primitives,MW_VEHICLE_WORLD_MAX_PRIMITIVES,&count);
    if(r<0)return r;
    if(count>MW_VEHICLE_WORLD_MAX_PRIMITIVES)return MW_BODY_SHAPE_CAPACITY;
    a.count=(unsigned)count;*out=a;return 0;
}
bool mw_vehicle_world_prepare(MwVehicleWorldActor *actor,const MwOriginalRigidBody *s)
{
    if(!actor||!s||actor->count>MW_VEHICLE_WORLD_MAX_PRIMITIVES||!finite_vec(s->position,3)||!finite_vec(s->orientation,16))return false;
    float p[MW_VEHICLE_WORLD_MAX_PRIMITIVES][3];
    for(unsigned i=0;i<actor->count;i++){
        position(s,actor->primitives[i].center,p[i]);if(!finite_vec(p[i],3))return false;
    }
    memcpy(actor->previous_position,p,actor->count*sizeof(p[0]));actor->prepared=true;return true;
}
bool mw_vehicle_world_geometry(const MwVehicleWorldActor *actor,unsigned index,
    const MwOriginalRigidBody *s,MwVehicleWorldGeometry *out)
{
    if(!actor||!s||!out||!actor->prepared||index>=actor->count||index>=MW_VEHICLE_WORLD_MAX_PRIMITIVES||
       !finite_vec(s->position,3)||!finite_vec(s->orientation,16)||!finite_vec(s->quaternion,4))return false;
    const MwBodyCollisionShape *p=&actor->primitives[index];if(p->kind!=1&&p->kind!=2)return false;
    MwVehicleWorldGeometry g;memset(&g,0,sizeof(g));g.shape=p->kind;g.overlap=-100000;
    position(s,p->center,g.position);
    for(unsigned i=0;i<3;i++)g.delta[i]=g.position[i]-actor->previous_position[index][i];
    if(p->kind==2){
        g.position[3]=1;
        for(unsigned i=0;i<3;i++){
            g.normal[i][3]=1;g.extent[i][3]=1;
            g.dimension[i]=fmaxf(p->half_extents[0],fmaxf(p->half_extents[1],p->half_extents[2]));
        }
    }else{
        const float *a=s->quaternion,*b=p->quaternion;float q[4];
        q[0]=fmaf(a[0],b[3],fmaf(a[3],b[0],fmaf(a[1],b[2],-(a[2]*b[1]))));
        q[1]=fmaf(a[1],b[3],fmaf(a[3],b[1],fmaf(a[2],b[0],-(a[0]*b[2]))));
        q[2]=fmaf(a[2],b[3],fmaf(a[3],b[2],fmaf(a[0],b[1],-(a[1]*b[0]))));
        q[3]=fmaf(a[3],b[3],-(a[0]*b[0]));q[3]=q[3]-a[1]*b[1];q[3]=q[3]-a[2]*b[2];
        matrix(q,g.normal);
        for(unsigned i=0;i<3;i++){
            g.dimension[i]=p->half_extents[i];
            for(unsigned j=0;j<3;j++)g.extent[i][j]=g.normal[i][j]*g.dimension[i];
        }
    }
    if(!finite_vec(g.position,4)||!finite_vec(&g.normal[0][0],12)||!finite_vec(&g.extent[0][0],12)||!finite_vec(g.delta,3))return false;
    *out=g;return true;
}
