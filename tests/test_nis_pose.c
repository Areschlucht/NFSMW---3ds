#include "mw_nis_pose.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
int main(void){
    float scale[3]={1,1,1},q[4]={0,0,0,1},t[3]={10,20,30};
    float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
    float rotation[16]={0,1,0,0,-1,0,0,0,0,0,1,0,0,0,0,1};
    float translation[16]={1,0,0,0,0,1,0,0,0,0,1,0,100,200,300,1};float local[16],world[16],bond[16];
    assert(mw_nis_pose_vehicle(scale,q,t,identity,identity,world,bond));
    assert(world[12]==10&&world[13]==20&&world[14]==30);assert(bond[12]==-20&&bond[13]==30&&bond[14]==10);
    assert(mw_nis_pose_vehicle(scale,q,t,rotation,translation,world,bond));
    assert(world[12]==80&&world[13]==210&&world[14]==330);assert(bond[12]==-210&&bond[13]==330&&bond[14]==80);
    assert(mw_nis_pose_ground_height(bond,0,999));assert(bond[13]==330);
    assert(mw_nis_pose_ground_height(bond,1,123.5f));assert(bond[13]==128.5f);
    q[2]=.5f;q[3]=.5f;assert(mw_nis_pose_sqt(scale,q,t,local));assert(local[0]==.5f&&local[1]==.5f&&local[4]==-.5f&&local[5]==.5f&&local[10]==1);
    assert(!mw_nis_pose_vehicle(scale,q,t,identity,identity,NULL,NULL));q[0]=NAN;assert(!mw_nis_pose_sqt(scale,q,t,local));
    assert(!mw_nis_pose_ground_height(bond,1,NAN));
    puts("NIS pose: source matrix order, unnormalized quaternion and terrain height behavior OK");return 0;
}
