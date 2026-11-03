#include <3ds.h>
#include <citro3d.h>
#include "brake_gpu.h"
#include "brake_gpu_mesh.h"
#include "brake_vshader_shbin.h"

#define TRANSFER_FLAGS (GX_TRANSFER_FLIP_VERT(0) | GX_TRANSFER_OUT_TILED(0) | GX_TRANSFER_RAW_COPY(0) | GX_TRANSFER_IN_FORMAT(GX_TRANSFER_FMT_RGBA8) | GX_TRANSFER_OUT_FORMAT(GX_TRANSFER_FMT_RGB8) | GX_TRANSFER_SCALING(GX_TRANSFER_SCALE_NO))

static C3D_RenderTarget *target;
static DVLB_s *shader;
static shaderProgram_s program;
static bool program_ready,renderer_ready;
static BrakeGpuVertex *vertices;
static size_t vertex_count;
static bool lines;
static int projection_location,model_location,lighting_location;
static C3D_Mtx projection;

bool brake_gpu_init(void)
{
    if (!C3D_Init(C3D_DEFAULT_CMDBUF_SIZE)) return false;
    renderer_ready=true;
    target=C3D_RenderTargetCreate(240,400,GPU_RB_RGBA8,GPU_RB_DEPTH24_STENCIL8);
    if (!target) goto failed;
    C3D_RenderTargetSetOutput(target,GFX_TOP,GFX_LEFT,TRANSFER_FLAGS);
    shader=DVLB_ParseFile((u32*)brake_vshader_shbin,brake_vshader_shbin_size);
    if (!shader || !shader->numDVLE) goto failed;
    if (R_FAILED(shaderProgramInit(&program))) goto failed;
    program_ready=true;
    if (R_FAILED(shaderProgramSetVsh(&program,&shader->DVLE[0]))) goto failed;
    C3D_BindProgram(&program);
    projection_location=shaderInstanceGetUniformLocation(program.vertexShader,"projection");
    model_location=shaderInstanceGetUniformLocation(program.vertexShader,"modelView");
    lighting_location=shaderInstanceGetUniformLocation(program.vertexShader,"lighting");
    if (projection_location<0 || model_location<0 || lighting_location<0) goto failed;
    vertices=linearAlloc(sizeof(*vertices)*BRAKE_GPU_MAX_VERTICES);
    if (!vertices) goto failed;
    C3D_AttrInfo *attrs=C3D_GetAttrInfo();
    AttrInfo_Init(attrs);
    AttrInfo_AddLoader(attrs,0,GPU_FLOAT,3);
    AttrInfo_AddLoader(attrs,1,GPU_FLOAT,3);
    C3D_BufInfo *buffers=C3D_GetBufInfo();
    BufInfo_Init(buffers);
    if (BufInfo_Add(buffers,vertices,sizeof(*vertices),2,0x10)<0) goto failed;
    Mtx_PerspTilt(&projection,C3D_AngleFromDegrees(40),C3D_AspectRatioTop,0.1f,20,false);
    C3D_CullFace(GPU_CULL_NONE);
    C3D_DepthTest(true,GPU_GREATER,GPU_WRITE_ALL);
    C3D_TexEnv *env=C3D_GetTexEnv(0);
    C3D_TexEnvInit(env);
    C3D_TexEnvSrc(env,C3D_Both,GPU_PRIMARY_COLOR,0,0);
    C3D_TexEnvFunc(env,C3D_Both,GPU_REPLACE);
    return true;
failed:
    brake_gpu_shutdown();
    return false;
}

bool brake_gpu_set_mesh(const BrakeMesh *mesh, bool wireframe)
{
    /* Call only before the first frame, or inside a synchronized frame. */
    if (!vertices) return false;
    vertex_count=brake_gpu_mesh(mesh,wireframe,vertices,BRAKE_GPU_MAX_VERTICES);
    lines=wireframe;
    if (!vertex_count) return false;
    GSPGPU_FlushDataCache(vertices,vertex_count*sizeof(*vertices));
    return true;
}

void brake_gpu_draw(float yaw,float pitch,float zoom)
{
    if (!renderer_ready || !vertex_count) return;
    C3D_RenderTargetClear(target,C3D_CLEAR_ALL,0x0c0c0cff,0);
    C3D_FrameDrawOn(target);
    C3D_Mtx model;
    Mtx_Identity(&model);
    Mtx_Translate(&model,0,0,-4.0f/zoom,true);
    Mtx_RotateX(&model,pitch,true);
    Mtx_RotateY(&model,yaw,true);
    C3D_FVUnifMtx4x4(GPU_VERTEX_SHADER,projection_location,&projection);
    C3D_FVUnifMtx4x4(GPU_VERTEX_SHADER,model_location,&model);
    C3D_FVUnifSet(GPU_VERTEX_SHADER,lighting_location,lines?0.9f:55.0f/255,lines?0:190.0f/255,0,0);
    C3D_DrawArrays(GPU_TRIANGLES,0,vertex_count);
}

void brake_gpu_shutdown(void)
{
    /* Fini drains the graphics queue and destroys render targets before we free
       memory that an in-flight draw could still reference. */
    if (renderer_ready) { C3D_Fini();renderer_ready=false;target=NULL; }
    if (vertices) { linearFree(vertices);vertices=NULL; }
    if (program_ready) { shaderProgramFree(&program);program_ready=false; }
    if (shader) { DVLB_Free(shader);shader=NULL; }
    vertex_count=0;
}
