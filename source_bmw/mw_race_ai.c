#include "mw_race_ai.h"
#include "mw_playable_race.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
#define NODE_LIMIT 8192
static uint32_t word(const unsigned char *p){return p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static float real(const unsigned char *p){uint32_t u=word(p);float f;memcpy(&f,&u,4);return f;}
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
static bool finite3(const float p[3]){return p&&isfinite(p[0])&&isfinite(p[1])&&isfinite(p[2]);}
static bool source_hash(const unsigned char *p,const char *hex){
    for(unsigned i=0;i<32;i++){unsigned a=(unsigned char)hex[i*2],b=(unsigned char)hex[i*2+1];a=a>='a'?a-'a'+10:a-'0';b=b>='a'?b-'a'+10:b-'0';if(p[i]!=(a*16+b))return false;}return true;
}
static const char *text(const MwRaceAIPack *p,uint32_t at,bool model){
    if(at>=p->strings_bytes)return NULL;
    const unsigned char *s=p->data+p->strings_at+at;
    for(unsigned i=0;i<64&&at+i<p->strings_bytes;i++){
        unsigned c=s[i];if(!c)return i?(const char*)s:NULL;
        if(c<32||c>126||(model&&!((c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_')))return NULL;
    }return NULL;
}
static bool event(const MwRaceAIPack *p,uint32_t key,uint32_t *first,uint32_t *count){
    if(!p||!p->data)return false;
    for(unsigned i=0;i<5;i++){const unsigned char *r=p->data+p->events_at+i*16;if(word(r)==key){*first=word(r+4);*count=word(r+8);return true;}}return false;
}
bool mw_race_ai_spec(const MwRaceAIPack *p,uint32_t key,unsigned index,MwRaceAISpec *out){
    uint32_t first,count;if(!out||!event(p,key,&first,&count)||index>=count)return false;
    const unsigned char *r=p->data+p->actors_at+(first+index)*64;
    MwRaceAISpec s={.key=word(r),.spawn_key=word(r+4),.model_key=word(r+8),.model=text(p,word(r+12),true),.preset=text(p,word(r+16),false),.explicit_spawn=word(r+20)!=0,.rotation=real(r+36)};
    for(unsigned a=0;a<3;a++)s.position[a]=real(r+24+a*4);
    *out=s;return true;
}
bool mw_race_ai_pack_open(MwRaceAIPack *out,const void *data,size_t bytes){
    if(!out||!data||bytes<=656||bytes>4096)return false;
    const unsigned char *p=data;
    if(memcmp(p,"NRO1",4)||word(p+4)!=1||word(p+8)!=bytes||word(p+12)!=crc(p+16,bytes-16)||word(p+16)!=5||word(p+20)!=128||word(p+24)!=208||word(p+28)!=7||p[656])return false;
    if(!source_hash(p+32,"7ac98113d931cd90c68dbdb8e6ba94c643eef85a9af076a5f2e71ac4072d9ab6")||
       !source_hash(p+64,"5b69c44ffcfc7013a3f24900b33617002b1f68f2484a9108daa5bfe5d72ad20c")||
       !source_hash(p+96,"da02353de70dea3a8a51d6231e4efde15ab8c5c72eed6119a49bc9dad20b770b"))return false;
    MwRaceAIPack v={p,bytes,128,208,656,(uint32_t)bytes-656};
    static const uint32_t ids[]={0x42938ce2,0xd348f2cd,0x6ddd8383,0x9f60a40e,0xf7e4440a};uint32_t next=0;
    for(unsigned i=0;i<5;i++){
        const unsigned char *r=p+128+i*16;uint32_t n=i==3?3:1;
        if(word(r)!=ids[i]||word(r+4)!=next||word(r+8)!=n||word(r+12))return false;
        for(unsigned j=0;j<n;j++){
            MwRaceAISpec s;mw_race_ai_spec(&v,ids[i],j,&s);
            const unsigned char *a=p+208+(next+j)*64;
            if(!s.key||!s.model_key||!s.model||!s.preset||!finite3(s.position)||!isfinite(s.rotation)||word(a+20)>1||s.explicit_spawn!=(s.spawn_key!=0))return false;
            if(!s.explicit_spawn&&(s.rotation||s.position[0]||s.position[1]||s.position[2]))return false;
            for(unsigned b=40;b<64;b++)if(a[b])return false;
        }next+=n;
    }*out=v;return true;
}
MwRaceAITuning mw_race_ai_default_tuning(void){return (MwRaceAITuning){24,8,7,1.15f,3,7,1.5f};}
typedef struct {
    float distance[NODE_LIMIT];uint16_t previous[NODE_LIMIT],edge[NODE_LIMIT],heap[NODE_LIMIT],where[NODE_LIMIT];
    unsigned char closed[NODE_LIMIT];uint32_t count;
} Planner;
static void heap_swap(Planner *p,unsigned a,unsigned b){uint16_t v=p->heap[a];p->heap[a]=p->heap[b];p->heap[b]=v;p->where[p->heap[a]]=(uint16_t)a;p->where[v]=(uint16_t)b;}
static void heap_up(Planner *p,unsigned at){while(at){unsigned parent=(at-1)/2;if(p->distance[p->heap[parent]]<=p->distance[p->heap[at]])break;heap_swap(p,parent,at);at=parent;}}
static void heap_push(Planner *p,uint16_t node){if(p->where[node]!=UINT16_MAX){heap_up(p,p->where[node]);return;}unsigned at=p->count++;p->heap[at]=node;p->where[node]=(uint16_t)at;heap_up(p,at);}
static uint16_t heap_pop(Planner *p){uint16_t out=p->heap[0];p->where[out]=UINT16_MAX;if(!--p->count)return out;p->heap[0]=p->heap[p->count];p->where[p->heap[0]]=0;unsigned at=0;for(;;){unsigned l=at*2+1,r=l+1;if(l>=p->count)break;unsigned child=r<p->count&&p->distance[p->heap[r]]<p->distance[p->heap[l]]?r:l;if(p->distance[p->heap[at]]<=p->distance[p->heap[child]])break;heap_swap(p,at,child);at=child;}return out;}
static uint16_t nearest(const MwTrafficWorld *w,const float source[3],MwRaceAIWork *work){
    float native[3]={-source[1],source[2],source[0]},best=INFINITY;uint16_t result=UINT16_MAX;
    for(uint32_t i=0;i<w->nodes;i++){
        MwTrafficNode n;mw_traffic_node(w,i,&n);if(!n.count)continue;float d=0;
        for(unsigned a=0;a<3;a++){float x=n.position[a]-native[a];d+=x*x;}
        if(d<best){best=d;result=(uint16_t)i;}if(work)work->nearest_nodes++;
    }return result;
}
static bool append(MwRaceAI *s,unsigned actor,const float native[3]){
    MwRaceAIActor *a=s->actors+actor;if(a->path_count==MW_RACE_AI_POINTS)return false;
    float p[3]={native[2]-s->origin[0],native[1]-s->origin[1],native[0]-s->origin[2]};
    if(a->path_count){const float *last=s->paths[actor][a->path_count-1].position;if(fabsf(last[0]-p[0])+fabsf(last[2]-p[2])<.01f)return true;}
    memcpy(s->paths[actor][a->path_count++].position,p,sizeof(p));return true;
}
static bool route_leg(MwRaceAI *s,unsigned actor,const MwTrafficWorld *w,Planner *p,uint16_t from,uint16_t to,MwRaceAIWork *work){
    for(uint32_t i=0;i<w->nodes;i++){p->distance[i]=INFINITY;p->previous[i]=p->edge[i]=p->where[i]=UINT16_MAX;p->closed[i]=0;}p->count=0;p->distance[from]=0;heap_push(p,from);
    while(p->count){
        uint16_t at=heap_pop(p);p->closed[at]=1;if(work)work->planner_nodes++;if(at==to)break;
        MwTrafficNode node;mw_traffic_node(w,at,&node);
        for(unsigned j=0;j<node.count;j++){
            MwTrafficSegment edge;mw_traffic_segment(w,node.segments[j],&edge);uint16_t next=edge.nodes[0]==at?edge.nodes[1]:edge.nodes[0];
            if(work)work->planner_edges++;
            if(p->closed[next])continue;
            float d=p->distance[at]+edge.length;
            if(d<p->distance[next]){p->distance[next]=d;p->previous[next]=at;p->edge[next]=node.segments[j];heap_push(p,next);}
        }
    }
    if(!isfinite(p->distance[to]))return false;
    /* Reuse heap storage after the search to reverse the source node chain. */
    unsigned n=0;uint16_t current=to;
    while(current!=from){if(n>=w->nodes||p->previous[current]==UINT16_MAX)return false;p->heap[n++]=current;current=p->previous[current];}
    uint16_t start=from;
    while(n){uint16_t end=p->heap[--n];MwTrafficSegment edge;mw_traffic_segment(w,p->edge[end],&edge);bool reverse=edge.nodes[1]==start;
        for(unsigned q=1;q<=4;q++){float u=(float)q*.25f,point[3],tangent[3];if(reverse)u=1-u;if(!mw_traffic_sample(w,p->edge[end],u,point,tangent)||!append(s,actor,point))return false;}
        start=end;
    }return true;
}
bool mw_race_ai_begin(MwRaceAI *out,const MwRaceAIPack *pack,const MwEventCatalog *catalog,const MwTrafficWorld *roads,uint32_t key,const float origin[3],MwRaceAIWork *work){
    uint32_t first,count;MwEventDefinition event_;MwEventNode start;
    if(!out||!catalog||!roads||!roads->data||roads->nodes>NODE_LIMIT||!finite3(origin)||!event(pack,key,&first,&count)||!mw_event_catalog_find(catalog,key,&event_)||!mw_event_catalog_node(catalog,event_.start,&start)||(start.present&3)!=3)return false;
    MwRaceAI *s=calloc(1,sizeof(*s));Planner *planner=malloc(sizeof(*planner));if(!s||!planner){free(s);free(planner);return false;}
    s->catalog=catalog;s->event=key;s->count=count;s->tuning=mw_race_ai_default_tuning();memcpy(s->origin,origin,12);
    bool ok=mw_event_catalog_route(catalog,key,s->checkpoints,1024,&s->route)&&s->route.laps&&s->route.laps<=8;
    for(unsigned i=0;ok&&i<count;i++){
        MwRaceAIActor *actor=s->actors+i;mw_race_ai_spec(pack,key,i,&actor->spec);
        float position[3],rotation=actor->spec.explicit_spawn?actor->spec.rotation:start.rotation;
        if(actor->spec.explicit_spawn)memcpy(position,actor->spec.position,12);
        else{
            float r=start.rotation*.017453292519943295f,back=(float)(i/2+1)*s->tuning.grid_spacing,side=(i&1?1.f:-1.f)*s->tuning.grid_lateral;
            position[0]=start.position[0]-cosf(r)*back-sinf(r)*side;position[1]=start.position[1]-sinf(r)*back+cosf(r)*side;position[2]=start.position[2];
        }
        drive_reset(&actor->motion,position[0]-origin[0],-position[1]-origin[2],remainderf(90+rotation,360)*.017453292519943295f);actor->height=position[2]-origin[1];
        if(!mw_race_begin(&actor->progress,&s->route)){ok=false;break;}
        uint16_t node=nearest(roads,position,work);if(node==UINT16_MAX){ok=false;break;}
        MwTrafficNode initial;mw_traffic_node(roads,node,&initial);if(!append(s,i,initial.position)){ok=false;break;}
        for(unsigned lap=0;ok&&lap<s->route.laps;lap++)for(size_t gate=0;ok&&gate<=s->route.count;gate++){
            MwEventNode target;if(!mw_event_catalog_node(catalog,gate==s->route.count?s->route.finish:s->checkpoints[gate],&target)){ok=false;break;}
            uint16_t goal=nearest(roads,target.position,work);if(goal==UINT16_MAX||!route_leg(s,i,roads,planner,node,goal,work)){ok=false;break;}
            float native[3]={-target.position[1],target.position[2],target.position[0]};if(!append(s,i,native)){ok=false;break;}node=goal;
        }
        if(!actor->path_count)ok=false;
    }
    if(ok){*out=*s;out->route.checkpoints=out->checkpoints;for(unsigned i=0;i<count;i++)out->actors[i].progress.route.checkpoints=out->checkpoints;}
    free(planner);free(s);return ok;
}
bool mw_race_ai_place(MwRaceAI *s,unsigned i,const float source[3],float yaw){
    if(!s||s->running||i>=s->count||!finite3(source)||!isfinite(yaw))return false;
    MwRaceAIActor *a=s->actors+i;drive_reset(&a->motion,source[0]-s->origin[0],-source[1]-s->origin[2],yaw);a->height=source[2]-s->origin[1];a->path_cursor=0;return true;
}
bool mw_race_ai_admit(MwRaceAI *s,unsigned i,bool ready){if(!s||s->running||i>=s->count)return false;s->actors[i].admitted=ready;return true;}
bool mw_race_ai_start(MwRaceAI *s){if(!s||!s->count||s->running)return false;for(unsigned i=0;i<s->count;i++)if(!s->actors[i].admitted||s->actors[i].failed)return false;s->running=true;s->step_ready=true;return true;}
bool mw_race_ai_pause(MwRaceAI *s,bool pause){if(!s||!s->running)return false;s->paused=pause;return true;}
static float distance2(const float a[3],const float b[3]){float x=a[0]-b[0],z=a[2]-b[2];return x*x+z*z;}
static float clamp(float f,float a,float b){return f<a?a:f>b?b:f;}
static bool progress_motion(MwRaceAI *s,MwRaceAIActor *a,const float from[3],const float to[3],uint64_t dt,MwRaceAIWork *work){
    double cursor=0;uint64_t timed=0;
    for(unsigned crossed=0;crossed<32&&!a->progress.finished;crossed++){
        uint32_t key=a->progress.next<a->progress.route.count?s->checkpoints[a->progress.next]:a->progress.route.finish;
        MwEventNode gate;if(!mw_event_catalog_node(s->catalog,key,&gate))return false;float begin[3];for(unsigned k=0;k<3;k++)begin[k]=(float)(from[k]+(to[k]-from[k])*cursor);
        double fraction;if(work)work->gate_tests++;
        if(!mw_playable_race_sweep(&gate,begin,to,1,&fraction))break;
        double global=cursor+(1-cursor)*fraction;uint64_t now=(uint64_t)((double)dt*global);
        if(now<timed||!mw_race_tick(&a->progress,now-timed))return false;
        timed=now;if(mw_race_gate(&a->progress,key)==MW_RACE_IGNORED)return false;cursor=global;if(cursor>=1)break;
    }
    return a->progress.finished||mw_race_tick(&a->progress,dt-timed);
}
bool mw_race_ai_step(MwRaceAI *s,float seconds,MwRaceAIDrive drive,void *ctx,MwRaceAIWork *work){
    if(!s||!s->running||!s->count||s->count>MW_RACE_AI_ACTORS||!drive||!isfinite(seconds)||seconds<=0||seconds>.1f)return false;
    if(s->paused)return true;
    s->step_ready=false;
    MwRaceAIActor next[MW_RACE_AI_ACTORS];memcpy(next,s->actors,sizeof(next));uint64_t dt=(uint64_t)llround((double)seconds*1000000);
    for(unsigned i=0;i<s->count;i++){
        MwRaceAIActor *a=next+i;if(!a->admitted||a->failed||!a->path_count||a->path_count>MW_RACE_AI_POINTS||a->path_cursor>=a->path_count)return false;if(a->progress.finished)continue;
        float current[3]={a->motion.x,a->height,a->motion.z};unsigned checked=0;
        while(a->path_cursor+1<a->path_count&&checked++<32){
            if(work)work->guide_checks++;
            float threshold=fminf(s->tuning.lookahead,s->tuning.arrival_radius+fabsf(a->motion.speed)*.15f);
            if(distance2(current,s->paths[i][a->path_cursor].position)>threshold*threshold)break;
            a->path_cursor++;
        }
        const float *target=s->paths[i][a->path_cursor].position;float dx=target[0]-a->motion.x,dz=target[2]-a->motion.z;
        float error=remainderf(atan2f(dx,dz)-a->motion.heading,6.283185307179586f);
        float target_speed=clamp(s->tuning.cruise_speed/(1+fabsf(error)*2),s->tuning.corner_speed,s->tuning.cruise_speed);
        /* A native tight-turn recovery policy. The provisional physical
           controller cannot pivot at cruise speed around a missed point. */
        if(fabsf(error)>1)target_speed=fminf(target_speed,s->tuning.corner_speed*.3f);
        DriveInput input={.throttle=a->motion.speed<target_speed?1.f:0.f,.brake=a->motion.speed>target_speed+1?1.f:0.f,.steering=clamp(error*s->tuning.steering_gain,-1,1)};
        float before[3]={a->motion.x+s->origin[0],-(a->motion.z+s->origin[2]),a->height+s->origin[1]};
        int result=drive(ctx,&a->motion,&a->height,input,seconds);if(work)work->drive_calls++;if(result<0||!finite3((float[3]){a->motion.x,a->height,a->motion.z}))return false;
        if(!result){a->blocked++;if(work)work->blocked_steps++;}else a->blocked=0;
        float after[3]={a->motion.x+s->origin[0],-(a->motion.z+s->origin[2]),a->height+s->origin[1]};
        if(!progress_motion(s,a,before,after,dt,work))return false;
    }memcpy(s->actors,next,sizeof(next));s->step_ready=true;return true;
}
static bool ahead(const MwRaceProgress *a,const float ap[3],const MwRaceProgress *b,const float bp[3],const MwEventCatalog *catalog){
    if(a->finished||b->finished)return a->finished&&(!b->finished||a->elapsed_us<b->elapsed_us);
    if(a->lap!=b->lap)return a->lap>b->lap;
    if(a->next!=b->next)return a->next>b->next;
    uint32_t key=a->next<a->route.count?a->route.checkpoints[a->next]:a->route.finish;MwEventNode node;
    if(!mw_event_catalog_node(catalog,key,&node))return false;
    float da=0,db=0;for(unsigned k=0;k<3;k++){float x=ap[k]-node.position[k],y=bp[k]-node.position[k];da+=x*x;db+=y*y;}return da<db;
}
bool mw_race_ai_rank(const MwRaceAI *s,const MwRaceProgress *player,const float position[3],unsigned *rank){
    if(!s||!s->running||!s->step_ready||!player||!finite3(position)||!rank||player->route.count!=s->route.count||player->route.finish!=s->route.finish||player->route.laps!=s->route.laps||!player->route.checkpoints||memcmp(player->route.checkpoints,s->checkpoints,s->route.count*4))return false;
    unsigned value=1;for(unsigned i=0;i<s->count;i++){const MwRaceAIActor *a=s->actors+i;if(!a->admitted||a->failed)return false;float source[3]={a->motion.x+s->origin[0],-(a->motion.z+s->origin[2]),a->height+s->origin[1]};if(ahead(&a->progress,source,player,position,s->catalog))value++;}*rank=value;return true;
}
