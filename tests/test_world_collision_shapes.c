#include "mw_body_collision_shapes.h"
#include <assert.h>
#include <math.h>
#include <string.h>
static void put16(unsigned char *p,int value){unsigned v=(unsigned)value;p[0]=(unsigned char)v;p[1]=(unsigned char)(v>>8);}
static void put32(unsigned char *p,uint32_t v){for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(v>>(i*8));}
static void putf(unsigned char *p,float v){uint32_t u;memcpy(&u,&v,4);put32(p,u);}
static void bound(unsigned char *p,unsigned flags){put16(p+6,32767);put16(p+14,(int)flags);p[23]=255;put16(p+30,-1);put32(p+36,0x99da6531);}
int main(void){
    unsigned char data[288]={0};put32(data,0xcafebabe);put32(data+4,4);
    bound(data+16,64);data[16+22]=3;put16(data+16+30,1);
    unsigned char *box=data+64,*sphere=data+112,*meshbound=data+160;
    bound(box,70);put16(box+8,-4);put16(box+10,-244);put16(box+12,-1);put16(box+16,934);put16(box+18,376);put16(box+20,2289);putf(box+32,2.5f);
    bound(sphere,130);put16(sphere,32767);put16(sphere+6,0);put16(sphere+16,328);put16(sphere+18,328);put16(sphere+20,328);putf(sphere+32,.328597f);
    bound(meshbound,80);meshbound[23]=0;
    put32(data+208,1);put32(data+224,3);putf(data+256,1);putf(data+276,1);
    MwBodyCollisionCompound compound;assert(mw_body_collision_compound_open(data,sizeof data,0xcafebabe,&compound)==0);
    assert(compound.bound_count==4&&compound.mesh_count==1&&mw_body_collision_mesh_count(&compound,0)==3);
    float vertex[4];assert(mw_body_collision_mesh_vertex(&compound,0,1,vertex)==0&&vertex[0]==1);
    assert(mw_body_collision_mesh_vertex(&compound,0,3,vertex)==MW_BODY_SHAPE_INVALID);
    MwBodyCollisionBound raw;assert(mw_body_collision_bound(&compound,1,&raw)==0&&raw.material_key==0x99da6531);
    assert(fabsf(raw.center[1]+.244f)<.000001f&&raw.source_flags==70);
    MwBodyCollisionShape shapes[3];size_t count;float pad[3]={.01f,.02f,.03f};
    assert(mw_body_collision_static_children(&compound,0,pad,shapes,3,&count)==0&&count==2);
    assert(shapes[0].bound_index==1&&shapes[0].kind==1&&shapes[0].runtime_flags==3);
    assert(fabsf(shapes[0].half_extents[0]-.944f)<.000001f);
    assert(shapes[1].bound_index==2&&shapes[1].kind==2&&shapes[1].runtime_flags==17);
    assert(shapes[1].half_extents[0]==.328597f&&shapes[1].quaternion[0]==0&&shapes[1].quaternion[3]==1);
    memset(shapes,0xaa,sizeof shapes);assert(mw_body_collision_static_children(&compound,0,pad,shapes,1,&count)==MW_BODY_SHAPE_CAPACITY&&count==2);
    assert(((unsigned char*)shapes)[0]==0xaa);
    put16(box+14,71);assert(mw_body_collision_static_children(&compound,0,pad,shapes,3,&count)==0&&count==1);put16(box+14,70);
    assert(mw_body_collision_static_children(&compound,1,pad,shapes,3,&count)==MW_BODY_SHAPE_ROOT_PATH_REQUIRED);
    assert(mw_body_collision_compound_open(data,sizeof data-1,0xcafebabe,&compound)==MW_BODY_SHAPE_INVALID);
    assert(mw_body_collision_compound_open(data,sizeof data,1,&compound)==MW_BODY_SHAPE_INVALID);
    put32(data+8,1);assert(mw_body_collision_compound_open(data,sizeof data,0xcafebabe,&compound)==MW_BODY_SHAPE_INVALID);put32(data+8,0);
    data[160+23]=1;assert(mw_body_collision_compound_open(data,sizeof data,0xcafebabe,&compound)==MW_BODY_SHAPE_INVALID);data[160+23]=0;
    put16(data+46,2);assert(mw_body_collision_compound_open(data,sizeof data,0xcafebabe,&compound)==MW_BODY_SHAPE_INVALID);put16(data+46,1);
    putf(data+240,NAN);assert(mw_body_collision_compound_open(data,sizeof data,0xcafebabe,&compound)==MW_BODY_SHAPE_INVALID);
    return 0;
}
