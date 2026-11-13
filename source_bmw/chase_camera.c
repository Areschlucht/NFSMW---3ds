#include "chase_camera.h"
#include <math.h>
#include <string.h>
static bool valid(const DriveState *car,float height)
{ return car && isfinite(car->x) && isfinite(car->z) && isfinite(car->heading) && isfinite(car->speed) && isfinite(car->lateral_speed) && isfinite(height); }
static void targets(const DriveState *car,float height,float heading,float eye[3],float at[3])
{
    float speed=fminf(fabsf(car->speed),65),distance=8.5f+speed*.035f,look=4.0f+speed*.035f;
    eye[0]=car->x-sinf(heading)*distance;eye[1]=height+3.8f+speed*.012f;eye[2]=car->z-cosf(heading)*distance;
    at[0]=car->x+sinf(car->heading)*look;at[1]=height+1;at[2]=car->z+cosf(car->heading)*look;
}
bool chase_reset(ChaseCamera *camera,const DriveState *car,float height)
{
    if (!camera || !valid(car,height)) return false;
    memset(camera,0,sizeof(*camera));camera->heading=car->heading;camera->fov=55+fminf(fabsf(car->speed)*.12f,8);
    targets(car,height,camera->heading,camera->eye,camera->target);camera->initialized=true;return true;
}
static void spring(float *position,float *velocity,float target,float rate,float dt,float decay)
{
    /* Exact critically damped spring for a constant target during this step. */
    float delta=*position-target,term=(*velocity+rate*delta)*dt;
    *position=target+(delta+term)*decay;*velocity=(*velocity-rate*term)*decay;
}
bool chase_bind_source(ChaseCamera *camera,const MwChaseAsset *asset,uint32_t ecar,unsigned mode,int view)
{
    if(!camera||!camera->initialized)return false;
    MwChaseSourceConfig c;if(!mw_chase_asset_vehicle(asset,ecar,mode,view,1,&c))return false;
    ChaseCamera next=*camera;next.source=c;next.source_bound=true;memset(&next.source_motion,0,sizeof(next.source_motion));
    *camera=next;return true;
}
bool chase_step(ChaseCamera *camera,const DriveState *car,float height,float seconds)
{
    if (!camera || !valid(car,height) || !isfinite(seconds) || seconds<=0 || seconds>.1f) return false;
    if (!camera->initialized) return chase_reset(camera,car,height);
    if(camera->source_bound){
        float s=sinf(car->heading),c=cosf(car->heading);
        float velocity[3]={s*car->speed+c*car->lateral_speed,0,c*car->speed-s*car->lateral_speed};
        float body[3]={s,0,c},speed=hypotf(car->speed,car->lateral_speed);
        MwChaseSourceMotion motion=camera->source_motion;
        if(!motion.initialized){
            /* Seed from the current camera heading, so binding during a mode
               change does not snap to the new car direction. */
            float old_body[3]={sinf(camera->heading),0,cosf(camera->heading)};
            float still[3]={0,0,0};
            if(!mw_chase_source_reset(&motion,&camera->source,still,old_body,0))return false;
        }
        if(!mw_chase_source_step(&motion,&camera->source,velocity,body,speed,seconds))return false;
        float horizontal=motion.direction[0]*motion.direction[0]+motion.direction[2]*motion.direction[2];
        if(horizontal>1e-12f)camera->heading=atan2f(motion.direction[0],motion.direction[2]);
        camera->source_motion=motion;
    }else{
        float heading=car->heading;
        if (car->speed>3) heading+=atan2f(car->lateral_speed,car->speed)*.65f;
        float delta=remainderf(heading-camera->heading,6.283185307f);
        camera->heading=remainderf(camera->heading+delta*(1-expf(-5*seconds)),6.283185307f);
    }
    float eye[3],at[3];targets(car,height,camera->heading,eye,at);
    /* Velocity feed-forward prevents the follow spring falling meters behind
       at steady speed, while yaw and acceleration still settle smoothly. */
    float s=sinf(car->heading),c=cosf(car->heading);
    float vx=s*car->speed+c*car->lateral_speed,vz=c*car->speed-s*car->lateral_speed;
    eye[0]+=vx*.12f;eye[2]+=vz*.12f;
    at[0]+=vx*.10f;at[2]+=vz*.10f;
    float eye_decay=expf(-12*seconds),target_decay=expf(-18*seconds);
    for (unsigned a=0;a<3;++a) {
        spring(&camera->eye[a],&camera->velocity[a],eye[a],12,seconds,eye_decay);
        spring(&camera->target[a],&camera->target_velocity[a],at[a],18,seconds,target_decay);
    }
    camera->fov+=(55+fminf(fabsf(car->speed)*.12f,8)-camera->fov)*(1-expf(-3*seconds));
    return true;
}
