#ifndef TEST_CITRO3D_H
#define TEST_CITRO3D_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
typedef uint8_t u8;typedef uint16_t u16;typedef uint32_t u32;
typedef struct {float x,y,z,w;} C3D_FVec;
typedef struct {C3D_FVec r[4];} C3D_Mtx;
typedef struct {void *data;size_t size;u16 width,height;} C3D_Tex;
typedef struct {void *pointer;int stride;} C3D_BufInfo;
typedef struct {int unused;} C3D_AttrInfo;
typedef struct {int unused;} C3D_TexEnv;
typedef struct {int unused;} shaderProgram_s;
enum {GPU_FLOAT,GPU_RGBA8,GPU_LINEAR,GPU_NEAREST,GPU_REPEAT,GPU_VERTEX_SHADER,
 GPU_CULL_NONE,GPU_TEXTURE0,GPU_PRIMARY_COLOR,GPU_MODULATE,GPU_GREATER,
 GPU_WRITE_COLOR,GPU_WRITE_ALL,GPU_BLEND_ADD,GPU_SRC_ALPHA,GPU_ONE,
 GPU_ONE_MINUS_SRC_ALPHA,GPU_ZERO,GPU_TRIANGLES,C3D_UNSIGNED_SHORT,C3D_Both};
static inline C3D_FVec FVec3_New(float x,float y,float z){return (C3D_FVec){x,y,z,0};}
static inline C3D_FVec FVec4_New(float x,float y,float z,float w){return (C3D_FVec){x,y,z,w};}
void Mtx_Identity(C3D_Mtx *);
void Mtx_Multiply(C3D_Mtx *,const C3D_Mtx *,const C3D_Mtx *);
void Mtx_LookAt(C3D_Mtx *,C3D_FVec,C3D_FVec,C3D_FVec,bool);
void C3D_FrameSync(void);
void *linearMemAlign(size_t,size_t);
void linearFree(void *);
void GSPGPU_FlushDataCache(void *,u32);
void BufInfo_Init(C3D_BufInfo *);
int BufInfo_Add(C3D_BufInfo *,void *,int,int,unsigned long long);
bool C3D_TexInit(C3D_Tex *,u16,u16,int);
void C3D_TexDelete(C3D_Tex *);
void C3D_TexFlush(C3D_Tex *);
void C3D_TexSetFilter(C3D_Tex *,int,int);
void C3D_TexSetWrap(C3D_Tex *,int,int);
void C3D_BindProgram(shaderProgram_s *);
void C3D_SetAttrInfo(C3D_AttrInfo *);
void C3D_CullFace(int);
void C3D_FVUnifMtx4x4(int,int,const C3D_Mtx *);
C3D_TexEnv *C3D_GetTexEnv(int);
void C3D_TexEnvInit(C3D_TexEnv *);
void C3D_TexEnvSrc(C3D_TexEnv *,int,int,int,int);
void C3D_TexEnvFunc(C3D_TexEnv *,int,int);
void C3D_SetBufInfo(C3D_BufInfo *);
void C3D_TexBind(int,C3D_Tex *);
void C3D_AlphaTest(bool,int,u8);
void C3D_DepthTest(bool,int,int);
void C3D_AlphaBlend(int,int,int,int,int,int);
void C3D_DrawElements(int,int,int,const void *);
void AttrInfo_Init(C3D_AttrInfo *);
void AttrInfo_AddLoader(C3D_AttrInfo *,int,int,int);
extern size_t mock_linear_used,mock_linear_limit;
extern unsigned mock_draw_calls,mock_frame_syncs,mock_linear_allocations;
extern uint64_t mock_draw_stream_hash;
#endif
