#include "road_pose.h"
#include <math.h>
#include <string.h>
static float limit(float x) { return fmaxf(-.5f,fminf(.5f,x)); }
static bool solve(float a[3][4],float result[3])
{
    for (unsigned col=0;col<3;++col) {
        unsigned pivot=col;
        for (unsigned row=col+1;row<3;++row) if (fabsf(a[row][col])>fabsf(a[pivot][col])) pivot=row;
        if (fabsf(a[pivot][col])<.00001f) return false;
        for (unsigned j=0;j<4;++j) { float v=a[col][j];a[col][j]=a[pivot][j];a[pivot][j]=v; }
        float divisor=a[col][col];for (unsigned j=col;j<4;++j) a[col][j]/=divisor;
        for (unsigned row=0;row<3;++row) if (row!=col) {
            float factor=a[row][col];for (unsigned j=col;j<4;++j) a[row][j]-=factor*a[col][j];
        }
    }
    for (unsigned i=0;i<3;++i) { result[i]=a[i][3];if (!isfinite(result[i])) return false; }
    return true;
}
bool road_pose_sample(const RoadWorld *w,const WheelRig *rig,const DriveState *car,float reference,RoadPose *out)
{
    if (!w || !rig || !car || !out || !isfinite(car->x) || !isfinite(car->z) ||
        !isfinite(car->heading) || !isfinite(reference) || !isfinite(w->car_half_extent) ||
        w->car_half_extent<1 || w->car_half_extent>4) return false;
    RoadPose pose={0};float center_normal[3];
    if (!road_surface(w,car->x,car->z,reference,&pose.height,center_normal)) return false;
    float s=sinf(car->heading),c=cosf(car->heading),equations[3][4]={{0}};
    for (unsigned i=0;i<4;++i) {
        float x=rig->wheels[i].pivot[0]*w->car_half_extent,z=rig->wheels[i].pivot[2]*w->car_half_extent;
        if (!isfinite(x) || !isfinite(z) || fabsf(x)>5 || fabsf(z)>5) return false;
        float y;
        if (!road_height(w,car->x+s*x-c*z,car->z+c*x+s*z,reference,&y)) continue;
        float row[3]={1,x,z};
        for (unsigned a=0;a<3;++a) {
            for (unsigned b=0;b<3;++b) equations[a][b]+=row[a]*row[b];
            equations[a][3]+=row[a]*(y-reference);
        }
        pose.contacts++;
    }
    float forward=-(center_normal[0]*s+center_normal[2]*c)/fmaxf(center_normal[1],.0001f);
    float right=(center_normal[0]*c-center_normal[2]*s)/fmaxf(center_normal[1],.0001f);
    float plane[3];
    if (pose.contacts>=3 && solve(equations,plane)) {
        pose.height=reference+plane[0];forward=plane[1];right=plane[2];
    }
    pose.pitch=limit(atanf(forward));pose.roll=limit(-atanf(right*cosf(pose.pitch)));
    /* R_y(heading-pi/2) R_z(pitch) R_x(roll), matching the renderer. */
    forward=tanf(pose.pitch);right=-tanf(pose.roll)/cosf(pose.pitch);
    float gx=s*forward-c*right,gz=c*forward+s*right,inv=1/sqrtf(gx*gx+1+gz*gz);
    pose.normal[0]=-gx*inv;pose.normal[1]=inv;pose.normal[2]=-gz*inv;
    if (!isfinite(pose.height)) return false;
    *out=pose;return true;
}
