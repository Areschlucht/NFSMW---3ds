#include <3ds.h>
#include <citro3d.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include "brake_mesh.h"
#include "brake_gpu.h"

#define ASSET_PATH "sdmc:/3ds/nfsmw-brake-viewer/brakes-geometry.bin"

static BrakePackage package;

static bool load(void)
{
    FILE *file=fopen(ASSET_PATH,"rb");
    if (!file) return false;
    u8 data[BRAKE_SAMPLE_BYTES];
    size_t count=fread(data,1,sizeof(data),file);
    int extra=fgetc(file);
    bool valid=!ferror(file) && extra==EOF && brake_package_decode(data,count,&package);
    fclose(file);
    return valid;
}

static void status(unsigned selected, bool wireframe, bool rotating)
{
    consoleClear();
    const BrakeMesh *mesh=&package.models[selected];
    printf("NFS MW GPU viewer v0.3\n\nModel %u / %u\n%s\n%u positions / %u triangles\n\n",
           selected+1,(unsigned)package.model_count,mesh->name,
           (unsigned)mesh->vertex_count,(unsigned)mesh->face_count);
    printf("X / Y: next / previous model\nSELECT: shaded / wireframe\nCircle Pad / D-pad: rotate\nA: pause/resume rotation\nL / R: zoom out / in\nB: reset view\nSTART: exit\n\n");
    printf("GPU %s | rotation %s\nNo textures or gameplay\n",
           wireframe?"Wireframe":"Shaded",rotating?"on":"off");
}

int main(void)
{
    gfxInitDefault();
    gfxSet3D(false);
    consoleInit(GFX_BOTTOM,NULL);
    gfxSetDoubleBuffering(GFX_BOTTOM,false);
    bool decoded=load();
    bool gpu=decoded && brake_gpu_init();
    bool loaded=gpu && brake_gpu_set_mesh(&package.models[0],false);
    unsigned selected=0;
    bool rotating=true,wireframe=false,mesh_dirty=false;
    if (loaded) status(selected,wireframe,rotating);
    else printf("NFS MW GPU viewer v0.3\n\n%s\n\nExpected sample at:\n/3ds/nfsmw-brake-viewer/\nbrakes-geometry.bin\n\nSTART: exit\n",
                decoded?"GPU initialization failed.":"Asset missing or unsupported.");
    float yaw=0,pitch=-0.8f,zoom=1;
    u64 previous=osGetTime();
    while (aptMainLoop()) {
        hidScanInput();
        u32 pressed=hidKeysDown(),held=hidKeysHeld();
        if (pressed&KEY_START) break;
        u64 now=osGetTime();
        float dt=(now-previous)*0.001f;
        previous=now;
        if (dt>0.05f) dt=0.05f;
        if (pressed&KEY_A) rotating=!rotating;
        if (pressed&KEY_SELECT) wireframe=!wireframe;
        if (loaded) {
            if (pressed&KEY_X) selected=(selected+1)%package.model_count;
            if (pressed&KEY_Y) selected=(selected+package.model_count-1)%package.model_count;
            if (pressed&(KEY_X|KEY_Y|KEY_A|KEY_SELECT)) status(selected,wireframe,rotating);
            mesh_dirty|=!!(pressed&(KEY_X|KEY_Y|KEY_SELECT));
        }
        circlePosition pad;
        hidCircleRead(&pad);
        float horizontal=abs(pad.dx)>15?pad.dx/156.0f:0;
        float vertical=abs(pad.dy)>15?pad.dy/156.0f:0;
        horizontal+=!!(held&KEY_RIGHT)-!!(held&KEY_LEFT);
        vertical+=!!(held&KEY_UP)-!!(held&KEY_DOWN);
        yaw+=dt*(horizontal*1.8f+(rotating?0.45f:0));
        pitch+=dt*vertical*1.8f;
        if (pitch>1.5f) pitch=1.5f;
        if (pitch< -1.5f) pitch=-1.5f;
        yaw=fmodf(yaw,6.2831853f);
        zoom+=dt*(!!(held&KEY_R)-!!(held&KEY_L));
        if (zoom<0.5f) zoom=0.5f;
        if (zoom>1.7f) zoom=1.7f;
        if (pressed&KEY_B) { yaw=0;pitch=-0.8f;zoom=1; }
        if (loaded) {
            if (C3D_FrameBegin(C3D_FRAME_SYNCDRAW)) {
                if (mesh_dirty) {
                    if (!brake_gpu_set_mesh(&package.models[selected],wireframe)) {
                        consoleClear();printf("Mesh preparation failed.\nSTART: exit\n");loaded=false;
                    }
                    mesh_dirty=false;
                }
                if (loaded) brake_gpu_draw(yaw,pitch,zoom);
                gfxFlushBuffers();
                C3D_FrameEnd(0);
            }
        } else {
            gfxFlushBuffers();
            gfxSwapBuffers();
            gspWaitForVBlank();
        }
    }
    if (gpu) brake_gpu_shutdown();
    gfxExit();
    return 0;
}
