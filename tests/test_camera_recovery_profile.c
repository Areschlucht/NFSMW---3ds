#include "mw_original_camera_profile.h"
#include <assert.h>
#include <math.h>
#include <string.h>
int main(void)
{
    MwOriginalCameraProfile p={.angle_degrees={-1.5f,3},.lag={-4.7f,-6.8f},
        .height={1.62f,1.7f},.lateral_offset={0,.25f},.fov_degrees={78,90},
        .stiffness={.5f,.75f},.tilting={1,0}};
    MwOriginalCameraProfileCache a,b;
    assert(mw_original_camera_profile_cache(&p,1,1,&a));
    assert(a.profile_index==0 && a.angle_turns==65263 && a.fov_turns==14199);
    assert(a.height==1.62f && a.lag==-4.7f && a.tilting==1);
    assert(mw_original_camera_profile_cache(&p,3,.5f,&b));
    assert(b.profile_index==1 && b.fov_turns==8192 && b.lag==-13.6f);
    assert(b.height==1.7f && b.lateral_offset==.25f && b.stiffness==.75f && !b.tilting);
    assert(mw_original_camera_profile_cache(&p,1,0,&b));
    assert(!memcmp(&a,&b,sizeof a));
    MwOriginalCameraProfileCache before=b;
    assert(!mw_original_camera_profile_cache(&p,1,NAN,&b));assert(!memcmp(&before,&b,sizeof b));
    p.fov_degrees[0]=INFINITY;assert(!mw_original_camera_profile_cache(&p,1,1,&b));
    p.fov_degrees[0]=1e20f;assert(!mw_original_camera_profile_cache(&p,1,1,&b));
    p.fov_degrees[0]=78;p.tilting[0]=2;assert(!mw_original_camera_profile_cache(&p,1,1,&b));
    assert(!mw_original_camera_profile_cache(NULL,1,1,&b));assert(!mw_original_camera_profile_cache(&p,1,1,NULL));
    assert(mw_original_camera_profile_field(2)==0x0c2da793);
    assert(mw_original_camera_profile_field(3)==0xccf03cb3);
    assert(!mw_original_camera_profile_field(-1) && !mw_original_camera_profile_field(7));
    MwOriginalCameraProjection projection;
    assert(mw_original_camera_projection(14199,640,480,480,.8f,1,1,&projection));
    assert(projection.vertical_fov_degrees==14199*0.0054931640625f);
    assert(projection.aspect==(640.0f*.8f)/480 && projection.viewport_y_factor==1);
    assert(mw_original_camera_projection(16384,400,120,240,1,1,1,&projection));
    assert(projection.vertical_fov_degrees==45 && projection.viewport_y_factor==.5f);
    MwOriginalCameraProjection unchanged=projection;
    assert(!mw_original_camera_projection(0,400,240,240,1,1,1,&projection));
    assert(!memcmp(&unchanged,&projection,sizeof projection));
    assert(!mw_original_camera_projection(32768,400,240,240,1,1,1,&projection));
    assert(!mw_original_camera_projection(16384,400,0,240,1,1,1,&projection));
    assert(!mw_original_camera_projection(16384,400,240,240,NAN,1,1,&projection));
    return 0;
}
