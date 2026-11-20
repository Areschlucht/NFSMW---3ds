#include "mw_ginsu.h"
#include <math.h>
#include <string.h>
static uint32_t u32(const unsigned char*p){return p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static float real(const unsigned char*p){uint32_t v=u32(p);float x;memcpy(&x,&v,4);return x;}
static float f32(float x){volatile float y=x;return y;}
static int32_t pos(const unsigned char*p,uint32_t i){return (int32_t)u32(p+i*4);}
static int32_t nearest(float x){return (int32_t)(x>0?f32(x+.5f):f32(x-.5f));}
bool mw_ginsu_bank_open(MwGinsuBank*out,const void*data,size_t bytes){
 if(!out||!data||bytes<48)return false;
 const unsigned char*p=data;MwGinsuBank b={0};
 if(memcmp(p,"Gnsu20\0\0",8))return false;
 b.data=p;b.bytes=bytes;b.min_frequency=real(p+8);b.max_frequency=real(p+12);b.segments=u32(p+16);b.cycles=u32(p+20);b.sample_count=u32(p+24);b.rate=u32(p+28);
 if(!isfinite(b.min_frequency)||!isfinite(b.max_frequency)||b.min_frequency<0||b.max_frequency<=b.min_frequency||!b.segments||b.segments>4096||b.cycles<2||b.cycles>65536||b.sample_count<32||b.sample_count>16777216||b.rate<8000||b.rate>48000)return false;
 size_t at=32+((size_t)b.segments+b.cycles+2)*4,encoded=((size_t)b.sample_count+31)/32*19;
 if(at>bytes||encoded>bytes-at)return false;
 b.frequency_positions=p+32;b.cycle_positions=p+32+(b.segments+1)*4;b.samples=p+at;b.min_period=(float)b.sample_count;
 for(uint32_t i=0;i<=b.segments;i++){int32_t n=pos(b.frequency_positions,i);if(n<0||(uint32_t)n>=b.sample_count)return false;}
 for(uint32_t i=0;i<=b.cycles;i++){int32_t n=pos(b.cycle_positions,i);if(n<0||(uint32_t)n>=b.sample_count)return false;if(i){int32_t delta=n-pos(b.cycle_positions,i-1);if(delta<=0)return false;if((float)delta<b.min_period)b.min_period=(float)delta;}}
 *out=b;return true;
}
static int32_t interpolate(const unsigned char*p,uint32_t i,float f){float a=(float)pos(p,i),delta=(float)(pos(p,i+1)-pos(p,i));return nearest(fmaf(f,delta,a));}
bool mw_ginsu_frequency_sample(const MwGinsuBank*b,float f,int32_t*out){
 if(!b||!b->data||!out||!isfinite(f))return false;
 if(f<=b->min_frequency){*out=pos(b->frequency_positions,0);return true;}if(f>=b->max_frequency){*out=pos(b->frequency_positions,b->segments);return true;}
 float x=f32(f32((float)b->segments*f32(f-b->min_frequency))/f32(b->max_frequency-b->min_frequency));uint32_t i=(uint32_t)floorf(x);if(i>=b->segments){*out=pos(b->frequency_positions,b->segments);return true;}
 *out=interpolate(b->frequency_positions,i,f32(x-(float)i));return true;
}
bool mw_ginsu_cycle_sample(const MwGinsuBank*b,float c,int32_t*out){
 if(!b||!b->data||!out||!isfinite(c))return false;
 if(c<=0){*out=pos(b->cycle_positions,0);return true;}if(c>=(float)b->cycles){*out=pos(b->cycle_positions,b->cycles);return true;}
 uint32_t i=(uint32_t)floorf(c);*out=interpolate(b->cycle_positions,i,f32(c-(float)i));return true;
}
bool mw_ginsu_sample_cycle(const MwGinsuBank*b,int32_t s,float*out){
 if(!b||!b->data||!out)return false;
 if(s<=pos(b->cycle_positions,0)){*out=0;return true;}if(s>=pos(b->cycle_positions,b->cycles)){*out=(float)b->cycles;return true;}
 uint32_t lo=0,hi=b->cycles;while(hi-lo>1){uint32_t mid=(lo+hi)/2;if(pos(b->cycle_positions,mid)<=s)lo=mid;else hi=mid;}
 float a=(float)pos(b->cycle_positions,lo),z=(float)pos(b->cycle_positions,lo+1);*out=f32((float)lo+f32(f32((float)s-a)/f32(z-a)));return true;
}
bool mw_ginsu_cycle_period(const MwGinsuBank*b,float c,float*out){
 if(!b||!b->data||!out||!isfinite(c)||fabsf(c)>16777216.f)return false;
 int32_t i=(int32_t)floorf(c);float a,z;
 if(i<=0){if(i<0){i=0;c=0;}a=(float)(pos(b->cycle_positions,1)-pos(b->cycle_positions,0));z=f32((float)(pos(b->cycle_positions,2)-pos(b->cycle_positions,0))*.5f);}
 else if(i>=(int32_t)b->cycles-1){if(i>=(int32_t)b->cycles){i=(int32_t)b->cycles-1;c=(float)b->cycles;}a=f32((float)(pos(b->cycle_positions,b->cycles)-pos(b->cycle_positions,b->cycles-2))*.5f);z=(float)(pos(b->cycle_positions,b->cycles)-pos(b->cycle_positions,b->cycles-1));}
 else{a=f32((float)(pos(b->cycle_positions,(uint32_t)i+1)-pos(b->cycle_positions,(uint32_t)i-1))*.5f);z=f32((float)(pos(b->cycle_positions,(uint32_t)i+2)-pos(b->cycle_positions,(uint32_t)i))*.5f);}
 *out=fmaf(f32(c-(float)i),f32(z-a),a);return true;
}
static void decode(MwGinsuState*s,const MwGinsuBank*b,int32_t block){
 const unsigned char*p=b->samples+(size_t)block*19;static const float c1[4]={0,.9375f,1.796875f,1.53125f},c2[4]={0,0,-.8125f,-.859375f};
 unsigned pred=p[0]&3,shift=p[2]&15;s->decoded[0]=(float)((int32_t)(int8_t)p[1]*256+(p[0]&240));s->decoded[1]=(float)((int32_t)(int8_t)p[3]*256+(p[2]&240));
 for(unsigned i=2;i<32;i++){unsigned nib=(i&1)?p[4+(i-2)/2]&15:p[4+(i-2)/2]>>4;int32_t n=nib<8?(int32_t)nib:(int32_t)nib-16;float x=ldexpf((float)n,12-(int)shift);float t=fmaf(c1[pred],s->decoded[i-1],x);s->decoded[i]=fmaf(c2[pred],s->decoded[i-2],t);}s->cached_block=block;
}
bool mw_ginsu_samples(MwGinsuState*s,const MwGinsuBank*b,int32_t at,int16_t*out,uint32_t count){
 if(!s||!s->ready||!b||!b->data||!out||at<0||(uint64_t)(uint32_t)at+count>b->sample_count)return false;
 for(uint32_t i=0;i<count;i++){uint32_t index=(uint32_t)at+i;int32_t block=(int32_t)(index/32);if(block!=s->cached_block)decode(s,b,block);float f=s->decoded[index&31];int32_t x=(int32_t)f;if(x>32767)x=32767;if(x< -32768)x=-32768;out[i]=(int16_t)x;}return true;
}
bool mw_ginsu_engine_frequency(const MwGinsuBank*b,float rpm,float minimum,float maximum,float*frequency,float*pitch){
 if(!b||!b->data||!frequency||!pitch||!isfinite(rpm)||!isfinite(minimum)||!isfinite(maximum)||minimum<=0||maximum<=minimum)return false;
 float q=rpm<1000?1000:rpm>10000?10000:rpm;
 float requested=fmaf(f32(q-1000.f),f32(f32(maximum-minimum)*.00011111111234640703f),minimum);
 if(!isfinite(requested)||requested<=0)return false;
 *frequency=requested<b->min_frequency?b->min_frequency:requested;
 *pitch=requested<b->min_frequency?f32(requested/b->min_frequency):1.f;return true;
}
bool mw_ginsu_start(MwGinsuState*out,const MwGinsuBank*b,float frequency){
 if(!out||!b||!b->data)return false;
 MwGinsuState s={0};if(!mw_ginsu_frequency_sample(b,frequency,&s.current))return false;
 s.packet_size=(uint32_t)nearest(f32((float)b->rate*.010999999940395355f));s.overlap_size=(uint32_t)nearest(f32((float)b->rate*.0005000000237487257f));s.no_jump_size=s.packet_size;
 if(!s.packet_size||s.packet_size+s.overlap_size>MW_GINSU_MAX_PACKET||!s.overlap_size)return false;
 s.playback=s.target=s.current;s.countdown=1;s.no_jump_remaining=(int32_t)s.no_jump_size;s.cached_block=-1;mw_ginsu_sample_cycle(b,s.current,&s.current_cycle);s.ready=true;*out=s;return true;
}
bool mw_ginsu_frequency(MwGinsuState*s,const MwGinsuBank*b,float frequency,float milliseconds){
 if(!s||!s->ready||!isfinite(milliseconds)||milliseconds<0||milliseconds>100000)return false;
 int32_t target;if(!mw_ginsu_frequency_sample(b,frequency,&target))return false;
 s->target=target;s->countdown=(int32_t)floorf(f32(milliseconds*.09090909361839294f))+1;return true;
}
bool mw_ginsu_packet(MwGinsuState*s,const MwGinsuBank*b,int16_t*out,size_t capacity){
 if(!s||!s->ready||!b||!out||capacity<s->packet_size||!s->packet_size||s->packet_size>MW_GINSU_MAX_PACKET||!s->overlap_size||s->overlap_size>256||s->countdown<1||s->no_jump_remaining<0)return false;
 MwGinsuState t=*s;int16_t result[MW_GINSU_MAX_PACKET],overlap[256];
 if(!mw_ginsu_sample_cycle(b,t.current,&t.current_cycle))return false;
 float delta=f32((float)(t.target-t.current)/(float)t.countdown),split=1;int32_t jump=0;
 if(t.no_jump_remaining<(int32_t)t.packet_size){
  float playback_cycle,period_a,period_b;mw_ginsu_sample_cycle(b,t.playback,&playback_cycle);mw_ginsu_cycle_period(b,playback_cycle,&period_a);mw_ginsu_cycle_period(b,t.current_cycle,&period_b);
  float advance=f32((float)t.packet_size/period_a),d=f32(f32(delta/period_b)-advance),fraction=f32((float)t.no_jump_remaining/(float)t.packet_size),offset=f32(t.current_cycle-playback_cycle);
  float a=fmaf(d,fraction,offset),z=f32(offset+d);
  if(floorf(a)!=floorf(z)){jump=(int32_t)(a<z?ceilf(a):floorf(a));split=f32(f32((float)jump-offset)/d);}
  else{float limit=ceilf(fabsf(f32(d*.9999999403953552f)));if(fabsf(a)>limit){split=fraction;jump=(int32_t)(a>0?floorf(a):ceilf(a));}}
 }
 if(!jump)split=1;
 int32_t n=nearest(f32(split*(float)t.packet_size));if(n<0||n>(int32_t)t.packet_size)return false;
 if(!mw_ginsu_samples(&t,b,t.playback,result,(uint32_t)n))return false;
 t.playback+=n;t.no_jump_remaining-=n;if(t.no_jump_remaining<0)t.no_jump_remaining=0;
 if(jump){
  if((uint32_t)n+t.overlap_size>MW_GINSU_MAX_PACKET||!mw_ginsu_samples(&t,b,t.playback,result+n,t.overlap_size))return false;
  float cycle;mw_ginsu_sample_cycle(b,t.playback,&cycle);if(!mw_ginsu_cycle_sample(b,f32(cycle+(float)jump),&t.playback)||!mw_ginsu_samples(&t,b,t.playback,overlap,t.overlap_size))return false;
  float alpha=0,step=f32(1.f/(float)t.overlap_size);
  for(uint32_t i=0;i<t.overlap_size;i++){float v=fmaf(alpha,(float)((int32_t)overlap[i]-result[n+(int32_t)i]),(float)result[n+(int32_t)i]);result[n+(int32_t)i]=(int16_t)nearest(v);alpha=f32(alpha+step);}
  n+=(int32_t)t.overlap_size;t.playback+=(int32_t)t.overlap_size;t.no_jump_remaining=(int32_t)t.no_jump_size-(int32_t)t.overlap_size;
  int32_t rest=(int32_t)t.packet_size-n;if(rest>0){if(!mw_ginsu_samples(&t,b,t.playback,result+n,(uint32_t)rest))return false;t.playback+=rest;t.no_jump_remaining-=rest;}
 }
 t.current=nearest(f32((float)t.current+delta));if(t.countdown>1)t.countdown--;
 *s=t;memcpy(out,result,t.packet_size*sizeof(*out));return true;
}
bool mw_ginsu_render(MwGinsuState*s,const MwGinsuBank*b,int16_t*out,uint32_t frames){
 if(!s||!s->ready||!out||frames>16384)return false;
 while(frames){if(s->cursor==s->available){if(!mw_ginsu_packet(s,b,s->packet,MW_GINSU_MAX_PACKET))return false;s->cursor=0;s->available=s->packet_size;}uint32_t n=s->available-s->cursor;if(n>frames)n=frames;memcpy(out,s->packet+s->cursor,n*sizeof(*out));s->cursor+=n;out+=n;frames-=n;}return true;
}
