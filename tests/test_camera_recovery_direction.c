#include "mw_original_camera_direction.h"
#include <assert.h>
#include <math.h>
#include <string.h>
int main(void)
{
    float forward[3]={1,0,0},velocity[3]={0,10,0},out[3],weight;
    assert(mw_original_camera_direction_target(velocity,forward,8,out,&weight));
    assert(weight==0 && out[0]==1 && out[1]==0 && out[2]==0);
    assert(mw_original_camera_direction_target(velocity,forward,13,out,&weight));
    assert(weight==1 && fabsf(out[0])<1e-6f && fabsf(out[1]-1)<1e-6f);
    assert(mw_original_camera_direction_target(velocity,forward,10.5f,out,&weight));
    assert(weight==.5f && fabsf(out[0]-.5f)<1e-6f && fabsf(out[1]-.5f)<1e-6f);
    velocity[0]=-20;velocity[1]=0;
    assert(mw_original_camera_direction_target(velocity,forward,20,out,&weight));
    assert(out[0]==1 && out[1]==0 && out[2]==0);
    velocity[0]=0;assert(mw_original_camera_direction_target(velocity,forward,0,out,NULL));
    assert(out[0]==1 && out[1]==0 && out[2]==0);
    float before[3];memcpy(before,out,sizeof out);velocity[2]=NAN;
    assert(!mw_original_camera_direction_target(velocity,forward,20,out,&weight));assert(!memcmp(before,out,sizeof out));
    assert(!mw_original_camera_direction_target(NULL,forward,1,out,&weight));
    assert(!mw_original_camera_direction_target(forward,forward,-1,out,&weight));
    assert(!mw_original_camera_direction_target(forward,forward,1,NULL,&weight));
    return 0;
}
