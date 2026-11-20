#include "mw_drive_camera.h"
#include "mw_original_camera_direction.h"
#include "mw_gekko_math.h"
#include <math.h>
#include <string.h>
_Static_assert(offsetof(MwDriveCameraAnchor,position)==24,"CameraAnchor position ABI");
_Static_assert(offsetof(MwDriveCameraAnchor,matrix)==72,"CameraAnchor matrix ABI");
static bool finite_array(const float*p,unsigned n){for(unsigned i=0;i<n;i++)if(!isfinite(p[i]))return false;return true;}
static float squared(const float*v){float r=v[1]*v[1];r=fmaf(v[0],v[0],r);return fmaf(v[2],v[2],r);}
static void vector_matrix(float*out,const float*m,const float*v){
 float t[3];for(unsigned i=0;i<3;i++){float x=v[1]*m[4+i];x=fmaf(v[0],m[i],x);x=fmaf(v[2],m[8+i],x);t[i]=x;}memcpy(out,t,sizeof(t));
}
static bool normalize(float*out,const float*v){float length=mw_gekko_sqrt_newton2(squared(v));if(!isfinite(length))return false;if(length!=0){float inv=1.0f/length;for(unsigned i=0;i<3;i++)out[i]=v[i]*inv;}else{out[0]=1;out[1]=out[2]=0;}return true;}
static void cross(float*out,const float*a,const float*b){float v[3];v[0]=fmaf(a[1],b[2],-(a[2]*b[1]));v[1]=fmaf(a[2],b[0],-(a[0]*b[2]));v[2]=fmaf(a[0],b[1],-(a[1]*b[0]));memcpy(out,v,sizeof(v));}
static void snap_channel(MwOriginalCameraCubic*c){c->value=c->target;c->derivative=c->target_derivative;c->state=0;}
bool mw_drive_camera_anchor_update(MwDriveCameraAnchor*out,const float m[16],const float v[3],float delta){
 if(!out||!m||!v||!finite_array(m,16)||!finite_array(v,3)||!isfinite(delta)||!finite_array(out->position,3)||!isfinite(out->speed))return false;
 MwDriveCameraAnchor a=*out;float d[3];for(unsigned i=0;i<3;i++)d[i]=out->position[i]-m[12+i];float dist=mw_gekko_sqrt_newton2(squared(d));float old_speed=a.speed;
 memcpy(a.matrix,m,64);memcpy(a.position,m+12,12);memcpy(a.velocity,v,12);a.matrix[12]=a.matrix[13]=a.matrix[14]=0;a.speed=mw_gekko_sqrt_newton2(squared(v));
 if(delta>0&&dist/delta<300){float local[3]={(a.speed-old_speed)/delta,0,0};vector_matrix(a.acceleration,m,local);}else memset(a.acceleration,0,12);
 if(!finite_array(a.acceleration,3)||!isfinite(a.speed))return false;
 *out=a;return true;
}
bool mw_drive_camera_forward(MwDriveCamera*out,const MwDriveCameraAnchor*a,int pov,uint32_t timer,bool snap){
 if(!out||!a||!finite_array(a->velocity,3)||!finite_array(a->matrix,16)||!isfinite(a->speed)||a->speed<0)return false;
 MwDriveCamera s=*out;float target[3];bool outside=pov>=2&&pov<=6;
 if(outside){
  if(!mw_original_camera_direction_target(a->velocity,a->matrix,a->speed,target,NULL))return false;
  int32_t elapsed=(int32_t)(timer-s.last_grounded);float attenuation=(float)elapsed*0.0002500000118743628f;attenuation=attenuation*.5f;attenuation=1.0f-attenuation;
  if(attenuation<0)attenuation=0;
  if(attenuation>1)attenuation=1;
  target[2]=target[2]*attenuation;float rest=1.0f-a->matrix[2]*a->matrix[2];target[2]=target[2]*rest;
 }else memcpy(target,a->matrix,12);
 for(unsigned i=0;i<3;i++){if(!mw_original_camera_cubic_target(&s.forward[i],target[i]))return false;if(snap||!outside)snap_channel(&s.forward[i]);}
 *out=s;return true;
}
bool mw_drive_camera_space(const MwDriveCamera*s,const MwDriveCameraAnchor*a,bool outside,float out[16]){
 if(!s||!a||!out||!finite_array(a->matrix,16)||!finite_array(a->position,3))return false;
 float m[16];if(outside){
  memset(m,0,sizeof(m));m[0]=m[5]=m[10]=m[15]=1;float f[3]={s->forward[0].value,s->forward[1].value,s->forward[2].value};
  if(!finite_array(f,3)||!normalize(m,f))return false;
  cross(m+4,m+8,m);cross(m+8,m,m+4);
 }else{
  memcpy(m,a->matrix,48);if(a->matrix[10]<0)for(unsigned i=4;i<12;i++)m[i]=-m[i];
 }
 memcpy(m+12,a->position,12);m[15]=1;memcpy(out,m,sizeof(m));return true;
}
void mw_drive_camera_source_data(MwDriveCameraSourceData*out){
 if(out)*out=(MwDriveCameraSourceData){.speed_hug={{1,1},{1,1},{1.02f,1},{1.125f,1},{1.2f,1}},.nos_fov_turns=1638};
}
float mw_drive_camera_sine_turns(uint16_t angle){
 float x=(float)angle*9.5873801910784095526e-5f,sign=1;
 if(x>=4.7123889923095703125f)x=x-6.283185482025146484375f;
 else if(x>=1.57079637050628662109375f){sign=-1;x=x-3.1415927410125732421875f;}
 float x2=x*x,x3=x*x2,x5=x3*x2;float value=x-x3*0.16666667163372039794921875f;
 float x7=x5*x2,term=x7*0.000198412701138295233249664306640625f;
 value=fmaf(x5,0.008333333767950534820556640625f,value);float x9=x7*x2;
 value=value-term;return fmaf(x9,2.755731884462875313125550746917724609375e-6f,value)*sign;
}
static float clamp(float f,float lo,float hi){if(f<lo)return lo;if(f>hi)return hi;return f;}
static float lookup(const float *data,unsigned stride,unsigned n,float lo,float hi,float input,unsigned channel,bool scalar){
 float index=(input-lo)*((float)(n-1)/(hi-lo));
 if(!isfinite(index))return index;
 if(index<=-1)return data[channel];
 if(index>=(float)(n-1))return data[(n-1)*stride+channel];
 int whole=(int)index;
 if(whole<0)return data[channel];
 if(whole>=(int)n-1)return data[(n-1)*stride+channel];
 float base=(float)whole;if(base>index)base=base-1;float blend=index-base;
 float lower=data[(unsigned)whole*stride+channel],upper=data[((unsigned)whole+1)*stride+channel];
 return scalar?fmaf(upper,blend,lower*(1-blend)):fmaf(lower,1-blend,upper*blend);
}
bool mw_drive_camera_desired(MwDriveCamera*out,const MwDriveCameraAnchor*a,const MwOriginalCameraProfileCache*p,const MwOriginalCameraTuning*t,const MwDriveCameraSourceData*source,const MwDriveCameraDesiredInput*i,float space[16]){
 if(!out||!a||!p||!t||!source||!i||!space||!finite_array(i->dutch,3)||!finite_array(out->average_acceleration,3)||!finite_array((const float*)t,44)||!finite_array((const float*)source->speed_hug,10))return false;
 MwDriveCamera s=*out;bool outside=i->pov_type>=2&&i->pov_type<=6;
 if(i->touching_ground)s.last_grounded=i->world_timer;
 if(i->under_vehicle)s.last_under_vehicle=i->world_timer;
 if(!mw_drive_camera_forward(&s,a,i->pov_type,i->world_timer,i->snap))return false;
 float m[16];if(!mw_drive_camera_space(&s,a,outside,m))return false;
 float local_accel[3]={0,0,0};if(s.accel_lag){
  for(unsigned axis=0;axis<3;axis++){float v=s.average_acceleration[0]*m[axis*4];v=fmaf(s.average_acceleration[1],m[axis*4+1],v);local_accel[axis]=fmaf(s.average_acceleration[2],m[axis*4+2],v);}
 }
 float eye[3]={p->lag,p->lateral_offset,p->height};
 if(a->top_speed>0)for(unsigned axis=0;axis<2;axis++)eye[axis?2:0]=eye[axis?2:0]*lookup(&source->speed_hug[0][0],2,5,0,a->top_speed,a->speed,axis,false);
 float tangent=mw_drive_camera_sine_turns(p->angle_turns)/mw_drive_camera_sine_turns((uint16_t)(p->angle_turns+0x4000u));
 float look[3]={outside?0:eye[0]+1,0,outside?fmaf(tangent,eye[0],eye[2]):eye[2]-tangent};
 float up[3]={0,0,1};
 for(unsigned axis=0;axis<3;axis++){
  eye[axis]=eye[axis]+clamp(t->vector[3][axis]*local_accel[axis],t->vector[4][axis],t->vector[5][axis]);
  look[axis]=look[axis]+clamp(t->vector[6][axis]*local_accel[axis],t->vector[7][axis],t->vector[8][axis]);
  if(p->tilting)up[axis]=clamp(up[axis]+t->vector[0][axis]*s.average_acceleration[axis],t->vector[1][axis],t->vector[2][axis]);
  if(a->speed>5)up[axis]=up[axis]+i->dutch[axis];
 }
 float normal[3];if(!normalize(normal,up))return false;
 uint16_t fov=p->fov_turns;if(outside&&i->nos_engaged&&a->speed>0)fov=(uint16_t)(fov+source->nos_fov_turns);
 if(!mw_original_camera_cubic_target(&s.fov,(float)fov))return false;
 for(unsigned axis=0;axis<3;axis++){
  if(!mw_original_camera_cubic_target(s.eye+axis,eye[axis])||!mw_original_camera_cubic_target(s.look+axis,look[axis])||!mw_original_camera_cubic_target(s.up+axis,normal[axis]))return false;
  if(i->snap||!outside){snap_channel(s.eye+axis);snap_channel(s.look+axis);snap_channel(s.up+axis);}
 }
 if(i->snap||!outside)snap_channel(&s.fov);
 *out=s;memcpy(space,m,sizeof(m));return true;
}

