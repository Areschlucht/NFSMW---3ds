#include "mw_nis_pose.h"
#include <math.h>
#include <string.h>
static int finite_values(const float*p,unsigned n){unsigned i;if(!p)return 0;for(i=0;i<n;i++)if(!isfinite(p[i]))return 0;return 1;}
static void multiply(float out[16],const float a[16],const float b[16]){
    float r[16];unsigned i,j;for(i=0;i<4;i++)for(j=0;j<4;j++){
        float v=a[4*i]*b[j];v=fmaf(b[4+j],a[4*i+1],v);v=fmaf(b[8+j],a[4*i+2],v);v=fmaf(b[12+j],a[4*i+3],v);r[4*i+j]=v;
    }memcpy(out,r,sizeof(r));
}
int mw_nis_pose_sqt(const float scale[3],const float q[4],const float t[3],float out[16]){
    float twice_y,twice_x,twice_z,xx,yy,zz,wz,xz,wx,yz,wy,xy,xx_yy,xx_zz,yy_zz;
    if(!out||!finite_values(scale,3)||!finite_values(q,4)||!finite_values(t,3))return 0;
    twice_y=q[1]+q[1];twice_x=q[0]+q[0];twice_z=q[2]+q[2];
    xx=q[0]*twice_x;yy=q[1]*twice_y;zz=q[2]*twice_z;wz=q[3]*twice_z;
    xx_yy=xx+yy;xz=q[0]*twice_z;wx=q[3]*twice_x;yz=q[1]*twice_z;
    xx_zz=xx+zz;wy=q[3]*twice_y;xy=q[0]*twice_y;yy_zz=yy+zz;
    out[0]=scale[0]*(1.0f-yy_zz);out[1]=scale[0]*(xy+wz);out[2]=scale[0]*(xz-wy);out[3]=0;
    out[4]=scale[1]*(xy-wz);out[5]=scale[1]*(1.0f-xx_zz);out[6]=scale[1]*(yz+wx);out[7]=0;
    out[8]=scale[2]*(xz+wy);out[9]=scale[2]*(yz-wx);out[10]=scale[2]*(1.0f-xx_yy);out[11]=0;
    out[12]=t[0];out[13]=t[1];out[14]=t[2];out[15]=1;
    return finite_values(out,16);
}
int mw_nis_pose_world(const float local[16],const float rotation[16],const float translation[16],float source[16],float bond[16]){
    const float root[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};float world[16],b[16];
    if((!source&&!bond)||!finite_values(local,16)||!finite_values(rotation,16)||!finite_values(translation,16))return 0;
    /* Original ROOT bone0 is identity; bone1 still passes through the parent's
     * exact matrix multiply, preserving source arithmetic order/sign behavior. */
    multiply(world,local,root);multiply(world,world,rotation);multiply(world,world,translation);
    if(!finite_values(world,16))return 0;
    b[0]=world[5];b[1]=-world[6];b[2]=-world[4];b[3]=world[7];
    b[4]=-world[9];b[5]=world[10];b[6]=world[8];b[7]=world[11];
    b[8]=-world[1];b[9]=world[2];b[10]=world[0];b[11]=world[3];
    b[12]=-world[13];b[13]=world[14];b[14]=world[12];b[15]=world[15];
    if(source)memcpy(source,world,sizeof(world));
    if(bond)memcpy(bond,b,sizeof(b));
    return 1;
}
int mw_nis_pose_vehicle(const float scale[3],const float q[4],const float t[3],const float rotation[16],const float translation[16],float source[16],float bond[16]){
    float local[16];return mw_nis_pose_sqt(scale,q,t,local)&&mw_nis_pose_world(local,rotation,translation,source,bond);
}

int mw_nis_pose_ground_height(float bond[16],int hit,float world_height){
    if(!bond||!finite_values(bond,16)|| (hit&&!isfinite(world_height)))return 0;
    if(hit)bond[13]=world_height+5.0f;
    return 1;
}
