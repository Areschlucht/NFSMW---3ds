#include <3ds.h>
#include <citro3d.h>
#include <tex3ds.h>
#include <math.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "nfs_scene.h"
#include "garage_menu.h"
#include "bmw_vshader_shbin.h"

#define ROOT "sdmc:/3ds/nfsmw-bmw-viewer/"
#define TRANSFER_FLAGS (GX_TRANSFER_FLIP_VERT(0)|GX_TRANSFER_OUT_TILED(0)|GX_TRANSFER_RAW_COPY(0)|GX_TRANSFER_IN_FORMAT(GX_TRANSFER_FMT_RGBA8)|GX_TRANSFER_OUT_FORMAT(GX_TRANSFER_FMT_RGB8)|GX_TRANSFER_SCALING(GX_TRANSFER_SCALE_NO))

static NfsScene scene;
static C3D_Tex textures[NFS_MAX_TEXTURES];
static unsigned textures_loaded;
static NfsVertex *vertices;
static DVLB_s *shader;
static shaderProgram_s program;
static bool initialized,program_ready;
static C3D_RenderTarget *target;
static C3D_Mtx projection;
static int projection_loc,model_loc,lighting_loc;
static float centers[2048][3];
static unsigned render_order[2048];
static float render_distances[2048];
static char error_message[160];

static bool read_scene(void)
{
    FILE *file=fopen(ROOT "body.nfm","rb");
    if (!file) { snprintf(error_message,sizeof(error_message),"Cannot open body.nfm (%d)",errno);return false; }
    if (fseek(file,0,SEEK_END)) { fclose(file);return false; }
    long size=ftell(file);
    if (size<32 || size>8*1024*1024 || fseek(file,0,SEEK_SET)) { fclose(file);return false; }
    uint8_t *data=malloc((size_t)size);
    if (!data) { fclose(file);return false; }
    bool ok=fread(data,1,(size_t)size,file)==(size_t)size && !ferror(file);
    fclose(file);
    if (ok) {
        ok=nfs_scene_decode(data,(size_t)size,&scene);
        if (!ok) snprintf(error_message,sizeof(error_message),"Scene integrity/bounds check failed.");
    }
    free(data);
    return ok;
}

static bool initialize(void)
{
    snprintf(error_message,sizeof(error_message),"GPU context initialization failed.");
    if (!C3D_Init(C3D_DEFAULT_CMDBUF_SIZE)) return false;
    initialized=true;
    snprintf(error_message,sizeof(error_message),"Render target allocation failed.");
    target=C3D_RenderTargetCreate(240,400,GPU_RB_RGBA8,GPU_RB_DEPTH24_STENCIL8);
    if (!target) return false;
    C3D_RenderTargetSetOutput(target,GFX_TOP,GFX_LEFT,TRANSFER_FLAGS);
    snprintf(error_message,sizeof(error_message),"Vertex shader initialization failed.");
    shader=DVLB_ParseFile((u32*)bmw_vshader_shbin,bmw_vshader_shbin_size);
    if (!shader || !shader->numDVLE || R_FAILED(shaderProgramInit(&program))) return false;
    program_ready=true;
    if (R_FAILED(shaderProgramSetVsh(&program,&shader->DVLE[0]))) return false;
    C3D_BindProgram(&program);
    projection_loc=shaderInstanceGetUniformLocation(program.vertexShader,"projection");
    model_loc=shaderInstanceGetUniformLocation(program.vertexShader,"modelView");
    lighting_loc=shaderInstanceGetUniformLocation(program.vertexShader,"lighting");
    if (projection_loc<0 || model_loc<0 || lighting_loc<0) return false;
    snprintf(error_message,sizeof(error_message),"Vertex buffer allocation failed.");
    vertices=linearAlloc(scene.vertex_count*sizeof(*vertices));
    if (!vertices) return false;
    memcpy(vertices,scene.vertices,scene.vertex_count*sizeof(*vertices));
    for (uint32_t i=0;i<scene.vertex_count;++i) vertices[i].uv[1]=1-vertices[i].uv[1];
    GSPGPU_FlushDataCache(vertices,scene.vertex_count*sizeof(*vertices));
    for (uint32_t i=0;i<scene.batch_count;++i) {
        NfsBatch b=scene.batches[i];
        for (uint32_t v=b.first;v<b.first+b.count;++v)
            for (unsigned a=0;a<3;++a) centers[i][a]+=scene.vertices[v].position[a]/b.count;
    }
    free(scene.vertices);scene.vertices=NULL;
    C3D_AttrInfo *attrs=C3D_GetAttrInfo();AttrInfo_Init(attrs);
    AttrInfo_AddLoader(attrs,0,GPU_FLOAT,3);AttrInfo_AddLoader(attrs,1,GPU_FLOAT,3);AttrInfo_AddLoader(attrs,2,GPU_FLOAT,2);
    C3D_BufInfo *buffers=C3D_GetBufInfo();BufInfo_Init(buffers);
    if (BufInfo_Add(buffers,vertices,sizeof(*vertices),3,0x210)<0) return false;
    for (unsigned i=0;i<scene.texture_count;++i) {
        char path[160];snprintf(path,sizeof(path),ROOT "textures/%08lx.t3x",(unsigned long)scene.textures[i].key);
        snprintf(error_message,sizeof(error_message),"Cannot load texture %08lx.",(unsigned long)scene.textures[i].key);
        FILE *file=fopen(path,"rb");if (!file) return false;
        Tex3DS_Texture imported=Tex3DS_TextureImportStdio(file,&textures[i],NULL,false);
        fclose(file);
        if (!imported) return false;
        Tex3DS_TextureFree(imported);textures_loaded++;
        if (textures[i].width!=scene.textures[i].width || textures[i].height!=scene.textures[i].height) {
            snprintf(error_message,sizeof(error_message),"Texture %08lx size mismatch.",(unsigned long)scene.textures[i].key);return false;
        }
        C3D_TexSetFilter(&textures[i],GPU_LINEAR,GPU_NEAREST);
        C3D_TexSetWrap(&textures[i],GPU_REPEAT,GPU_REPEAT);
    }
    Mtx_PerspTilt(&projection,C3D_AngleFromDegrees(40),C3D_AspectRatioTop,0.1f,20,false);
    C3D_CullFace(GPU_CULL_NONE);
    C3D_AlphaTest(true,GPU_GREATER,0);
    C3D_AlphaBlend(GPU_BLEND_ADD,GPU_BLEND_ADD,GPU_SRC_ALPHA,GPU_ONE_MINUS_SRC_ALPHA,GPU_ONE,GPU_ONE_MINUS_SRC_ALPHA);
    error_message[0]=0;
    return true;
}