bool mw_drive_camera_channels(MwDriveCamera*out,const MwDriveCameraAnchor*a,const MwOriginalCameraTuning*t,int pov,float damping,float drift,float delta){
 if(!out||!a||!t||!finite_array(a->acceleration,3)||!finite_array((const float*)t,44)||!isfinite(damping)||!isfinite(drift)||!isfinite(delta)||delta<0||!isfinite(out->ignore_snap_seconds)||!finite_array(out->acceleration_sum,3)||!finite_array(&out->acceleration_samples[0][0],20)||!finite_array(out->impact,2)||!finite_array(out->impact_seconds,2)||out->acceleration_count>5||out->acceleration_cursor>=5)return false;
 MwDriveCamera s=*out;
 if(s.ignore_snap_seconds>0)s.ignore_snap_seconds=s.ignore_snap_seconds-delta;
 float accel[3]={0,0,0};
 static const float curve[5]={-1,-.1f,0,.1f,1};
 if(s.ignore_snap_seconds<=0)for(unsigned axis=0;axis<3;axis++)accel[axis]=lookup(curve,1,5,-30,30,a->acceleration[axis],0,true)*30;
 if(s.acceleration_count<5)s.acceleration_count++;
 for(unsigned axis=0;axis<3;axis++){
  float sum=s.acceleration_sum[axis]-s.acceleration_samples[s.acceleration_cursor][axis];
  sum=sum+accel[axis];s.acceleration_sum[axis]=sum;s.acceleration_samples[s.acceleration_cursor][axis]=accel[axis];
  s.average_acceleration[axis]=sum*(1.0f/(float)s.acceleration_count);
 }
 if(++s.acceleration_cursor>=5)s.acceleration_cursor=0;
 if(fmaxf(fabsf(accel[0]),fabsf(accel[1]))>=24&&damping>0&&damping>s.impact[0]){s.impact[0]=damping;s.impact_seconds[0]=1;}
 if(accel[2]>=24){float amount=clamp((accel[2]-24)*.1666666716337204f,0,1);if(amount>s.impact[1]){s.impact[1]=amount;s.impact_seconds[1]=1;}}
 for(unsigned axis=0;axis<3;axis++){
  s.up[axis].duration=t->scalar[3];s.look[axis].duration=t->scalar[1];
  float duration=t->vector[9][axis]+damping;duration=duration+drift;s.forward[axis].duration=duration;
  s.eye[axis].duration=t->scalar[0];
 }
 s.fov.duration=t->scalar[2];
 /* This order is visible through source shared state: up, FOV, eye, look,
  * forward. Channels are independent but the complete stage retains it. */
 for(unsigned axis=0;axis<3;axis++)if(!mw_original_camera_cubic_step(s.up+axis,delta,0,0))return false;
 if(!mw_original_camera_cubic_step(&s.fov,delta,0,0))return false;
 for(unsigned axis=0;axis<3;axis++)if(!mw_original_camera_cubic_step(s.eye+axis,delta,0,0))return false;
 for(unsigned axis=0;axis<3;axis++)if(!mw_original_camera_cubic_step(s.look+axis,delta,0,0))return false;
 for(unsigned axis=0;axis<3;axis++)if(!mw_original_camera_cubic_step(s.forward+axis,delta,0,0))return false;
 if(!finite_array(s.acceleration_sum,3)||!finite_array(s.average_acceleration,3))return false;
 *out=s;(void)pov;return true;
}
bool mw_drive_camera_placement(MwDriveCamera*out,const MwDriveCameraAnchor*a,int pov,uint32_t timer,bool changing,float delta,const float space[16],MwDriveCameraPlacement*placement){
 if(!out||!a||!placement||!space||!finite_array(space,16)||!finite_array(a->matrix,16)||!isfinite(a->speed)||!isfinite(delta)||delta<0||!finite_array(out->impact,2)||!finite_array(out->impact_seconds,2))return false;
 MwDriveCamera s=*out;MwDriveCameraPlacement result={0};bool outside=pov>=2&&pov<=6;float direction=s.look_back?-1:1;
 result.up[0]=s.up[0].value;result.up[1]=s.up[1].value;result.up[2]=1;
 if(!outside){result.up[0]=a->matrix[8];result.up[1]=a->matrix[9];result.up[2]=a->matrix[10];}
 float eye[3]={direction*s.eye[0].value,direction*s.eye[1].value,s.eye[2].value};
 float look[3]={direction*s.look[0].value,direction*s.look[1].value,s.look[2].value};
 static const float impact_curve[5]={0,.02f,.25f,.99f,0};
 static const float vertical_curve[5]={0,0,0,0,0};
 static const float shift_curve[9]={0,.2f,.13f,-.08f,-.2f,-.13f,-.07f,-.03f,0};
 if(s.impact[0]>0&&s.impact_seconds[0]>0){float amount=s.impact[0]*.25f;amount=lookup(impact_curve,1,5,0,1,s.impact_seconds[0],0,true)*amount;eye[0]=eye[0]*(1-amount);look[0]=look[0]*(amount+1);}
 if(s.impact_seconds[0]>0){s.impact_seconds[0]=s.impact_seconds[0]-delta;if(s.impact_seconds[0]<=0)s.impact[0]=0;}else s.impact[0]=0;
 if(s.impact[1]>0&&s.impact_seconds[1]>0){float amount=s.impact[1]*.25f;amount=lookup(vertical_curve,1,5,0,1,s.impact_seconds[1],0,true)*amount;eye[2]=eye[2]*(1-amount);}
 if(s.impact_seconds[1]>0){s.impact_seconds[1]=s.impact_seconds[1]-delta;if(s.impact_seconds[1]<=0)s.impact[1]=0;}else s.impact[1]=0;
 if(outside){
  float elapsed=(float)(int32_t)(timer-s.last_gear_change)*.0002500000118743628f;
  if(elapsed<1.5f){float curve=lookup(shift_curve,1,9,0,1.5f,elapsed,0,true);float attenuation=clamp(a->speed*.009999999776482582f,0,1);float magnitude=fabsf(eye[0])*.20000000298023224f;curve=curve*magnitude;eye[0]=fmaf(curve,1-attenuation,eye[0]);}
  else if(a->speed>10&&changing)s.last_gear_change=timer;
  float lift=(float)(int32_t)(timer-s.last_under_vehicle)*.0002500000118743628f;lift=lift*1.25f;lift=clamp(1.2000000476837158f-lift,0,1.2000000476837158f);if(lift>1)lift=2-lift;
  eye[2]=fmaf(lift,-.8999999761581421f,eye[2]);result.lifted_under_vehicle=lift>0;
 }
 for(unsigned axis=0;axis<3;axis++){
  float e=eye[0]*space[axis];e=fmaf(eye[1],space[4+axis],e);e=fmaf(eye[2],space[8+axis],e);result.eye[axis]=e+space[12+axis];
  float l=look[0]*space[axis];l=fmaf(look[1],space[4+axis],l);l=fmaf(look[2],space[8+axis],l);result.look[axis]=l+space[12+axis];
  float difference=result.eye[axis]-result.look[axis];result.eye[axis]=result.look[axis]+difference;
 }
 if(!finite_array(result.eye,3)||!finite_array(result.look,3)||!finite_array(result.up,3))return false;
 *out=s;*placement=result;return true;
}
void mw_drive_camera_lens_table(uint16_t table[257]){
 if(!table)return;
 for(unsigned i=0;i<=256;i++)table[i]=(uint16_t)(atan((double)i/256.0)*10430.378350470453+.5);
}
bool mw_drive_camera_fov_turns(float input,const uint16_t table[257],uint16_t*out){
 if(!table||!out||!isfinite(input)||input<=0||input>=32768)return false;
 uint16_t half=(uint16_t)((uint32_t)(int32_t)input>>1);
 float tangent=mw_drive_camera_sine_turns(half)/mw_drive_camera_sine_turns((uint16_t)(half+0x4000u));
 if(!isfinite(tangent)||tangent<0)return false;
 uint16_t angle;
 if(tangent==1)angle=0x2000;
 else{
  float ratio=tangent<1?tangent:1.0f/tangent;uint32_t fixed=(uint32_t)(ratio*65536.0f);
  if(fixed>=65536)return false;
  unsigned index=fixed>>8;int lower=table[index],difference=(int)table[index+1]-lower;
  if(difference<0)return false;
  angle=(uint16_t)(lower+(difference*(int)(fixed&255)>>8));
  if(tangent>1)angle=(uint16_t)(0x4000-angle);
 }
 *out=(uint16_t)(angle*2u);return true;
}
bool mw_drive_camera_look_at(const float eye[3],const float look[3],const float up[3],float output[16]){
 if(!output||!eye||!look||!up||!finite_array(eye,3)||!finite_array(look,3)||!finite_array(up,3))return false;
 float forward[3],vertical[3],side[3];for(unsigned i=0;i<3;i++){forward[i]=look[i]-eye[i];vertical[i]=-up[i];}
 if(!normalize(forward,forward))return false;
 cross(side,vertical,forward);cross(vertical,forward,side);
 if(!normalize(side,side)||!normalize(vertical,vertical))return false;
 float rotation[16]={side[0],vertical[0],forward[0],0,side[1],vertical[1],forward[1],0,side[2],vertical[2],forward[2],0,0,0,0,1};
 float translation[16]={1,0,0,0,0,1,0,0,0,0,1,0,-eye[0],-eye[1],-eye[2],1};float matrix[16];
 for(unsigned row=0;row<4;row++)for(unsigned col=0;col<4;col++){
  float value=translation[row*4]*rotation[col];value=fmaf(rotation[4+col],translation[row*4+1],value);value=fmaf(rotation[8+col],translation[row*4+2],value);matrix[row*4+col]=fmaf(rotation[12+col],translation[row*4+3],value);
 }
 if(!finite_array(matrix,16))return false;
 memcpy(output,matrix,sizeof(matrix));return true;
}
