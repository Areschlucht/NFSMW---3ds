#include "mw_original_camera_cubic.h"
#include <assert.h>
#include <math.h>
#include <string.h>
int main(void)
{
    MwOriginalCameraCubic s={.target=1,.duration=1,.state=2};
    assert(mw_original_camera_cubic_step(&s,.5f,0,0));
    assert(s.value==.5f && s.derivative==1.5f && s.state==1 && s.progress==.5f);
    assert(s.cubic[0]==-2 && s.cubic[1]==3 && !s.cubic[2] && !s.cubic[3]);
    assert(mw_original_camera_cubic_step(&s,.5f,0,0));
    assert(s.value==1 && s.derivative==0 && s.progress==1 && s.state==1);
    assert(mw_original_camera_cubic_step(&s,.01f,0,0));assert(s.state==0);
    assert(mw_original_camera_cubic_target(&s,0) && s.state==2);
    assert(mw_original_camera_cubic_step(&s,.5f,0,0));assert(s.value==.5f);
    MwOriginalCameraCubic old=s;
    assert(!mw_original_camera_cubic_step(&s,NAN,0,0));assert(!memcmp(&old,&s,sizeof s));
    assert(!mw_original_camera_cubic_target(&s,NAN));assert(!memcmp(&old,&s,sizeof s));
    s=(MwOriginalCameraCubic){.target=2,.duration=0,.state=2};old=s;
    assert(!mw_original_camera_cubic_step(&s,.1f,1,0));assert(!memcmp(&old,&s,sizeof s));
    assert(mw_original_camera_cubic_step(&s,.1f,0,0));assert(s.value==2 && s.progress==1);
    s=(MwOriginalCameraCubic){.target=3,.duration=-1,.state=2};
    assert(mw_original_camera_cubic_step(&s,.1f,0,0));assert(s.value==3 && s.progress==1);
    s=(MwOriginalCameraCubic){.target=1,.duration=1,.state=2,.mode=1};
    assert(mw_original_camera_cubic_step(&s,.2f,0,0));assert(s.state==2 && s.progress==.2f);
    float previous=s.value;assert(mw_original_camera_cubic_step(&s,.2f,0,0));
    assert(s.progress==.2f && s.value>previous);
    assert(!mw_original_camera_cubic_step(NULL,.1f,0,0));
    return 0;
}