static void scene_shutdown(void)
{
    if (initialized) { C3D_Fini();initialized=false; }
    for (unsigned i=0;i<textures_loaded;++i) C3D_TexDelete(&textures[i]);
    if (vertices) linearFree(vertices);
    if (program_ready) shaderProgramFree(&program);
    if (shader) DVLB_Free(shader);
    nfs_scene_free(&scene);
}

static void render(float yaw,float pitch,float zoom,bool textured)
{
    C3D_RenderTargetClear(target,C3D_CLEAR_ALL,0x141414ff,0);
    C3D_FrameDrawOn(target);
    C3D_Mtx model;Mtx_Identity(&model);
    Mtx_Translate(&model,0,0,-3.4f/zoom,true);
    Mtx_RotateX(&model,pitch,true);Mtx_RotateY(&model,yaw,true);
    C3D_FVUnifMtx4x4(GPU_VERTEX_SHADER,projection_loc,&projection);
    C3D_FVUnifMtx4x4(GPU_VERTEX_SHADER,model_loc,&model);
    C3D_FVUnifSet(GPU_VERTEX_SHADER,lighting_loc,0.35f,0.65f,0,0);
    C3D_TexEnv *env=C3D_GetTexEnv(0);C3D_TexEnvInit(env);
    C3D_TexEnvSrc(env,C3D_Both,textured?GPU_TEXTURE0:GPU_PRIMARY_COLOR,GPU_PRIMARY_COLOR,0);
    C3D_TexEnvFunc(env,C3D_Both,textured?GPU_MODULATE:GPU_REPLACE);
    unsigned *order=render_order;float *distances=render_distances;unsigned count=0;
    float cy=cosf(yaw),sy=sinf(yaw),cp=cosf(pitch),sp=sinf(pitch);
    for (unsigned i=0;i<scene.batch_count;++i) {
        bool transparent=textured && (scene.textures[scene.batches[i].texture].flags&1);
        if (!transparent) {
            C3D_DepthTest(true,GPU_GREATER,GPU_WRITE_ALL);
            C3D_TexBind(0,&textures[scene.batches[i].texture]);
            C3D_DrawArrays(GPU_TRIANGLES,scene.batches[i].first,scene.batches[i].count);
        } else {
            float z=sp*centers[i][1]+cp*(-sy*centers[i][0]+cy*centers[i][2]);
            unsigned at=count;
            while (at && distances[at-1]<z) { order[at]=order[at-1];distances[at]=distances[at-1];--at; }
            order[at]=i;distances[at]=z;++count;
        }
    }
    C3D_DepthTest(true,GPU_GREATER,GPU_WRITE_COLOR);
    for (unsigned j=0;j<count;++j) {
        NfsBatch b=scene.batches[order[j]];
        C3D_TexBind(0,&textures[b.texture]);C3D_DrawArrays(GPU_TRIANGLES,b.first,b.count);
    }
}

