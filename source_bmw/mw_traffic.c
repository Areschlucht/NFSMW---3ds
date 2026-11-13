#include "mw_traffic.h"
#include <math.h>
#include <string.h>
static uint32_t le32(const unsigned char *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint16_t be16(const unsigned char *p){return (uint16_t)((uint16_t)p[0]<<8|p[1]);}
static float lf(const unsigned char *p){uint32_t b=le32(p);float v;memcpy(&v,&b,4);return v;}
static float bf(const unsigned char *p){uint32_t b=(uint32_t)p[0]<<24|(uint32_t)p[1]<<16|(uint32_t)p[2]<<8|p[3];float v;memcpy(&v,&b,4);return v;}
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
static bool point_ok(const float p[3]){return p&&isfinite(p[0])&&isfinite(p[1])&&isfinite(p[2]);}
bool mw_traffic_node(const MwTrafficWorld *w,uint32_t i,MwTrafficNode *out){
 if(!w||!w->data||!out||i>=w->nodes)return false;
 const unsigned char *p=w->data+w->nodes_at+(size_t)i*32;MwTrafficNode n={.id=be16(p+12),.profile=be16(p+14),.count=p[16]};
 for(unsigned a=0;a<3;a++)n.position[a]=bf(p+a*4);
 for(unsigned a=0;a<7;a++)n.segments[a]=be16(p+18+a*2);
 *out=n;return true;
}
bool mw_traffic_segment(const MwTrafficWorld *w,uint32_t i,MwTrafficSegment *out){
 if(!w||!w->data||!out||i>=w->segments)return false;
 const unsigned char *p=w->data+w->segments_at+(size_t)i*32;
 *out=(MwTrafficSegment){.nodes={be16(p),be16(p+2)},.id=be16(p+8),.flags=be16(p+10),.length=lf(p+24)};return true;
}
bool mw_traffic_open(MwTrafficWorld *out,const void *data,size_t bytes){
 if(!out||!data||bytes<192||bytes>4*1024*1024)return false;
 const unsigned char *p=data;
 if(memcmp(p,"MWT1",4)||le32(p+4)!=1||le32(p+8)!=bytes||le32(p+12)!=crc(p+16,bytes-16))return false;
 MwTrafficWorld w={.data=p,.bytes=bytes,.nodes=le32(p+16),.segments=le32(p+20),.nodes_at=le32(p+24),.segments_at=le32(p+28),.profiles=le32(p+32),.profiles_at=le32(p+36),.columns=le32(p+40),.rows=le32(p+44),.grid_refs=le32(p+48),.grid_at=le32(p+52),.refs_at=le32(p+56),.min_x=lf(p+128),.min_z=lf(p+132),.cell=lf(p+136)};
 if(!w.nodes||w.nodes>8192||!w.segments||w.segments>8192||w.nodes_at!=192||w.segments_at!=w.nodes_at+w.nodes*32||w.profiles_at!=w.segments_at+w.segments*32||w.profiles>4096||!w.columns||w.columns>256||!w.rows||w.rows>256||!isfinite(w.min_x)||!isfinite(w.min_z)||!isfinite(w.cell)||w.cell<16||w.cell>1024||le32(p+60))return false;
 if(w.grid_at!=w.profiles_at+w.profiles*64||w.refs_at!=w.grid_at+((uint64_t)w.columns*w.rows+1)*4||bytes!=w.refs_at+(uint64_t)w.grid_refs*2)return false;
 for(unsigned i=140;i<192;i++)if(p[i])return false;
 uint32_t prior=0,cells=w.columns*w.rows;
 for(uint32_t i=0;i<=cells;i++){uint32_t v=le32(p+w.grid_at+i*4);if(v<prior||v>w.grid_refs||(!i&&v)||(i==cells&&v!=w.grid_refs))return false;prior=v;}
 for(uint32_t i=0;i<w.grid_refs;i++){const unsigned char *q=p+w.refs_at+i*2;uint16_t id=(uint16_t)(q[0]|(uint16_t)q[1]<<8);if(id>=w.segments)return false;}
 for(uint32_t i=0;i<w.nodes;i++){
  MwTrafficNode n;mw_traffic_node(&w,i,&n);if(n.id!=i||!n.count||n.count>7||!point_ok(n.position))return false;
  for(unsigned a=0;a<3;a++)if(fabsf(n.position[a])>20000)return false;
  for(unsigned j=0;j<n.count;j++){MwTrafficSegment s;if(!mw_traffic_segment(&w,n.segments[j],&s)||(s.nodes[0]!=i&&s.nodes[1]!=i))return false;}
 }
 for(uint32_t i=0;i<w.segments;i++){
  MwTrafficSegment s;mw_traffic_segment(&w,i,&s);const unsigned char *r=p+w.segments_at+i*32;
  if(s.id!=i||s.nodes[0]>=w.nodes||s.nodes[1]>=w.nodes||s.nodes[0]==s.nodes[1]||!isfinite(s.length)||s.length<.001f||s.length>10000||r[22]||r[23]||le32(r+28))return false;
  for(unsigned a=0;a<2;a++){MwTrafficNode n;mw_traffic_node(&w,s.nodes[a],&n);bool found=false;for(unsigned j=0;j<n.count;j++)found|=n.segments[j]==i;if(!found)return false;}
 }
 *out=w;return true;
}
bool mw_traffic_sample(const MwTrafficWorld *w,uint16_t id,float t,float position[3],float tangent[3]){
 MwTrafficSegment s;MwTrafficNode a,b;
 if(!position||!tangent||!isfinite(t)||t<0||t>1||!mw_traffic_segment(w,id,&s)||!mw_traffic_node(w,s.nodes[0],&a)||!mw_traffic_node(w,s.nodes[1],&b))return false;
 const unsigned char *r=w->data+w->segments_at+(size_t)id*32;float p[3],d[3];
 for(unsigned k=0;k<3;k++){
  if(!(s.flags&0x100)){p[k]=fmaf(b.position[k]-a.position[k],t,a.position[k]);d[k]=b.position[k]-a.position[k];continue;}
  float la=be16(r+12)*6.00748899159953e-05f,lb=be16(r+14)*6.00748899159953e-05f;
  float c1=a.position[k]+lb*(int8_t)r[19+k],c2=b.position[k]+la*(int8_t)r[16+k];
  float A=fmaf(-1,a.position[k],3*c1);A=fmaf(-3,c2,A);A=b.position[k]+A;
  float B=fmaf(3,a.position[k],-6*c1);B=fmaf(3,c2,B);
  float C=fmaf(-3,a.position[k],3*c1),t2=t*t,t3=t2*t;
  p[k]=fmaf(t2,B,t3*A);p[k]=fmaf(t,C,p[k]);p[k]+=a.position[k];
  d[k]=fmaf(3*A,t2,fmaf(2*B,t,C));
 }
 if(!point_ok(p)||!point_ok(d))return false;
 memcpy(position,p,sizeof(p));memcpy(tangent,d,sizeof(d));return true;
}
static int admit(const MwTrafficWorld *w,uint16_t id,unsigned direction,MwTrafficAdmission allow,void *ctx,MwTrafficSegment *s){
 if(!mw_traffic_segment(w,id,s))return -1;
 if(s->flags&1)return 0;
 int value=allow?allow(ctx,id,s->flags,direction):1;
 return value==0||value==1?value:-1;
}
static bool pose(const MwTrafficWorld *w,MwTrafficCar *c,MwTrafficWork *work){
 float t=c->direction?1-c->u:c->u;
 if(!mw_traffic_sample(w,c->segment,t,c->position,c->forward))return false;
 if(work)work->samples++;
 if(c->direction)for(unsigned a=0;a<3;a++)c->forward[a]=-c->forward[a];
 float l=sqrtf(c->forward[0]*c->forward[0]+c->forward[1]*c->forward[1]+c->forward[2]*c->forward[2]);
 if(!(l>.00001f))return false;
 for(unsigned a=0;a<3;a++)c->forward[a]/=l;
 return true;
}
bool mw_traffic_start(const MwTrafficWorld *w,MwTrafficCar *out,uint16_t id,unsigned direction,float u,float speed,MwTrafficAdmission allow,void *ctx,MwTrafficWork *work){
 if(!out||direction>1||!isfinite(u)||u<0||u>1||!isfinite(speed)||speed<0||speed>80)return false;
 MwTrafficSegment s;if(admit(w,id,direction,allow,ctx,&s)!=1)return false;
 MwTrafficCar c={.segment=id,.direction=direction,.u=u,.speed=speed,.active=true};if(!pose(w,&c,work))return false;*out=c;return true;
}
int mw_traffic_step(const MwTrafficWorld *w,MwTrafficCar *out,float seconds,MwTrafficAdmission allow,void *ctx,MwTrafficWork *work){
 if(!out||!isfinite(seconds)||seconds<=0||seconds>.1f||!isfinite(out->u)||out->u<0||out->u>1||out->direction>1||!isfinite(out->speed)||out->speed<0||out->speed>80)return -1;
 if(!out->active)return 0;
 MwTrafficCar c=*out;float distance=c.speed*seconds;unsigned transitions=0;MwTrafficSegment current;
 int allowed=admit(w,c.segment,c.direction,allow,ctx,&current);if(allowed<0)return -1;
 if(!allowed){c.speed=0;c.active=false;*out=c;return 0;}
 while(distance>(1-c.u)*current.length){
  if(transitions++==MW_TRAFFIC_MAX_TRANSITIONS)return -1;
  distance-=(1-c.u)*current.length;c.u=1;if(!pose(w,&c,work))return -1;
  uint16_t end=current.nodes[c.direction?0:1];MwTrafficNode node;if(!mw_traffic_node(w,end,&node))return -1;
  float best=-2;uint16_t next=UINT16_MAX;unsigned next_direction=0;
  for(unsigned j=0;j<node.count;j++){
   uint16_t id=node.segments[j];if(id==c.segment)continue;MwTrafficSegment s;mw_traffic_segment(w,id,&s);unsigned direction=s.nodes[0]==end?0u:1u;
   if(work)work->neighbor_checks++;
   int ok=admit(w,id,direction,allow,ctx,&s);if(ok<0)return -1;if(!ok)continue;
   MwTrafficCar candidate={.segment=id,.direction=direction};if(!pose(w,&candidate,work))return -1;
   float dot=0;for(unsigned a=0;a<3;a++)dot+=c.forward[a]*candidate.forward[a];
   if(dot>best){best=dot;next=id;next_direction=direction;}
  }
  if(next==UINT16_MAX){c.active=false;c.speed=0;*out=c;return 0;}
  c.segment=next;c.direction=next_direction;c.u=0;mw_traffic_segment(w,next,&current);if(work)work->transitions++;
 }
 c.u+=distance/current.length;if(!pose(w,&c,work))return -1;*out=c;return 1;
}
bool mw_traffic_nearest(const MwTrafficWorld *w,const float point[3],float radius,uint16_t *out,float *out_u,MwTrafficAdmission allow,void *ctx,MwTrafficWork *work){
 if(!w||!w->data||!point_ok(point)||!out||!out_u||!isfinite(radius)||radius<=0||radius>1000)return false;
 float gx=(point[0]-w->min_x)/w->cell,gz=(point[2]-w->min_z)/w->cell,span=radius/w->cell;
 if(gx+span<0||gz+span<0||gx-span>=w->columns||gz-span>=w->rows)return false;
 int x0=(int)fmaxf(0,floorf(gx-span)),z0=(int)fmaxf(0,floorf(gz-span)),x1=(int)fminf(w->columns-1,floorf(gx+span)),z1=(int)fminf(w->rows-1,floorf(gz+span));
 unsigned char seen[1024]={0};unsigned checked=0;float best=radius*radius,u_best=0;uint16_t found=UINT16_MAX;
 for(int z=z0;z<=z1;z++)for(int x=x0;x<=x1;x++){
  uint32_t cell=(unsigned)z*w->columns+(unsigned)x,begin=le32(w->data+w->grid_at+cell*4),end=le32(w->data+w->grid_at+(cell+1)*4);
  for(uint32_t i=begin;i<end;i++){
   const unsigned char *r=w->data+w->refs_at+i*2;uint16_t id=(uint16_t)(r[0]|(uint16_t)r[1]<<8);if(seen[id/8]&(1u<<(id%8)))continue;seen[id/8]|=(unsigned char)(1u<<(id%8));
   if(++checked>MW_TRAFFIC_MAX_NEAREST)return false;
   if(work)work->nearest_checks++;
   MwTrafficSegment s;int ok=admit(w,id,0,allow,ctx,&s);if(ok<0)return false;if(!ok)continue;
   float a[3],d[3];if(!mw_traffic_sample(w,id,0,a,d))return false;if(work)work->samples++;
   for(unsigned j=1;j<=16;j++){
    float b[3],tangent[3],line[3],q=0,length=0;if(!mw_traffic_sample(w,id,j/16.f,b,tangent))return false;if(work)work->samples++;
    for(unsigned k=0;k<3;k++){line[k]=b[k]-a[k];q+=(point[k]-a[k])*line[k];length+=line[k]*line[k];}
    q=length>0?fminf(1,fmaxf(0,q/length)):0;float squared=0;
    for(unsigned k=0;k<3;k++){float v=point[k]-(a[k]+q*line[k]);squared+=v*v;}
    if(squared<best){best=squared;found=id;u_best=((j-1)+q)/16;}
    memcpy(a,b,sizeof(a));
   }
  }
 }
 if(found==UINT16_MAX)return false;
 *out=found;*out_u=u_best;return true;
}
