#include "mw_original_camera_tuning.h"
#include <assert.h>
#include <math.h>
#include <string.h>
int main(void)
{
    MwOriginalCameraTuning lower={0},upper={0},out={0};
    for(unsigned i=0;i<4;++i){lower.scalar[i]=2;upper.scalar[i]=6;}
    for(unsigned i=0;i<10;++i)for(unsigned j=0;j<4;++j){lower.vector[i][j]=2;upper.vector[i][j]=6;out.vector[i][j]=123;}
    assert(mw_original_camera_tuning_blend(&lower,&upper,.25f,&out));
    assert(out.scalar[0]==3 && out.vector[9][2]==3 && out.vector[9][3]==123);
    assert(mw_original_camera_tuning_blend(&lower,&upper,.5f,&lower));
    assert(lower.scalar[0]==4 && lower.vector[0][0]==4 && lower.vector[0][3]==2);
    MwOriginalCameraTuning saved=out;upper.vector[9][2]=NAN;
    assert(!mw_original_camera_tuning_blend(&lower,&upper,.5f,&out));
    assert(memcmp(&out,&saved,sizeof out)==0);
    float t=123;assert(mw_original_camera_tuning_parameter(35.5f,&t) && t==.5f);
    assert(mw_original_camera_tuning_parameter(100,&t) && t==1);
    assert(!mw_original_camera_tuning_parameter(-1,&t) && t==1);
    assert(!mw_original_camera_tuning_parameter(INFINITY,&t) && t==1);
    return 0;
}
