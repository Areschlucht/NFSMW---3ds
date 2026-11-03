#define _POSIX_C_SOURCE 200112L
#include "citro3d.h"
#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
size_t mock_linear_used=0,mock_linear_limit=SIZE_MAX;
unsigned mock_draw_calls=0,mock_frame_syncs=0,mock_linear_allocations=0;
uint64_t mock_draw_stream_hash=UINT64_C(14695981039346656037);
static bool in_flight;
static struct {void *pointer;size_t bytes;} allocations[8192];
static C3D_BufInfo *bound;
static C3D_TexEnv environment;
static C3D_Mtx model_matrix;
static uint64_t texture_hash;
static int alpha_state[3],depth_state[3],blend_state[6];
static uint64_t hash_bytes(uint64_t hash,const void *data,size_t bytes){const unsigned char *p=data;for(size_t i=0;i<bytes;i++){hash^=p[i];hash*=UINT64_C(1099511628211);}return hash;}
void C3D_FrameSync(void){in_flight=false;mock_frame_syncs++;}
void *linearMemAlign(size_t size,size_t alignment){
    if(size>mock_linear_limit-mock_linear_used)return NULL;
    void *p=NULL;if(posix_memalign(&p,alignment,size))return NULL;
    for(unsigned i=0;i<8192;i++)if(!allocations[i].pointer){allocations[i].pointer=p;allocations[i].bytes=size;mock_linear_used+=size;mock_linear_allocations++;return p;}
    abort();
}
void linearFree(void *p){
    assert(!in_flight);
    for(unsigned i=0;i<8192;i++)if(allocations[i].pointer==p){mock_linear_used-=allocations[i].bytes;allocations[i].pointer=NULL;free(p);return;}
    abort();
}
void GSPGPU_FlushDataCache(void *p,u32 bytes){assert(p&&bytes);}
void BufInfo_Init(C3D_BufInfo *b){memset(b,0,sizeof(*b));}
int BufInfo_Add(C3D_BufInfo *b,void *p,int stride,int attributes,unsigned long long permutation){assert(stride==36&&attributes==3&&permutation==0x210);b->pointer=p;b->stride=stride;return 0;}
bool C3D_TexInit(C3D_Tex *t,u16 w,u16 h,int format){assert(format==GPU_RGBA8);t->size=(size_t)w*h*4;t->width=w;t->height=h;t->data=linearMemAlign(t->size,128);return t->data!=NULL;}
void C3D_TexDelete(C3D_Tex *t){linearFree(t->data);t->data=NULL;}
void C3D_TexFlush(C3D_Tex *t){assert(t->data);}
void C3D_TexSetFilter(C3D_Tex *t,int a,int b){(void)t;(void)a;(void)b;}
void C3D_TexSetWrap(C3D_Tex *t,int a,int b){(void)t;(void)a;(void)b;}
void C3D_BindProgram(shaderProgram_s *p){assert(p);}
void C3D_SetAttrInfo(C3D_AttrInfo *p){assert(p);}
void C3D_CullFace(int a){(void)a;}
void C3D_FVUnifMtx4x4(int stage,int location,const C3D_Mtx *m){(void)stage;for(unsigned r=0;r<4;r++)for(unsigned c=0;c<4;c++)assert(isfinite(((const float *)&m->r[r])[c]));if(location==1)model_matrix=*m;}
C3D_TexEnv *C3D_GetTexEnv(int stage){assert(stage==0);return &environment;}
void C3D_TexEnvInit(C3D_TexEnv *p){(void)p;}
void C3D_TexEnvSrc(C3D_TexEnv *p,int a,int b,int c,int d){(void)p;(void)a;(void)b;(void)c;(void)d;}
void C3D_TexEnvFunc(C3D_TexEnv *p,int a,int b){(void)p;(void)a;(void)b;}
void C3D_SetBufInfo(C3D_BufInfo *b){bound=b;}
void C3D_TexBind(int unit,C3D_Tex *t){assert(unit==0&&t->data);texture_hash=hash_bytes(UINT64_C(14695981039346656037),t->data,t->size);}
void C3D_AlphaTest(bool enabled,int mode,u8 reference){assert(mode==GPU_GREATER&&reference==40);alpha_state[0]=enabled;alpha_state[1]=mode;alpha_state[2]=reference;}
void C3D_DepthTest(bool enabled,int mode,int mask){assert(enabled&&mode==GPU_GREATER);depth_state[0]=enabled;depth_state[1]=mode;depth_state[2]=mask;}
void C3D_AlphaBlend(int a,int b,int c,int d,int e,int f){blend_state[0]=a;blend_state[1]=b;blend_state[2]=c;blend_state[3]=d;blend_state[4]=e;blend_state[5]=f;}
void C3D_DrawElements(int primitive,int count,int type,const void *indices){
    assert(primitive==GPU_TRIANGLES&&count>0&&count%3==0&&type==C3D_UNSIGNED_SHORT&&bound&&bound->pointer&&indices);
    const uint16_t *ix=indices;
    for(int i=0;i<count;i++){
        mock_draw_stream_hash=hash_bytes(mock_draw_stream_hash,(const unsigned char *)bound->pointer+(size_t)ix[i]*(size_t)bound->stride,(size_t)bound->stride);
        mock_draw_stream_hash=hash_bytes(mock_draw_stream_hash,&model_matrix,sizeof(model_matrix));
        mock_draw_stream_hash=hash_bytes(mock_draw_stream_hash,&texture_hash,sizeof(texture_hash));
        mock_draw_stream_hash=hash_bytes(mock_draw_stream_hash,alpha_state,sizeof(alpha_state));
        mock_draw_stream_hash=hash_bytes(mock_draw_stream_hash,depth_state,sizeof(depth_state));
        mock_draw_stream_hash=hash_bytes(mock_draw_stream_hash,blend_state,sizeof(blend_state));
    }
    mock_draw_calls++;in_flight=true;
}
void AttrInfo_Init(C3D_AttrInfo *a){memset(a,0,sizeof(*a));}
void AttrInfo_AddLoader(C3D_AttrInfo *a,int index,int type,int n){(void)a;assert(index>=0&&index<3&&type==GPU_FLOAT&&n>=2&&n<=4);}
void Mtx_Identity(C3D_Mtx *m){memset(m,0,sizeof(*m));m->r[0].x=m->r[1].y=m->r[2].z=m->r[3].w=1;}
void Mtx_Multiply(C3D_Mtx *out,const C3D_Mtx *a,const C3D_Mtx *b){C3D_Mtx result={0};for(unsigned r=0;r<4;r++)for(unsigned c=0;c<4;c++)for(unsigned k=0;k<4;k++)((float *)&result.r[r])[c]+=((const float *)&a->r[r])[k]*((const float *)&b->r[k])[c];*out=result;}
static C3D_FVec normal(C3D_FVec v){float n=sqrtf(v.x*v.x+v.y*v.y+v.z*v.z);assert(n>0);return FVec3_New(v.x/n,v.y/n,v.z/n);}
static C3D_FVec cross(C3D_FVec a,C3D_FVec b){return FVec3_New(a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x);}
void Mtx_LookAt(C3D_Mtx *m,C3D_FVec eye,C3D_FVec at,C3D_FVec up,bool left){assert(!left&&eye.x==0&&eye.y==0&&eye.z==0);C3D_FVec f=normal(at),r=normal(cross(f,up)),u=cross(r,f);Mtx_Identity(m);m->r[0]=r;m->r[1]=u;m->r[2]=FVec3_New(-f.x,-f.y,-f.z);}