static void status(const GarageUI *ui,bool textured,bool rotating)
{
    consoleClear();
    printf("NFS MW 3DS prototype v0.5\n\n");
    if (ui->screen==UI_MAIN) {
        const char *items[]={"Rockport drive (unavailable)","Garage","Controls","Quit"};
        for (unsigned i=0;i<4;++i) printf("%s %s\n",i==ui->selected?">":" ",items[i]);
        printf("\nUp/Down: choose\nA: select\nSTART: quit\n\nOriginal track data required\nfor driving.\n");
    } else if (ui->screen==UI_GARAGE) {
        printf("GARAGE\n%s | rotation %s\n\n",textured?"Textured":"Solid",rotating?"on":"off");
        printf("Circle Pad / D-pad: rotate\nA: pause/resume\nL/R: zoom out/in\nX: reset view\nSELECT: textures/solid\nB / START: main menu\n\n");
        printf("Body preview; wheels and\npaint skin remain unfinished.\n");
    } else if (ui->screen==UI_CONTROLS) {
        printf("GARAGE CONTROLS\n\nCircle Pad / D-pad: rotate\nA: pause/resume\nL/R: zoom out/in\nX: reset view\nSELECT: textures/solid\n\nDriving is not available\nuntil Rockport is decoded.\n\nA / B / START: main menu\n");
    } else if (ui->screen==UI_MAP_MISSING) {
        printf("ROCKPORT NOT AVAILABLE\n\nThe original track data\nis not installed/decoded.\n\nDriving cannot start yet.\nNo substitute map is included.\n\nA / B / START: main menu\n");
    }
}

int main(void)
{
    gfxInitDefault();gfxSet3D(false);consoleInit(GFX_BOTTOM,NULL);gfxSetDoubleBuffering(GFX_BOTTOM,false);
    bool ok=read_scene() && initialize();
    bool textured=true,rotating=true;GarageUI ui;garage_ui_reset(&ui);
    if (ok) status(&ui,textured,rotating);
    else printf("NFS MW prototype v0.5\n\n%s\n\nExtract the complete ZIP\nto the SD card root.\n\nSTART: exit\n",error_message[0]?error_message:"Scene read failed.");
    float yaw=0.65f,pitch=0.25f,zoom=1;u64 previous=osGetTime();
    while (aptMainLoop()) {
        hidScanInput();u32 pressed=hidKeysDown(),held=hidKeysHeld();
        if (!ok && (pressed&KEY_START)) break;
        GarageScreen previous_screen=ui.screen;unsigned previous_selection=ui.selected;
        uint32_t event=0;
        if (pressed&(KEY_UP|KEY_CPAD_UP)) event|=UI_UP;
        if (pressed&(KEY_DOWN|KEY_CPAD_DOWN)) event|=UI_DOWN;
        if (pressed&KEY_A) event|=UI_ACCEPT;
        if (pressed&KEY_B) event|=UI_BACK;
        if (pressed&KEY_START) event|=UI_START;
        if (ok) garage_ui_event(&ui,event);
        if (ui.screen==UI_QUIT) break;
        if (ui.screen==UI_GARAGE && previous_screen==UI_GARAGE) {
            if (pressed&KEY_A) rotating=!rotating;
            if (pressed&KEY_SELECT) textured=!textured;
        }
        if (ok && (previous_screen!=ui.screen || previous_selection!=ui.selected ||
            (ui.screen==UI_GARAGE && (pressed&(KEY_A|KEY_SELECT))))) status(&ui,textured,rotating);
        u64 now=osGetTime();float dt=(now-previous)*0.001f;previous=now;if (dt>0.05f) dt=0.05f;
        circlePosition pad={0};if (ui.screen==UI_GARAGE) hidCircleRead(&pad);
        float dx=abs(pad.dx)>15?pad.dx/156.0f:0,dy=abs(pad.dy)>15?pad.dy/156.0f:0;
        if (ui.screen==UI_GARAGE) { dx+=!!(held&KEY_RIGHT)-!!(held&KEY_LEFT);dy+=!!(held&KEY_UP)-!!(held&KEY_DOWN); }
        yaw=fmodf(yaw+dt*(dx*1.8f+(rotating?0.3f:0)),6.2831853f);pitch+=dt*dy*1.8f;
        if (pitch>1.4f) pitch=1.4f;
        if (pitch< -1.4f) pitch=-1.4f;
        if (ui.screen==UI_GARAGE) zoom+=dt*(!!(held&KEY_R)-!!(held&KEY_L));
        if (zoom<0.5f) zoom=0.5f;
        if (zoom>1.5f) zoom=1.5f;
        if (ui.screen==UI_GARAGE && (pressed&KEY_X)) { yaw=0.65f;pitch=0.25f;zoom=1; }
        if (ok) {
            if (C3D_FrameBegin(C3D_FRAME_SYNCDRAW)) { render(yaw,pitch,zoom,textured);gfxFlushBuffers();C3D_FrameEnd(0); }
        } else { gfxFlushBuffers();gfxSwapBuffers();gspWaitForVBlank(); }
    }
    scene_shutdown();gfxExit();return 0;
}
