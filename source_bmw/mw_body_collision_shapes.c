#include "mw_body_collision_shapes.h"
#include <math.h>
#include <string.h>
static unsigned u16(const unsigned char *p){return (unsigned)p[0]|((unsigned)p[1]<<8);}
static int s16(const unsigned char *p){unsigned v=u16(p);return v&32768?(int)v-65536:(int)v;}
static uint32_t u32(const unsigned char *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static float f32le(const unsigned char *p){uint32_t value=u32(p);float out;memcpy(&out,&value,4);return out;}
int mw_body_collision_compound_open(const void *bytes,size_t size,uint32_t expected,MwBodyCollisionCompound *out){
    if(!bytes||!out||size<32||size>UINT32_MAX)return MW_BODY_SHAPE_INVALID;
    const unsigned char *p=bytes;uint32_t key=u32(p),count=u32(p+4);
    if(key!=expected||u32(p+8)||u32(p+12)||!count||count>4096||count>(size-32)/48)return MW_BODY_SHAPE_INVALID;
    size_t mesh_header=16+count*48u;uint32_t meshes=u32(p+mesh_header);
    if(meshes>MW_BODY_COLLISION_MAX_MESHES||u32(p+mesh_header+4)||u32(p+mesh_header+8)||u32(p+mesh_header+12))return MW_BODY_SHAPE_INVALID;
    MwBodyCollisionCompound result;memset(&result,0,sizeof result);result.data=p;result.bytes=size;result.model_key=key;result.bound_count=count;result.mesh_count=meshes;
    size_t at=mesh_header+16;
    for(uint32_t i=0;i<meshes;i++){
        if(at>size||size-at<16)return MW_BODY_SHAPE_INVALID;
        uint32_t vertices=u32(p+at);if(!vertices||vertices>65535||vertices>(size-at-16)/16||u32(p+at+4)||u32(p+at+8)||u32(p+at+12))return MW_BODY_SHAPE_INVALID;
        result.mesh_offsets[i]=(uint32_t)at;
        for(uint32_t j=0;j<vertices*4;j++)if(!isfinite(f32le(p+at+16+j*4)))return MW_BODY_SHAPE_INVALID;
        at+=16+vertices*16u;
    }
    if(at!=size)return MW_BODY_SHAPE_INVALID;
    for(uint32_t i=0;i<count;i++){
        const unsigned char *r=p+16+i*48;unsigned children=r[22];int first=s16(r+30),mesh=(int)(int8_t)r[23];float radius=f32le(r+32);
        if(s16(r+16)<0||s16(r+18)<0||s16(r+20)<0||!isfinite(radius)||radius<0||u32(r+44))return MW_BODY_SHAPE_INVALID;
        if(children&&(first<0||(uint32_t)first<=i||(uint32_t)first+children>count))return MW_BODY_SHAPE_INVALID;
        if(!children&&first!=-1)return MW_BODY_SHAPE_INVALID;
        if(mesh< -1||(mesh>=0&&(unsigned)mesh>=meshes)||((u16(r+14)&16)&&mesh<0))return MW_BODY_SHAPE_INVALID;
    }
    *out=result;return 0;
}
int mw_body_collision_bound(const MwBodyCollisionCompound *c,unsigned index,MwBodyCollisionBound *out){
    if(!c||!c->data||!out||index>=c->bound_count)return MW_BODY_SHAPE_INVALID;
    const unsigned char *p=c->data+16+index*48;
    for(unsigned a=0;a<4;a++)out->quaternion[a]=s16(p+a*2)*(1.0f/32767.0f);
    for(unsigned a=0;a<3;a++){out->center[a]=s16(p+8+a*2)*0.001f;out->half_extents[a]=s16(p+16+a*2)*0.001f;}
    out->radius=f32le(p+32);out->material_key=u32(p+36);out->token=u32(p+40);out->source_flags=(uint16_t)u16(p+14);out->child_count=p[22];out->mesh_index=(int8_t)p[23];out->first_child=(int16_t)s16(p+30);return 0;
}
unsigned mw_body_collision_mesh_count(const MwBodyCollisionCompound *c,unsigned mesh){return c&&c->data&&mesh<c->mesh_count?u32(c->data+c->mesh_offsets[mesh]):0;}
int mw_body_collision_mesh_vertex(const MwBodyCollisionCompound *c,unsigned mesh,unsigned index,float out[4]){
    if(!c||!c->data||!out||mesh>=c->mesh_count||index>=mw_body_collision_mesh_count(c,mesh))return MW_BODY_SHAPE_INVALID;
    const unsigned char *p=c->data+c->mesh_offsets[mesh]+16+index*16;for(unsigned a=0;a<4;a++)out[a]=f32le(p+a*4);return 0;
}
int mw_body_collision_primitive(const MwBodyCollisionBound *b,const float pad[3],MwBodyCollisionShape *out){
    if(!b||!pad||!out)return MW_BODY_SHAPE_INVALID;
    unsigned flags=b->source_flags,runtime=0;
    if(!(flags&14)||!(flags&(64|128)))return 0;
    for(unsigned a=0;a<3;a++)if(!isfinite(pad[a])||!isfinite(b->center[a])||!isfinite(b->half_extents[a]))return MW_BODY_SHAPE_INVALID;
    if(!isfinite(b->radius)||b->radius<0)return MW_BODY_SHAPE_INVALID;
    if(flags&1)runtime|=8;
    if(flags&8)runtime|=4;
    if(flags&2)runtime|=1;
    if(flags&4)runtime|=2;
    MwBodyCollisionShape result;memset(&result,0,sizeof result);result.source_flags=(uint16_t)flags;result.material_key=b->material_key;result.token=b->token;result.runtime_flags=(uint16_t)runtime;result.radius=b->radius;
    for(unsigned a=0;a<3;a++)result.center[a]=b->center[a];
    if(flags&64){
        result.kind=1;for(unsigned a=0;a<3;a++){result.half_extents[a]=b->half_extents[a]+pad[a];if(!isfinite(result.half_extents[a])||result.half_extents[a]<0)return MW_BODY_SHAPE_INVALID;}
        for(unsigned a=0;a<4;a++){if(!isfinite(b->quaternion[a]))return MW_BODY_SHAPE_INVALID;result.quaternion[a]=b->quaternion[a];}
    }else{
        result.kind=2;result.runtime_flags|=16;result.quaternion[3]=1;
        for(unsigned a=0;a<3;a++)result.half_extents[a]=b->radius;
    }
    *out=result;return 1;
}
int mw_body_collision_static_children(const MwBodyCollisionCompound *c,unsigned root,const float pad[3],MwBodyCollisionShape *out,size_t capacity,size_t *count){
    if(!c||!pad||!count||(!out&&capacity))return MW_BODY_SHAPE_INVALID;
    MwBodyCollisionBound parent;if(mw_body_collision_bound(c,root,&parent)<0)return MW_BODY_SHAPE_INVALID;
    if(!parent.child_count){*count=0;return MW_BODY_SHAPE_ROOT_PATH_REQUIRED;}
    size_t needed=0;int any=0;
    for(unsigned child=0;child<parent.child_count;child++){
        MwBodyCollisionBound b;MwBodyCollisionShape shape;unsigned index=(unsigned)parent.first_child+child;if(mw_body_collision_bound(c,index,&b)<0)return MW_BODY_SHAPE_INVALID;
        if(b.source_flags&32)continue;
        int made=mw_body_collision_primitive(&b,pad,&shape);if(made<0)return made;if(made)any=1;
        if((b.source_flags&16)&&b.mesh_index>=0)any=1;
        if(made&&(shape.runtime_flags&1)&&!(shape.runtime_flags&8))needed++;
    }
    *count=needed;if(!any)return MW_BODY_SHAPE_ROOT_PATH_REQUIRED;if(needed>capacity)return MW_BODY_SHAPE_CAPACITY;
    size_t at=0;for(unsigned child=0;child<parent.child_count;child++){
        MwBodyCollisionBound b;MwBodyCollisionShape shape;unsigned index=(unsigned)parent.first_child+child;mw_body_collision_bound(c,index,&b);if(b.source_flags&32)continue;
        if(mw_body_collision_primitive(&b,pad,&shape)==1&&(shape.runtime_flags&1)&&!(shape.runtime_flags&8)){shape.bound_index=(uint16_t)index;out[at++]=shape;}
    }
    return 0;
}
