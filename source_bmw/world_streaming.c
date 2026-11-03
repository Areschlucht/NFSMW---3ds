#include "world_streaming.h"
#include <math.h>
#include <string.h>
_Static_assert(sizeof(float)==4,"Original metadata requires float32");

static uint16_t u16(const uint8_t *p){return (uint16_t)(p[0]|(uint16_t)p[1]<<8);}
static uint32_t u32(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static float f32(const uint8_t *p){uint32_t bits=u32(p);float value;memcpy(&value,&bits,4);return value;}
static bool range(size_t size,uint32_t offset,uint32_t count,uint32_t width){return offset<=size&&count<=(size-offset)/width;}
static const uint8_t *polygon(const WorldStreamingDatabase *db,uint32_t index){return db->data+db->polygons+index*36;}
static const uint8_t *dependency(const WorldStreamingDatabase *db,uint32_t index){return db->data+db->dependencies+index*12;}

WorldStreamingResult world_streaming_open(const void *bytes,size_t size,WorldStreamingDatabase *out){
    if(!out)return WORLD_STREAMING_INVALID;
    memset(out,0,sizeof(*out));
    const uint8_t *p=bytes;
    if(!p||size<128||size>256*1024||memcmp(p,"WST1",4)||u16(p+4)!=1||u16(p+6)!=128||u32(p+8)!=size||u32(p+60))return WORLD_STREAMING_INVALID;
    WorldStreamingDatabase db={0};db.data=p;db.size=size;
    db.section_count=u32(p+12);db.polygon_count=u32(p+16);db.dependency_count=u32(p+20);
    db.point_count=u32(p+24);db.ref_count=u32(p+28);uint32_t span=u32(p+32);
    db.sections=u32(p+36);db.polygons=u32(p+40);db.dependencies=u32(p+44);
    db.points=u32(p+48);db.refs=u32(p+52);db.stream_bytes=u32(p+56);db.span=(uint16_t)span;
    if(!db.section_count||db.section_count>1024||!db.polygon_count||db.polygon_count>768||!db.dependency_count||db.dependency_count>512||db.point_count>768*16||db.ref_count>512*72||span<1||span>=100||
       !range(size,db.sections,db.section_count,12)||!range(size,db.polygons,db.polygon_count,36)||
       !range(size,db.dependencies,db.dependency_count,12)||!range(size,db.points,db.point_count,8)||!range(size,db.refs,db.ref_count,2))return WORLD_STREAMING_INVALID;
    if(db.sections!=128||db.polygons!=db.sections+db.section_count*12||db.dependencies!=db.polygons+db.polygon_count*36||
       db.points!=db.dependencies+db.dependency_count*12||db.refs!=db.points+db.point_count*8||size!=db.refs+db.ref_count*2)return WORLD_STREAMING_INVALID;
    uint16_t previous=0;
    for(uint32_t i=0;i<db.section_count;i++){
        const uint8_t *s=p+db.sections+i*12;uint16_t id=u16(s);uint32_t offset=u32(s+4),length=u32(s+8);
        if(!id||id>32767||(i&&id<=previous)||u16(s+2)||!length||offset%2048||offset>db.stream_bytes||length>db.stream_bytes-offset)return WORLD_STREAMING_INVALID;
        previous=id;
    }
    for(uint32_t i=0;i<db.point_count;i++)if(!isfinite(f32(p+db.points+i*8))||!isfinite(f32(p+db.points+i*8+4)))return WORLD_STREAMING_INVALID;
    for(uint32_t i=0;i<db.polygon_count;i++){
        const uint8_t *r=polygon(&db,i);uint32_t count=u16(r+2),first=u32(r+4);
        if(count<3||count>16||first>db.point_count||count>db.point_count-first)return WORLD_STREAMING_INVALID;
        for(unsigned j=0;j<6;j++)if(!isfinite(f32(r+8+j*4)))return WORLD_STREAMING_INVALID;
        if(f32(r+8)>f32(r+16)||f32(r+12)>f32(r+20))return WORLD_STREAMING_INVALID;
        for(uint32_t j=0;j<count;j++){
            const uint8_t *v=p+db.points+(first+j)*8;float x=f32(v),y=f32(v+4);
            if(x<f32(r+8)||x>f32(r+16)||y<f32(r+12)||y>f32(r+20))return WORLD_STREAMING_INVALID;
        }
    }
    for(uint32_t i=0;i<db.dependency_count;i++){
        const uint8_t *r=dependency(&db,i);uint32_t pi=u16(r+2),first=u32(r+4),count=u16(r+8);
        if(pi>=db.polygon_count||u16(polygon(&db,pi))!=u16(r)||count>72||first>db.ref_count||count>db.ref_count-first||u16(r+10))return WORLD_STREAMING_INVALID;
    }
    *out=db;return WORLD_STREAMING_OK;
}

void world_streaming_selector_init(const WorldStreamingDatabase *db,WorldStreamingSelector *state){
    if(!state)return;
    memset(state,0,sizeof(*state));if(!db||!db->data)return;
    state->count=(uint16_t)db->dependency_count;for(uint16_t i=0;i<state->count;i++)state->order[i]=i;
}
static bool contains(const WorldStreamingDatabase *db,const uint8_t *p,float x,float y){
    if(x<f32(p+8)||x>f32(p+16)||y<f32(p+12)||y>f32(p+20))return false;
    uint32_t count=u16(p+2),first=u32(p+4);bool result=false;
    const uint8_t *previous=db->data+db->points+(first+count-1)*8;
    for(uint32_t i=0;i<count;i++){
        const uint8_t *current=db->data+db->points+(first+i)*8;
        float xi=f32(current),yi=f32(current+4),xp=f32(previous),yp=f32(previous+4);
        if((yi<=y&&y<yp)||(yp<=y&&y<yi)){
            /* Original uses separate fsubs/fmuls/fdivs/fadds, not fused multiply-add. */
            volatile float dx=xp-xi,dy=y-yi,product=dx*dy,denominator=yp-yi;
            volatile float quotient=product/denominator,crossing=quotient+xi;
            if(x<crossing)result=!result;
        }
        previous=current;
    }
    return result;
}
WorldStreamingResult world_streaming_select(const WorldStreamingDatabase *db,WorldStreamingSelector *state,float x,float y,uint16_t *selected){
    if(!db||!db->data||!state||!selected||state->count!=db->dependency_count||!isfinite(x)||!isfinite(y))return WORLD_STREAMING_INVALID;
    for(uint16_t i=0;i<state->count;i++){
        uint16_t index=state->order[i];if(index>=db->dependency_count)return WORLD_STREAMING_INVALID;
        const uint8_t *d=dependency(db,index);
        if(contains(db,polygon(db,u16(d+2)),x,y)){
            memmove(state->order+1,state->order,i*sizeof(uint16_t));state->order[0]=index;*selected=index;return WORLD_STREAMING_OK;
        }
    }
    return WORLD_STREAMING_NEAREST_REQUIRED;
}
static int section_index(const WorldStreamingDatabase *db,uint16_t id){
    uint32_t low=0,high=db->section_count;
    while(low<high){uint32_t mid=low+(high-low)/2;uint16_t key=u16(db->data+db->sections+mid*12);if(key<id)low=mid+1;else high=mid;}
    return low<db->section_count&&u16(db->data+db->sections+low*12)==id?(int)low:-1;
}
bool world_streaming_section(const WorldStreamingDatabase *db,uint16_t id,WorldStreamingSection *out){
    if(!db||!db->data||!out)return false;
    int i=section_index(db,id);if(i<0)return false;
    const uint8_t *s=db->data+db->sections+(uint32_t)i*12;out->id=id;out->offset=u32(s+4);out->bytes=u32(s+8);return true;
}
WorldStreamingResult world_streaming_plan(const WorldStreamingDatabase *db,const uint16_t *indices,size_t viewpoints,uint16_t *out,size_t capacity,size_t *count){
    if(!db||!db->data||!count||viewpoints>2||(viewpoints&&!indices)||(!out&&capacity))return WORLD_STREAMING_INVALID;
    uint16_t ordered[147];size_t n=0;uint16_t base[3]={2500,2400,2600};
    for(size_t view=0;view<=viewpoints;view++){
        const uint8_t *record=NULL;uint32_t first=0;size_t length=3;
        if(view){if(indices[view-1]>=db->dependency_count)return WORLD_STREAMING_INVALID;record=dependency(db,indices[view-1]);first=u32(record+4);length=u16(record+8);}
        for(size_t j=0;j<length;j++){
            uint16_t id=record?u16(db->data+db->refs+(first+(uint32_t)j)*2):base[j];
            if(section_index(db,id)<0)continue;
            bool seen=false;for(size_t k=0;k<n;k++)if(ordered[k]==id){seen=true;break;}
            if(!seen)ordered[n++]=id;
        }
    }
    *count=n;if(n>capacity)return WORLD_STREAMING_CAPACITY;
    if(n)memcpy(out,ordered,n*sizeof(uint16_t));
    return WORLD_STREAMING_OK;
}
void world_streaming_residency_init(WorldStreamingResidency *state,uint32_t budget){if(state){memset(state,0,sizeof(*state));state->budget_bytes=budget;}}
WorldStreamingResult world_streaming_begin(const WorldStreamingDatabase *db,WorldStreamingResidency *state,uint16_t id,uint32_t bytes){
    if(!db||!db->data||!state||!bytes)return WORLD_STREAMING_INVALID;
    int i=section_index(db,id);if(i<0)return WORLD_STREAMING_INVALID;
    if(state->state[i]!=WORLD_STREAMING_UNLOADED)return WORLD_STREAMING_NOT_READY;
    if(state->used_bytes>state->budget_bytes||bytes>state->budget_bytes-state->used_bytes)return WORLD_STREAMING_BUDGET;
    state->charged_bytes[i]=bytes;state->used_bytes+=bytes;state->state[i]=WORLD_STREAMING_LOADING;return WORLD_STREAMING_OK;
}
WorldStreamingResult world_streaming_ready(const WorldStreamingDatabase *db,WorldStreamingResidency *state,uint16_t id){
    if(!db||!db->data||!state)return WORLD_STREAMING_INVALID;
    int i=section_index(db,id);if(i<0)return WORLD_STREAMING_INVALID;
    if(state->state[i]!=WORLD_STREAMING_LOADING)return WORLD_STREAMING_NOT_READY;
    state->state[i]=WORLD_STREAMING_READY;return WORLD_STREAMING_OK;
}
WorldStreamingResult world_streaming_release(const WorldStreamingDatabase *db,WorldStreamingResidency *state,uint16_t id){
    if(!db||!db->data||!state)return WORLD_STREAMING_INVALID;
    int i=section_index(db,id);if(i<0)return WORLD_STREAMING_INVALID;
    if(state->state[i]==WORLD_STREAMING_UNLOADED)return WORLD_STREAMING_NOT_READY;
    if(state->charged_bytes[i]>state->used_bytes)return WORLD_STREAMING_INVALID;
    state->used_bytes-=state->charged_bytes[i];state->charged_bytes[i]=0;state->state[i]=WORLD_STREAMING_UNLOADED;return WORLD_STREAMING_OK;
}
bool world_streaming_is_ready(const WorldStreamingDatabase *db,const WorldStreamingResidency *state,uint16_t id){
    if(!db||!db->data||!state)return false;
    int i=section_index(db,id);return i>=0&&state->state[i]==WORLD_STREAMING_READY;
}
