#include <3ds.h>
#include <citro3d.h>
#include <citro2d.h>
#include <tex3ds.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <errno.h>
#include "nfs_scene.h"
#include "road_contact.h"
#include "wheel_motion.h"
#include "road_pose.h"
#include "road_map.h"
#include "world_visibility.h"
#include "chase_camera.h"
#include "world_vertex.h"
#include "world_index.h"
#include "mw_ui.h"
#include "mw_alias.h"
#include "mw_race_session.h"
#include "mw_ui_texture.h"
#include "mw_color_grade.h"
#ifdef NFS_STREAMED_WORLD
#include "streamed_world.h"
#include "streamed_drive.h"
#include "streamed_world_pack.h"
#endif
#include "rockport_vshader_shbin.h"
#include "world_vshader_shbin.h"
#define ROOT "sdmc:/3ds/nfsmw-rockport/"
#define BUILD_VERSION "0.18"
#ifdef NFS_STREAMED_WORLD_PROBE
#ifndef NFS_STREAMED_WORLD
#error "Streamed probe requires NFS_STREAMED_WORLD"
#endif
#define DRIVE_FAR_WORLD 350.0f
#else
#define DRIVE_FAR_WORLD 700.0f
#endif
#define TRANSFER_FLAGS (GX_TRANSFER_FLIP_VERT(0)|GX_TRANSFER_OUT_TILED(0)|GX_TRANSFER_RAW_COPY(0)|GX_TRANSFER_IN_FORMAT(GX_TRANSFER_FMT_RGBA8)|GX_TRANSFER_OUT_FORMAT(GX_TRANSFER_FMT_RGB8)|GX_TRANSFER_SCALING(GX_TRANSFER_SCALE_NO))
typedef struct { NfsScene scene;NfsVertex *vertices;void *gpu_vertices;uint16_t *indices;WorldBounds *bounds;C3D_Tex textures[NFS_MAX_TEXTURES];unsigned loaded;uint32_t asset_crc;C3D_BufInfo buffer; } Mesh;
typedef enum { MENU,DRIVE,GARAGE,CONTROLS,QUIT,DISPLAY } Screen;
static Mesh world,body;
typedef enum { FE_TITLE,FE_ALIASES,FE_MAIN,FE_CAREER,FE_QUICK,FE_CHALLENGE,FE_OPTIONS,FE_DELETE,FE_RACE_SETUP } FrontendPage;
static FrontendPage frontend_page=FE_TITLE;
static MwAliasStore aliases;
static unsigned frontend_selected;
static uint32_t alias_delete_id;
static unsigned char *event_catalog_bytes;
static MwEventCatalog event_catalog;
static MwRaceSession race_session;
static uint32_t quick_event_keys[512];
static size_t quick_event_count;
static bool alias_storage_blocked;
static const char *frontend_notice;
static const char *frontend_main_items[]={"CAREER","CHALLENGE SERIES","QUICK RACE","MY CARS","ALIAS MANAGER","OPTIONS"};
#ifdef NFS_STREAMED_WORLD
static StreamedWorld *stream_world;
static MwScenePack scene_pack;
static bool stream_has_frame;
/* A failed stage retains the complete old view. Pause until explicit reset or
   menu navigation; never repeat blocking SD work every frame on a bad asset. */
static bool stream_blocked;
static bool stream_load_announced;
static WorldCollisionRuntime collision_world;
static unsigned char collision_arena[1024*1024];
static uint16_t collision_sections[147];
static size_t collision_section_count;
static int stream_collision_error;
#endif
static RoadWorld road;
static WheelRig wheel_rig;
static RoadMap navigation;
static ChaseCamera chase;
static unsigned world_triangles_drawn,world_draw_calls,measured_fps;
static float simulation_ms;
static MwUiAssets *ui_assets;
static bool piss_filter; /* Neutral by default; an optional artistic grade. */
static unsigned char map_rgb[152*128*3];
/* Rasterize off-screen. The displayed bottom buffer must never be cleared or
   repainted during LCD scanout, even when HUD updates are throttled. */
static unsigned char ui_pixels[MW_UI_BYTES];
static bool ui_pending,ui_to_present,ui_gpu_ready,ui_texture_ready;
static C3D_Tex ui_texture;
static Tex3DS_SubTexture ui_subtexture={.width=320,.height=240,
    .left=0,.top=1,.right=320.f/512,.bottom=1-240.f/256};
static C3D_RenderTarget *ui_target;
static C3D_RenderTarget *target;
static DVLB_s *shader,*world_shader;
static shaderProgram_s program,world_program;
static C3D_AttrInfo world_attributes,car_attributes;
static bool gpu_ready,program_ready,world_program_ready;
static int projection_loc,model_loc,lighting_loc,world_projection_loc,world_model_loc;
static C3D_Mtx world_projection;
static float car_ground_offset;
static char error[160];
static uint8_t *read_file(const char *path,size_t *size)
{
    FILE *f=fopen(path,"rb");if (!f) return NULL;
    if (fseek(f,0,SEEK_END)) { fclose(f);return NULL; }
    long n=ftell(f);
    if (n<1 || n>8*1024*1024 || fseek(f,0,SEEK_SET)) { fclose(f);return NULL; }
    uint8_t *data=malloc((size_t)n);
    if (!data) { fclose(f);return NULL; }
    bool ok=fread(data,1,(size_t)n,f)==(size_t)n && !ferror(f);fclose(f);
    if (!ok) { free(data);return NULL; }
    *size=(size_t)n;return data;
}
static void load_aliases(void)
{
    const char *paths[]={ROOT "aliases.sav",ROOT "aliases.bak"};
    for(unsigned i=0;i<2;i++) {
        FILE *check=fopen(paths[i],"rb");if(!check){if(errno!=ENOENT)alias_storage_blocked=true;continue;}fclose(check);
        size_t n=0;unsigned char *raw=read_file(paths[i],&n);
        bool valid=raw&&mw_alias_decode(&aliases,raw,n);free(raw);
        if(valid){frontend_notice=i?"RECOVERED SAVED ALIASES":NULL;return;}
        alias_storage_blocked=true;
    }
    if(alias_storage_blocked)frontend_notice="ALIAS SAVE COULD NOT BE READ";
}
static bool save_aliases(const MwAliasStore *next)
{
    if(alias_storage_blocked){frontend_notice="ALIAS SAVE COULD NOT BE READ";return false;}
    unsigned char data[MW_ALIAS_SAVE_BYTES];
    if(!mw_alias_encode(next,data,sizeof(data)))return false;
    FILE *existing=fopen(ROOT "aliases.sav","rb");
    if(!existing&&errno!=ENOENT){alias_storage_blocked=true;frontend_notice="ALIAS SAVE COULD NOT BE READ";return false;}
    bool previous=existing!=NULL;if(existing)fclose(existing);
    FILE *f=fopen(ROOT "aliases.pending","wb");if(!f){frontend_notice="COULD NOT SAVE ALIAS";return false;}
    bool ok=fwrite(data,1,sizeof(data),f)==sizeof(data);
    if(fflush(f))ok=false;
    if(fclose(f))ok=false;
    if(!ok){frontend_notice="COULD NOT SAVE ALIAS";return false;}
    if(previous&&rename(ROOT "aliases.sav",ROOT "aliases.bak")){frontend_notice="COULD NOT SAVE ALIAS";return false;}
    if(rename(ROOT "aliases.pending",ROOT "aliases.sav")) {
        if(previous)(void)rename(ROOT "aliases.bak",ROOT "aliases.sav");
        frontend_notice="COULD NOT SAVE ALIAS";return false;
    }
    aliases=*next;frontend_notice=NULL;return true;
}
static void edit_alias(bool rename_existing)
{
    if(alias_storage_blocked){frontend_notice="ALIAS SAVE COULD NOT BE READ";return;}
    if(!rename_existing&&aliases.count==MW_ALIAS_CAPACITY){frontend_notice="ALIAS LIST IS FULL";return;}
    SwkbdState keyboard;char name[MW_ALIAS_NAME_BYTES]={0};
    swkbdInit(&keyboard,SWKBD_TYPE_NORMAL,2,MW_ALIAS_NAME_BYTES-1);
    swkbdSetHintText(&keyboard,rename_existing?"Rename alias":"Create alias");
    swkbdSetValidation(&keyboard,SWKBD_NOTEMPTY_NOTBLANK,0,0);
    if(rename_existing&&frontend_selected>0&&frontend_selected<=aliases.count)
        swkbdSetInitialText(&keyboard,aliases.aliases[frontend_selected-1].name);
    C3D_FrameSync();
    if(swkbdInputText(&keyboard,name,sizeof(name))!=SWKBD_BUTTON_RIGHT)return;
    MwAliasStore next=aliases;
    bool valid=rename_existing?mw_alias_rename(&next,aliases.aliases[frontend_selected-1].id,name):mw_alias_create(&next,name);
    if(!valid){frontend_notice="INVALID OR DUPLICATE ALIAS";return;}
    if(save_aliases(&next)){frontend_page=FE_MAIN;frontend_selected=0;}
}
static unsigned frontend_rows(void)
{
    if(frontend_page==FE_TITLE)return 0;
    if(frontend_page==FE_ALIASES)return aliases.count+1;
    if(frontend_page==FE_MAIN)return 6;
    if(frontend_page==FE_DELETE)return 2;
    if(frontend_page==FE_QUICK)return quick_event_count?(unsigned)quick_event_count:1;
    return frontend_page==FE_OPTIONS?3:1;
}
static void frontend_model(MwUiModel *ui)
{
    ui->mode=frontend_page==FE_TITLE?MW_UI_TITLE:MW_UI_FRONTEND;
    ui->alias_name=mw_alias_selected_name(&aliases);
    if(frontend_page==FE_DELETE)for(unsigned i=0;i<aliases.count;i++)if(aliases.aliases[i].id==alias_delete_id)ui->alias_name=aliases.aliases[i].name;
    ui->frontend_title=(const char*[]){"MOST WANTED","ALIAS MANAGER","MAIN MENU","CAREER","QUICK RACE","CHALLENGE SERIES","OPTIONS","DELETE ALIAS?","RACE SETUP"}[frontend_page];
    unsigned rows=frontend_rows(),base=frontend_selected>=6?frontend_selected-5:0;
    ui->selected=frontend_selected-base;ui->frontend_count=rows-base>6?6:rows-base;
    for(unsigned i=0;i<ui->frontend_count;i++){
        unsigned row=base+i;
        ui->frontend_rows[i]=frontend_page==FE_ALIASES?(row?aliases.aliases[row-1].name:"CREATE ALIAS"):
            frontend_page==FE_MAIN?frontend_main_items[row]:
            frontend_page==FE_OPTIONS?(const char*[]){"CONTROLS","BACK","EXIT"}[row]:
            frontend_page==FE_DELETE?(row?"CANCEL":"DELETE"):
            frontend_page==FE_RACE_SETUP?"BACK":"NOT AVAILABLE IN THIS VERSION";
        if(frontend_page==FE_QUICK&&quick_event_count){MwEventDefinition event;if(mw_event_catalog_find(&event_catalog,quick_event_keys[row],&event))ui->frontend_rows[i]=event.display_title;}
    }
    if(frontend_page==FE_RACE_SETUP){ui->frontend_title_body=true;MwEventDefinition event;if(mw_event_catalog_find(&event_catalog,race_session.event_key,&event))ui->frontend_title=event.display_title;}
    ui->frontend_hint=frontend_page==FE_RACE_SETUP?"RACE NOT AVAILABLE IN THIS VERSION":frontend_notice?frontend_notice:frontend_page==FE_ALIASES?"A: LOAD  X: RENAME  Y: DELETE":
        frontend_page==FE_MAIN?"A: SELECT  Y: FREE ROAM":"A: SELECT  B: BACK";
}
static bool load_mesh(Mesh *mesh,const char *name,const char *texture_dir)
{
    char path[192];snprintf(path,sizeof(path),ROOT "%s",name);
    size_t size;uint8_t *raw=read_file(path,&size);
    snprintf(error,sizeof(error),"Cannot read/validate %s",name);
    if (!raw) return false;
    bool ok=nfs_scene_decode(raw,size,&mesh->scene);
    if (ok) mesh->asset_crc=(uint32_t)raw[24]|(uint32_t)raw[25]<<8|(uint32_t)raw[26]<<16|(uint32_t)raw[27]<<24;
    free(raw);
    if (!ok) return false;
    mesh->bounds=calloc(mesh->scene.batch_count,sizeof(*mesh->bounds));
    if (!mesh->bounds) return false;
    for (unsigned i=0;i<mesh->scene.batch_count;++i) {
        NfsBatch *batch=&mesh->scene.batches[i];float low[3]={INFINITY,INFINITY,INFINITY},high[3]={-INFINITY,-INFINITY,-INFINITY};
        for (unsigned v=batch->first;v<batch->first+batch->count;++v) for (unsigned a=0;a<3;++a) {
            float p=mesh->scene.vertices[v].position[a];low[a]=fminf(low[a],p);high[a]=fmaxf(high[a],p);
        }
        for (unsigned a=0;a<3;++a) {
            mesh->bounds[i].center[a]=(low[a]+high[a])*.5f;
            mesh->bounds[i].extent[a]=(high[a]-low[a])*.5f;
        }
    }
    bool is_world=mesh==&world;
    size_t stride=is_world?sizeof(WorldVertex):sizeof(NfsVertex);
    size_t gpu_bytes=mesh->scene.vertex_count*stride;
    #ifndef NFS_DISABLE_WORLD_INDEX
    if (is_world) {
        WorldIndexedVertices indexed={0};
        if (world_index_encode(mesh->scene.vertices,mesh->scene.vertex_count,&indexed)==WORLD_INDEX_OK) {
            size_t vertex_bytes=indexed.vertex_count*stride,index_offset=(vertex_bytes+127)&~(size_t)127;
            size_t index_bytes=indexed.index_count*sizeof(*indexed.indices),used=index_offset+index_bytes;
            size_t total=(used+127)&~(size_t)127;
            mesh->gpu_vertices=linearAlloc(total);
            if (mesh->gpu_vertices) {
                memcpy(mesh->gpu_vertices,indexed.vertices,vertex_bytes);
                memset((uint8_t *)mesh->gpu_vertices+vertex_bytes,0,index_offset-vertex_bytes);
                mesh->indices=(uint16_t *)((uint8_t *)mesh->gpu_vertices+index_offset);
                memcpy(mesh->indices,indexed.indices,index_bytes);
                memset((uint8_t *)mesh->gpu_vertices+used,0,total-used);gpu_bytes=total;
            }
        }
        world_index_free(&indexed);
    }
    #endif
    if (!mesh->gpu_vertices) {
        mesh->gpu_vertices=linearAlloc(gpu_bytes);if (!mesh->gpu_vertices) return false;
        if (is_world) world_vertex_pack(mesh->gpu_vertices,mesh->scene.vertices,mesh->scene.vertex_count);
    }
    if (!is_world) {
        mesh->vertices=mesh->gpu_vertices;
        memcpy(mesh->vertices,mesh->scene.vertices,mesh->scene.vertex_count*stride);
        for (uint32_t i=0;i<mesh->scene.vertex_count;++i) mesh->vertices[i].uv[1]=1-mesh->vertices[i].uv[1];
    }
    free(mesh->scene.vertices);mesh->scene.vertices=NULL;
    GSPGPU_FlushDataCache(mesh->gpu_vertices,gpu_bytes);
    BufInfo_Init(&mesh->buffer);
    if (BufInfo_Add(&mesh->buffer,mesh->gpu_vertices,(int)stride,is_world?3:4,is_world?0x210:0x3210)<0) return false;
    for (unsigned i=0;i<mesh->scene.texture_count;++i) {
        NfsTexture *t=&mesh->scene.textures[i];
        snprintf(path,sizeof(path),ROOT "%s/%08lx.t3x",texture_dir,(unsigned long)t->key);
        snprintf(error,sizeof(error),"Cannot load %s/%08lx",texture_dir,(unsigned long)t->key);
        FILE *f=fopen(path,"rb");if (!f) return false;
        Tex3DS_Texture imported=Tex3DS_TextureImportStdio(f,&mesh->textures[i],NULL,false);fclose(f);
        if (!imported) return false;
        Tex3DS_TextureFree(imported);mesh->loaded++;
        if (mesh->textures[i].width!=t->width || mesh->textures[i].height!=t->height) return false;
        C3D_TexSetFilter(&mesh->textures[i],GPU_LINEAR,GPU_NEAREST);
        C3D_TexSetWrap(&mesh->textures[i],GPU_REPEAT,GPU_REPEAT);
    }
    return true;
}
static void free_mesh(Mesh *mesh)
{
    for (unsigned i=0;i<mesh->loaded;++i) C3D_TexDelete(&mesh->textures[i]);
    if (mesh->gpu_vertices) linearFree(mesh->gpu_vertices);
    free(mesh->bounds);
    nfs_scene_free(&mesh->scene);
}
static bool initialize(void)
{
    snprintf(error,sizeof(error),"GPU initialization failed");
    #ifdef NFS_STREAMED_WORLD
    if (!C3D_Init(C3D_DEFAULT_CMDBUF_SIZE*4)) return false;
#else
    if (!C3D_Init(C3D_DEFAULT_CMDBUF_SIZE)) return false;
#endif
    gpu_ready=true;
    target=C3D_RenderTargetCreate(240,400,GPU_RB_RGBA8,GPU_RB_DEPTH24_STENCIL8);
    if (!target) return false;
    C3D_RenderTargetSetOutput(target,GFX_TOP,GFX_LEFT,TRANSFER_FLAGS);
    shader=DVLB_ParseFile((u32*)rockport_vshader_shbin,rockport_vshader_shbin_size);
    if (!shader || !shader->numDVLE || R_FAILED(shaderProgramInit(&program))) return false;
    program_ready=true;
    if (R_FAILED(shaderProgramSetVsh(&program,&shader->DVLE[0]))) return false;
    C3D_BindProgram(&program);
    projection_loc=shaderInstanceGetUniformLocation(program.vertexShader,"projection");
    model_loc=shaderInstanceGetUniformLocation(program.vertexShader,"modelView");
    lighting_loc=shaderInstanceGetUniformLocation(program.vertexShader,"lighting");
    if (projection_loc<0 || model_loc<0 || lighting_loc<0) return false;
    world_shader=DVLB_ParseFile((u32*)world_vshader_shbin,world_vshader_shbin_size);
    if (!world_shader || !world_shader->numDVLE || R_FAILED(shaderProgramInit(&world_program))) return false;
    world_program_ready=true;
    if (R_FAILED(shaderProgramSetVsh(&world_program,&world_shader->DVLE[0]))) return false;
    world_projection_loc=shaderInstanceGetUniformLocation(world_program.vertexShader,"projection");
    world_model_loc=shaderInstanceGetUniformLocation(world_program.vertexShader,"modelView");
    if (world_projection_loc<0 || world_model_loc<0) return false;
    AttrInfo_Init(&car_attributes);
    AttrInfo_AddLoader(&car_attributes,0,GPU_FLOAT,3);AttrInfo_AddLoader(&car_attributes,1,GPU_FLOAT,3);AttrInfo_AddLoader(&car_attributes,2,GPU_FLOAT,2);AttrInfo_AddLoader(&car_attributes,3,GPU_FLOAT,4);
    AttrInfo_Init(&world_attributes);
    AttrInfo_AddLoader(&world_attributes,0,GPU_FLOAT,3);AttrInfo_AddLoader(&world_attributes,1,GPU_FLOAT,2);AttrInfo_AddLoader(&world_attributes,2,GPU_FLOAT,4);
    #ifdef NFS_STREAMED_WORLD
    if (!load_mesh(&body,"body.nfm","car-textures")) return false;
#else
    if (!load_mesh(&world,"world.nfm","world-textures") || !load_mesh(&body,"body.nfm","car-textures")) return false;
#endif
    snprintf(error,sizeof(error),"Cannot read/validate road.nrd");
    size_t size;uint8_t *raw=read_file(ROOT "road.nrd",&size);
    if (!raw) return false;
    bool ok=road_decode(raw,size,&road);free(raw);if (!ok) return false;
    snprintf(error,sizeof(error),"Cannot read/validate wheels.nwa");
    raw=read_file(ROOT "wheels.nwa",&size);if (!raw) return false;
    ok=wheel_rig_decode(raw,size,body.scene.batch_count,body.asset_crc,&wheel_rig);free(raw);
    if (!ok) return false;
    snprintf(error,sizeof(error),"Cannot initialize road map");
    if (!road_map_init(&road,&navigation)) return false;
    /* Optional during development; present but unreadable/corrupt is an error. */
    struct stat art_info;
    if (!stat(ROOT "ui.nui",&art_info)) {
        raw=read_file(ROOT "ui.nui",&size);
        if (raw) { ui_assets=mw_ui_assets_decode(raw,size);free(raw); }
        if (!ui_assets) { snprintf(error,sizeof(error),"Invalid/unreadable ui.nui artwork pack");return false; }
    } else if (errno!=ENOENT) {
        snprintf(error,sizeof(error),"Cannot inspect ui.nui artwork pack");return false;
    }
    struct stat event_info;
    if(!stat(ROOT "events.nre",&event_info)){
        event_catalog_bytes=read_file(ROOT "events.nre",&size);
        if(!event_catalog_bytes||!mw_event_catalog_open(&event_catalog,event_catalog_bytes,size)||
           !mw_race_session_courses(&event_catalog,true,quick_event_keys,512,&quick_event_count)){
            snprintf(error,sizeof(error),"Invalid/unreadable events.nre");return false;
        }
    }else if(errno!=ENOENT){snprintf(error,sizeof(error),"Cannot inspect events.nre");return false;}
    for (uint32_t i=0;i<body.scene.vertex_count;++i)
        car_ground_offset=fmaxf(car_ground_offset,-body.vertices[i].position[1]*road.car_half_extent);
#ifdef NFS_STREAMED_WORLD
    snprintf(error,sizeof(error),"Cannot read/validate world.mwp archive");
    if (mw_scene_pack_open(&scene_pack,ROOT "world.mwp",2*1024*1024)!=MW_SCENE_PACK_OK) return false;
    StreamedWorldConfig stream_config={.read_asset=streamed_world_pack_read,.read_context=&scene_pack,
        .metadata_path=ROOT "world-streaming.bin",.normal_bytes=12*1024*1024,
        .linear_bytes=20*1024*1024,.scratch_bytes=4*1024*1024,.cache_entries=2048,
        .object_capacity=4096,.run_capacity=32768,.render_scale=road.scale,
        .lod_mode=STREAMED_WORLD_SOURCE_LOD_COMPONENTS,.alpha_reference=40,
        .comparison_zero_transparent_rgb=false,
        .boot_global_provider_bank=true,.original_missing_texture_hash=0x66994f4a};
    StreamedWorldResult stream_result=streamed_world_create(&stream_config,&stream_world);
    if (stream_result!=STREAMED_WORLD_OK) {
        snprintf(error,sizeof(error),"Cannot initialize streamed map (%d)",(int)stream_result);return false;
    }
    snprintf(error,sizeof(error),"Cannot read/validate original world.nwc collision");
    if (world_collision_runtime_open(&collision_world,ROOT "world.nwc",collision_arena,sizeof(collision_arena))) return false;
    raw=read_file(ROOT "world-streaming.bin",&size);
    bool same_source=raw && size>=96 && !memcmp(raw+64,collision_world.source_sha256,32) &&
        !memcmp(raw+64,scene_pack.source_sha256,32);
    free(raw);
    if (!same_source) { snprintf(error,sizeof(error),"Map/collision source identity mismatch");return false; }
#endif
    snprintf(error,sizeof(error),"Cannot initialize bottom-screen presentation");
    if (!C2D_Init(16)) return false;
    ui_gpu_ready=true;ui_target=C2D_CreateScreenTarget(GFX_BOTTOM,GFX_LEFT);
    if (!ui_target || !C3D_TexInit(&ui_texture,MW_UI_TEXTURE_WIDTH,MW_UI_TEXTURE_HEIGHT,GPU_RGBA8)) return false;
    ui_texture_ready=true;
    C3D_TexSetFilter(&ui_texture,GPU_NEAREST,GPU_NEAREST);
    C3D_TexSetWrap(&ui_texture,GPU_CLAMP_TO_EDGE,GPU_CLAMP_TO_EDGE);
    C3D_CullFace(GPU_CULL_NONE);
    C3D_AlphaTest(true,GPU_GREATER,0);
    C3D_AlphaBlend(GPU_BLEND_ADD,GPU_BLEND_ADD,GPU_SRC_ALPHA,GPU_ONE_MINUS_SRC_ALPHA,GPU_ONE,GPU_ONE_MINUS_SRC_ALPHA);
    C3D_TexEnv *env=C3D_GetTexEnv(0);C3D_TexEnvInit(env);
    C3D_TexEnvSrc(env,C3D_Both,GPU_TEXTURE0,GPU_PRIMARY_COLOR,0);C3D_TexEnvFunc(env,C3D_Both,GPU_MODULATE);
    error[0]=0;return true;
}
#ifndef NFS_STREAMED_WORLD
static void draw_world_run(Mesh *mesh,unsigned first,unsigned count,unsigned texture,int *last_additive,unsigned *last_texture)
{
    int additive=!!(mesh->scene.textures[texture].flags&4);
    if (additive!=*last_additive) {
        C3D_AlphaBlend(GPU_BLEND_ADD,GPU_BLEND_ADD,GPU_SRC_ALPHA,additive?GPU_ONE:GPU_ONE_MINUS_SRC_ALPHA,GPU_ONE,GPU_ONE_MINUS_SRC_ALPHA);
        *last_additive=additive;
    }
    if (texture!=*last_texture) { C3D_TexBind(0,&mesh->textures[texture]);*last_texture=texture; }
    if (mesh->indices) C3D_DrawElements(GPU_TRIANGLES,(int)count,C3D_UNSIGNED_SHORT,mesh->indices+first);
    else C3D_DrawArrays(GPU_TRIANGLES,first,count);
    world_triangles_drawn+=count/3;++world_draw_calls;
}
static void draw_mesh(Mesh *mesh,const C3D_Mtx *model,const WorldFrustum *frustum)
{
    C3D_BindProgram(&world_program);C3D_SetAttrInfo(&world_attributes);
    int last_additive=-1;
    unsigned last_texture=NFS_MAX_TEXTURES;world_triangles_drawn=0;world_draw_calls=0;
    C3D_SetBufInfo(&mesh->buffer);
    C3D_FVUnifMtx4x4(GPU_VERTEX_SHADER,world_projection_loc,&world_projection);
    C3D_FVUnifMtx4x4(GPU_VERTEX_SHADER,world_model_loc,model);
    for (unsigned pass=0;pass<2;++pass) {
        C3D_DepthTest(true,GPU_GREATER,pass?GPU_WRITE_COLOR:GPU_WRITE_ALL);
        unsigned first=0,count=0,texture=0;
        for (uint32_t i=0;i<mesh->scene.batch_count;++i) {
            NfsBatch *b=&mesh->scene.batches[i];
            bool transparent=mesh->scene.textures[b->texture].flags&1;
            if (transparent!=(bool)pass) continue;
            if (frustum && !world_visible(frustum,&mesh->bounds[i])) continue;
            if (count && (texture!=b->texture || first+count!=b->first)) {
                draw_world_run(mesh,first,count,texture,&last_additive,&last_texture);count=0;
            }
            if (!count) { first=b->first;texture=b->texture; }
            count+=b->count;
        }
        if (count) draw_world_run(mesh,first,count,texture,&last_additive,&last_texture);
    }
}
#endif
static void draw_car(const C3D_Mtx *parent,const WheelMotion *motion,float steering)
{
    C3D_BindProgram(&program);C3D_SetAttrInfo(&car_attributes);
    C3D_AlphaTest(true,GPU_GREATER,0);
    C3D_AlphaBlend(GPU_BLEND_ADD,GPU_BLEND_ADD,GPU_SRC_ALPHA,GPU_ONE_MINUS_SRC_ALPHA,GPU_ONE,GPU_ONE_MINUS_SRC_ALPHA);
    C3D_Mtx models[5];models[0]=*parent;
    for (unsigned i=0;i<4;++i) {
        const Wheel *wheel=&wheel_rig.wheels[i];const float *p=wheel->pivot;
        C3D_Mtx local;Mtx_Identity(&local);
        Mtx_Translate(&local,p[0],p[1],p[2],true);
        if (wheel->front) Mtx_RotateY(&local,steering,true);
        Mtx_RotateZ(&local,motion->angle[i],true);
        Mtx_Translate(&local,-p[0],-p[1],-p[2],true);
        Mtx_Multiply(&models[i+1],parent,&local);
    }
    C3D_SetBufInfo(&body.buffer);
    for (unsigned pass=0;pass<2;++pass) {
        C3D_DepthTest(true,GPU_GREATER,pass?GPU_WRITE_COLOR:GPU_WRITE_ALL);
        unsigned current=5;
        for (uint32_t i=0;i<body.scene.batch_count;++i) {
            NfsBatch *b=&body.scene.batches[i];
            if ((bool)(body.scene.textures[b->texture].flags&1)!=(bool)pass) continue;
            unsigned group=wheel_rig.groups[i];
            if (group!=current) { C3D_FVUnifMtx4x4(GPU_VERTEX_SHADER,model_loc,&models[group]);current=group; }
            C3D_TexBind(0,&body.textures[b->texture]);C3D_DrawArrays(GPU_TRIANGLES,b->first,b->count);
        }
    }
}
static void render(Screen screen,const DriveState *car,float height,float rotation,
                   const WheelMotion *motion,float garage_steering,const RoadPose *pose)
{
    C3D_RenderTargetClear(target,C3D_CLEAR_ALL,mw_color_grade_clear(screen==DRIVE?0x718699ff:0x141414ff,piss_filter),0);
    C3D_FrameDrawOn(target);mw_color_grade_apply(piss_filter);C3D_Mtx projection,model;
    C3D_BindProgram(&program);
    C3D_FVUnifSet(GPU_VERTEX_SHADER,lighting_loc,.5f,.5f,0,0);
    if (screen==DRIVE) {
        (void)height;float scale=road.scale;
        float camera_eye[3],camera_at[3];
        for (unsigned a=0;a<3;++a) { camera_eye[a]=chase.eye[a]*scale;camera_at[a]=chase.target[a]*scale; }
        C3D_FVec eye=FVec3_New(camera_eye[0],camera_eye[1],camera_eye[2]);
        C3D_FVec at=FVec3_New(camera_at[0],camera_at[1],camera_at[2]);
        C3D_FVec up=FVec3_New(0,1,0);
        C3D_Mtx view;Mtx_LookAt(&view,eye,at,up,false);
        float fov=C3D_AngleFromDegrees(chase.fov);
        Mtx_PerspTilt(&projection,fov,C3D_AspectRatioTop,.15f*scale,DRIVE_FAR_WORLD*scale,false);
        world_projection=projection;
        /* World RGB already carries baked lighting. Keep inspection lighting
           for the car, whose legacy scene has white vertex colours. */
        C3D_FVUnifSet(GPU_VERTEX_SHADER,lighting_loc,1,0,0,0);
#ifdef NFS_STREAMED_WORLD
        streamed_world_draw(stream_world,&world_program,world_projection_loc,world_model_loc,&projection);
        StreamedWorldStats stats={0};streamed_world_stats(stream_world,&stats);
        world_triangles_drawn=stats.triangles;world_draw_calls=stats.draw_runs;
#else
        WorldFrustum frustum;bool valid_view=world_frustum(&frustum,camera_eye,camera_at,fov,C3D_AspectRatioTop,.15f*scale,DRIVE_FAR_WORLD*scale);
#ifdef NFS_DISABLE_WORLD_CULLING
        valid_view=false; /* Offline pixel-reference build only. */
#endif
        draw_mesh(&world,&view,valid_view?&frustum:NULL);
#endif
        C3D_BindProgram(&program);
        C3D_FVUnifMtx4x4(GPU_VERTEX_SHADER,projection_loc,&projection);
        C3D_FVUnifSet(GPU_VERTEX_SHADER,lighting_loc,.5f,.5f,0,0);
        Mtx_Identity(&model);
        Mtx_Translate(&model,(car->x+pose->normal[0]*car_ground_offset)*scale,
                      (pose->height+pose->normal[1]*car_ground_offset)*scale,
                      (car->z+pose->normal[2]*car_ground_offset)*scale,true);
        Mtx_RotateY(&model,car->heading-1.5707963f,true);
        Mtx_RotateZ(&model,pose->pitch,true);Mtx_RotateX(&model,pose->roll,true);
        Mtx_Scale(&model,road.car_half_extent*scale,road.car_half_extent*scale,road.car_half_extent*scale);
        C3D_Mtx combined;Mtx_Multiply(&combined,&view,&model);draw_car(&combined,motion,car->steering);
    } else {
        Mtx_PerspTilt(&projection,C3D_AngleFromDegrees(40),C3D_AspectRatioTop,.1f,20,false);
        C3D_FVUnifMtx4x4(GPU_VERTEX_SHADER,projection_loc,&projection);
        Mtx_Identity(&model);Mtx_Translate(&model,0,0,-3.4f,true);Mtx_RotateX(&model,.25f,true);Mtx_RotateY(&model,rotation,true);
        draw_car(&model,motion,garage_steering);
    }
}
#ifdef NFS_STREAMED_WORLD
static StreamedWorldResult prepare_streamed_world(const DriveState *car)
{
    StreamedWorldView view={.up_viewer={0,1,0},
        .vertical_fov_radians=C3D_AngleFromDegrees(chase.fov),.aspect=C3D_AspectRatioTop,
        .near_world=.15f,.far_world=DRIVE_FAR_WORLD,
        .original_fov_turn=(uint16_t)lroundf(chase.fov*(65536.0f/360.0f))};
    float length=0;
    for (unsigned a=0;a<3;++a) {
        view.camera_viewer[a]=(double)chase.eye[a]+road.origin[a];
        view.forward_viewer[a]=chase.target[a]-chase.eye[a];
        length+=view.forward_viewer[a]*view.forward_viewer[a];
    }
    length=sqrtf(length);if (!(length>0)) return STREAMED_WORLD_INVALID;
    for (unsigned a=0;a<3;++a) view.forward_viewer[a]/=length;
    /* Ordinary main driving view uses source normal-context LOD components.
       Special race/replay view-state producers remain outside this prototype. */
    stream_collision_error=0;
#ifdef NFS_STREAMED_WORLD_PROBE
    (void)car;StreamedWorldResult result=streamed_world_prepare(stream_world,360,2410,&view);
#else
    StreamedWorldResult result=streamed_world_prepare(stream_world,car->x+road.origin[0],
                                  -(car->z+road.origin[2]),&view);
#endif
    if (result!=STREAMED_WORLD_OK) return result;
    uint16_t sections[147];size_t count=0;
    result=streamed_world_sections(stream_world,sections,147,&count);
    if (result!=STREAMED_WORLD_OK) { stream_has_frame=false;return result; }
    if (collision_world.ready && count==collision_section_count &&
        !memcmp(sections,collision_sections,count*sizeof(*sections))) return STREAMED_WORLD_OK;
    WorldCollisionAdmission admission;
    stream_collision_error=world_collision_runtime_activate(&collision_world,sections,count,&admission);
    if (stream_collision_error) {
        /* Renderer has staged its new view, but collision is not ready. Do not
           present either consumer as playable; reset/menu remains available. */
        stream_has_frame=false;return STREAMED_WORLD_IO;
    }
    memcpy(collision_sections,sections,count*sizeof(*sections));collision_section_count=count;
    return STREAMED_WORLD_OK;
}
#endif
static MwUiModel ui_model(Screen screen,unsigned selected,const DriveState *car,
                          float height,bool edge,MwUiPanel panel,u32 held)
{
    MwUiModel ui={.mode=screen==MENU?MW_UI_MENU:screen==DRIVE?MW_UI_DRIVE:
        screen==GARAGE?MW_UI_GARAGE:screen==DISPLAY?MW_UI_DISPLAY:MW_UI_CONTROLS,.panel=panel,.selected=selected,
        .speed_mps=car->speed,.handbrake=screen==DRIVE && (held&KEY_R),
        .road_status=edge?MW_UI_EDGE_REACHED:MW_UI_ROAD_LOADED,
        .assets=ui_assets,.piss_filter=piss_filter,.fps=measured_fps,.triangles=world_triangles_drawn,.draw_calls=world_draw_calls,
        .gpu_ms=C3D_GetDrawingTime(),.draw_ms=C3D_GetProcessingTime(),.logic_ms=simulation_ms,
        .slip_degrees=atan2f(car->lateral_speed,fmaxf(fabsf(car->speed),.01f))*57.29578f};
#ifdef NFS_STREAMED_WORLD
    (void)height;
    ui.streamed_map=true;
    if (screen==DRIVE && stream_blocked) ui.road_status=MW_UI_MAP_PAUSED;
    else if (screen==DRIVE && !stream_has_frame) ui.road_status=MW_UI_MAP_LOADING;
#else
    if (screen==DRIVE && !edge && road_edge_ahead(&road,car,height))
        ui.road_status=car->speed<0?MW_UI_EDGE_BEHIND:MW_UI_EDGE_AHEAD;
#endif
    if(screen==MENU)frontend_model(&ui);
    return ui;
}
static void draw_ui(const MwUiModel *ui,const DriveState *car)
{
    const unsigned char *map=NULL;
    if (ui->mode==MW_UI_DRIVE && ui->panel==MW_UI_NAVIGATION &&
        road_map_render(&navigation,&road,car,map_rgb,152,128)) map=map_rgb;
    if (mw_ui_render(ui_pixels,sizeof(ui_pixels),ui,map)) ui_pending=true;
}
static void upload_ui(void)
{
    if (!ui_pending) return;
    /* Called outside a frame: never modify the texture while a previous UI
       draw reads it. Both LCD swaps now belong to the GPU completion queue. */
    C3D_FrameSync();
    if (!mw_ui_texture_pack(ui_texture.data,ui_texture.size,ui_pixels,sizeof(ui_pixels))) return;
    C3D_TexFlush(&ui_texture);ui_pending=false;ui_to_present=true;
}
static void present_ui(void)
{
    if (!ui_to_present) return;
    /* C2D screen targets include a depth buffer. Never let uninitialized or
       previously written depth mask portions of the complete HUD image. */
    C3D_RenderTargetClear(ui_target,C3D_CLEAR_ALL,0x000000ff,0);
    C2D_Prepare();C2D_SceneBegin(ui_target);
    /* This is one opaque full-screen image, with no depth layering or alpha
       rejection. Do not inherit either test from the car/world passes. */
    C3D_DepthTest(false,GPU_ALWAYS,GPU_WRITE_COLOR);
    C3D_AlphaTest(false,GPU_ALWAYS,0);
    C2D_Image image={.tex=&ui_texture,.subtex=&ui_subtexture};
    C2D_DrawImageAt(image,0,0,0,NULL,1,1);C2D_Flush();ui_to_present=false;
}
int main(void)
{
    gfxInitDefault();gfxSet3D(false);consoleInit(GFX_BOTTOM,NULL);gfxSetDoubleBuffering(GFX_BOTTOM,false);
    bool ok=initialize();load_aliases();Screen screen=MENU;unsigned selected=0;
    DriveState car;drive_reset(&car,road.spawn[0],road.spawn[2],road.heading);float height=road.spawn[1];bool edge=false;
    RoadPose pose={.height=height,.normal={0,1,0}};
    MwUiPanel panel=MW_UI_NAVIGATION;
    if (ok) {
        gfxSetScreenFormat(GFX_BOTTOM,GSP_BGR8_OES);
        gfxSetDoubleBuffering(GFX_BOTTOM,true);
        MwUiModel ui=ui_model(screen,selected,&car,height,edge,panel,0);draw_ui(&ui,&car);
    }
    else printf("NFS MW Rockport v%s\n\n%s\n\nExtract the complete ZIP\nto the SD card root.\n\nSTART: exit\n",BUILD_VERSION,error);
    WheelMotion motion={0},garage_motion={0},stationary={0};float garage_steering=0;bool orbit=true;
    u64 previous=osGetTime(),last_status=previous,fps_start=previous;unsigned fps_frames=0;float rotation=.65f;
    while (aptMainLoop()) {
        u64 cpu_begin=svcGetSystemTick();
        hidScanInput();u32 down=hidKeysDown(),held=hidKeysHeld();Screen before=screen;bool ui_changed=false;
        if (!ok) { if (down&KEY_START) break;gfxFlushBuffers();gfxSwapBuffers();gspWaitForVBlank();continue; }
        if (screen==MENU) {
            bool accept=!!(down&KEY_A);
            if((down&KEY_TOUCH)&&!(down&(KEY_A|KEY_B|KEY_START|KEY_SELECT|KEY_UP|KEY_DOWN|KEY_CPAD_UP|KEY_CPAD_DOWN|KEY_X|KEY_Y))){
                touchPosition touch;hidTouchRead(&touch);
                if(frontend_page==FE_TITLE)accept=true;
                else if(touch.px>=12&&touch.px<308&&touch.py>=73&&touch.py<205){
                    unsigned base=frontend_selected>=6?frontend_selected-5:0;
                    unsigned row=base+(touch.py-73)/22;
                    if(row<frontend_rows()){frontend_selected=row;accept=true;}
                }
            }
            unsigned rows=frontend_rows();
            if(rows&&(down&(KEY_UP|KEY_CPAD_UP)))frontend_selected=(frontend_selected+rows-1)%rows;
            if(rows&&(down&(KEY_DOWN|KEY_CPAD_DOWN)))frontend_selected=(frontend_selected+1)%rows;
            if(frontend_page==FE_TITLE&&(accept||(down&KEY_START))){frontend_page=aliases.count?FE_MAIN:FE_ALIASES;frontend_selected=0;}
            else if(frontend_page==FE_MAIN&&(down&KEY_Y))screen=DRIVE;
            else if(frontend_page==FE_ALIASES&&(down&KEY_X)&&frontend_selected)edit_alias(true);
            else if(frontend_page==FE_ALIASES&&(down&KEY_Y)&&frontend_selected){alias_delete_id=aliases.aliases[frontend_selected-1].id;frontend_page=FE_DELETE;frontend_selected=1;}
            else if(down&KEY_B){if(frontend_page==FE_RACE_SETUP)(void)mw_race_session_cancel(&race_session);frontend_page=aliases.count?FE_MAIN:FE_TITLE;frontend_selected=0;frontend_notice=NULL;}
            else if(accept){
                if(frontend_page==FE_ALIASES){
                    if(!frontend_selected)edit_alias(false);
                    else {MwAliasStore next=aliases;if(mw_alias_select(&next,next.aliases[frontend_selected-1].id)&&save_aliases(&next)){frontend_page=FE_MAIN;frontend_selected=0;}}
                }else if(frontend_page==FE_MAIN){
                    if(frontend_selected==3)screen=GARAGE;
                    else {frontend_page=(FrontendPage[]){FE_CAREER,FE_CHALLENGE,FE_QUICK,FE_MAIN,FE_ALIASES,FE_OPTIONS}[frontend_selected];frontend_selected=0;}
                }else if(frontend_page==FE_QUICK&&quick_event_count){
                    if(mw_race_session_prepare(&race_session,&event_catalog,quick_event_keys[frontend_selected],&aliases,(uintptr_t)&car)){
                        frontend_page=FE_RACE_SETUP;frontend_selected=0;frontend_notice=NULL;
                    }else frontend_notice="SELECT AN ALIAS FIRST";
                }else if(frontend_page==FE_RACE_SETUP){
                    (void)mw_race_session_cancel(&race_session);frontend_page=FE_QUICK;frontend_selected=0;
                }else if(frontend_page==FE_DELETE){
                    if(!frontend_selected){MwAliasStore next=aliases;if(mw_alias_remove(&next,alias_delete_id))save_aliases(&next);}
                    frontend_page=FE_ALIASES;frontend_selected=0;
                }else if(frontend_page==FE_OPTIONS){
                    if(!frontend_selected)screen=CONTROLS;
                    else if(frontend_selected==2)screen=QUIT;
                    else {frontend_page=FE_MAIN;frontend_selected=0;}
                }else {frontend_page=FE_MAIN;frontend_selected=0;}
            }
        } else if (screen==DRIVE) {
            if (down&(KEY_START|KEY_SELECT)) screen=MENU;
        } else if (down&(KEY_B|KEY_START) || (screen==CONTROLS && (down&KEY_A))) screen=MENU;
        if (screen==DISPLAY && before==DISPLAY && (down&KEY_A)) {
            piss_filter=!piss_filter;ui_changed=true;
        }
        /* A controller-driven screen transition takes precedence over touch. */
        if (before!=MENU && (down&KEY_TOUCH) && screen==before && !(down&(KEY_A|KEY_B|KEY_START|KEY_SELECT))) {
            touchPosition touch;hidTouchRead(&touch);
            MwUiModel ui=ui_model(screen,selected,&car,height,edge,panel,held);
            MwUiAction action=mw_ui_touch(&ui,touch.px,touch.py);
            switch (action) {
            case MW_UI_OPEN_MENU:screen=MENU;break;
            case MW_UI_SELECT_DRIVE:selected=0;screen=DRIVE;break;
            case MW_UI_SELECT_GARAGE:selected=1;screen=GARAGE;break;
            case MW_UI_SELECT_CONTROLS:selected=2;screen=CONTROLS;break;
            case MW_UI_SELECT_DISPLAY:selected=3;screen=DISPLAY;break;
            case MW_UI_TOGGLE_PISS_FILTER:piss_filter=!piss_filter;break;
            case MW_UI_QUIT:selected=4;screen=QUIT;break;
            case MW_UI_TOGGLE_HELP:panel=panel==MW_UI_HELP?MW_UI_NAVIGATION:MW_UI_HELP;break;
            case MW_UI_TOGGLE_DIAGNOSTICS:panel=panel==MW_UI_DIAGNOSTICS?MW_UI_NAVIGATION:MW_UI_DIAGNOSTICS;break;
            default:break;
            }
            ui_changed=ui_changed || action!=MW_UI_NONE;
        }
        if (screen==QUIT) break;
        if (screen==DRIVE && (before!=DRIVE || (down&KEY_X))) {
#ifdef NFS_STREAMED_WORLD
            stream_has_frame=false;stream_blocked=false;stream_load_announced=false;
#endif
            drive_reset(&car,road.spawn[0],road.spawn[2],road.heading);height=road.spawn[1];edge=false;
            wheel_motion_reset(&motion);
            pose=(RoadPose){.height=height,.normal={0,1,0}};
            (void)road_pose_sample(&road,&wheel_rig,&car,height,&pose);
            (void)chase_reset(&chase,&car,height);
        }
        u64 now=osGetTime();float dt=(now-previous)*.001f;previous=now;if (dt>.1f) dt=.1f;
#ifdef NFS_STREAMED_WORLD
        DriveState saved_car=car;float saved_height=height;
        WheelMotion saved_motion=motion;RoadPose saved_pose=pose;ChaseCamera saved_chase=chase;
#endif
        bool advance_drive=screen==DRIVE && before==DRIVE && dt>0 && !(down&KEY_X);
#ifdef NFS_STREAMED_WORLD
        advance_drive=advance_drive && !stream_blocked && stream_has_frame;
#endif
        if (advance_drive) {
            circlePosition pad;hidCircleRead(&pad);
            float steering=abs(pad.dx)>15?pad.dx/156.0f:0;
            steering+=!!(held&KEY_RIGHT)-!!(held&KEY_LEFT);
            DriveInput input={.throttle=!!(held&KEY_A)-!!(held&KEY_Y),.brake=!!(held&KEY_B),.steering=-steering,.handbrake=held&KEY_R};
            DriveState previous_car=car;float previous_height=height;
#ifdef NFS_STREAMED_WORLD
            StreamedDriveSurface surface={&collision_world,&road};
            int advanced=streamed_drive_step(&surface,&car,&height,input,dt);
            edge=advanced!=1;
            if (advanced<0) { stream_blocked=true;stream_has_frame=false;ui_changed=true; }
#else
            edge=!road_drive_step(&road,&car,&height,input,dt);
#endif
            WheelMotion previous_motion=motion;
            if (!wheel_motion_update(&wheel_rig,&motion,&previous_car,&car)) wheel_motion_reset(&motion);
            else if (input.handbrake) (void)wheel_motion_lock_rear(&wheel_rig,&previous_motion,&motion);
            if (car.x!=previous_car.x || car.z!=previous_car.z || car.heading!=previous_car.heading || height!=previous_height) {
                pose=(RoadPose){.height=height,.normal={0,1,0}};
#ifdef NFS_STREAMED_WORLD
                (void)road_pose_sample_with_surface(&road,&wheel_rig,&car,height,&pose,streamed_drive_surface,&surface);
#else
                (void)road_pose_sample(&road,&wheel_rig,&car,height,&pose);
#endif
            }
        }
        if (advance_drive) (void)chase_step(&chase,&car,height,dt);
        if (screen==GARAGE && before==GARAGE) {
            if (down&KEY_Y) orbit=!orbit;
            circlePosition pad;hidCircleRead(&pad);
            garage_steering=-.55f*((abs(pad.dx)>15?pad.dx/156.0f:0)+!!(held&KEY_RIGHT)-!!(held&KEY_LEFT));
            if (garage_steering>.55f) garage_steering=.55f;
            if (garage_steering<-.55f) garage_steering=-.55f;
            if (held&KEY_A) {
                DriveState a={0},b={.z=dt*.75f};
                if (!wheel_motion_update(&wheel_rig,&garage_motion,&a,&b)) wheel_motion_reset(&garage_motion);
            }
            if (down&KEY_X) { wheel_motion_reset(&garage_motion);garage_steering=0;rotation=.65f; }
        }
        if (screen!=DRIVE && (screen!=GARAGE || orbit)) rotation=fmodf(rotation+dt*.3f,6.2831853f);
#ifdef NFS_STREAMED_WORLD_PROBE
        if (screen==DRIVE) {
            const float eye[3]={360,180,-2410};
            for (unsigned a=0;a<3;++a) { chase.eye[a]=eye[a]-road.origin[a];chase.target[a]=chase.eye[a]; }
            chase.target[2]+=10;chase.fov=57.2957795f;
        }
#endif
#ifdef NFS_STREAMED_WORLD
        if (screen==DRIVE && !stream_blocked) {
            /* Present a complete loading frame before any blocking asset IO. */
            bool announce=!stream_has_frame && !stream_load_announced;
            if (announce) { stream_load_announced=true;ui_changed=true; }
            StreamedWorldResult result=announce?STREAMED_WORLD_OK:prepare_streamed_world(&car);
            if (result==STREAMED_WORLD_OK && !announce) {
                if (!stream_has_frame) ui_changed=true;
                stream_has_frame=true;
            }
            else if (result!=STREAMED_WORLD_OK) {
                StreamedWorldStats stats={0};streamed_world_stats(stream_world,&stats);
                if (stream_collision_error) snprintf(error,sizeof(error),"Collision load (%d)",stream_collision_error);
                else snprintf(error,sizeof(error),"Map load (%d): %.110s",(int)result,stats.detail);
                svcOutputDebugString(error,(s32)strlen(error));
                car=saved_car;height=saved_height;motion=saved_motion;pose=saved_pose;
                chase=saved_chase;stream_blocked=true;ui_changed=true;
            }
        }
#endif
        if (before!=screen || ui_changed || (screen==MENU && down) ||
            (screen==DRIVE && (now-last_status>=200 || (down&KEY_X)))) {
            MwUiModel ui=ui_model(screen,selected,&car,height,edge,panel,held);
            draw_ui(&ui,&car);last_status=now;
        }
        const WheelMotion *display_motion=screen==DRIVE?&motion:screen==GARAGE?&garage_motion:&stationary;
        float logic_ms=(float)(svcGetSystemTick()-cpu_begin)*(1000.0f/SYSCLOCK_ARM11);
        simulation_ms+=(logic_ms-simulation_ms)*.1f;
        Screen render_screen=screen;
#ifdef NFS_STREAMED_WORLD
        /* No completed world exists after a failed initial load/reset. Keep
           menu preview above the actionable bottom-screen load status. */
        if (screen==DRIVE && !stream_has_frame) render_screen=MENU;
#endif
        upload_ui();
        if (C3D_FrameBegin(C3D_FRAME_SYNCDRAW)) {
            render(render_screen,&car,height,rotation,display_motion,screen==GARAGE?garage_steering:0,&pose);
            present_ui();C3D_FrameEnd(0);++fps_frames;
        }
        u64 fps_now=osGetTime();
        if (fps_now-fps_start>=1000) { measured_fps=(unsigned)((fps_frames*1000ULL+(fps_now-fps_start)/2)/(fps_now-fps_start));fps_start=fps_now;fps_frames=0; }
    }
#ifdef NFS_STREAMED_WORLD
    world_collision_runtime_close(&collision_world);
    streamed_world_destroy(stream_world);
    mw_scene_pack_close(&scene_pack);
#endif
    if (gpu_ready) {
        C3D_FrameSync();
        if (ui_texture_ready) C3D_TexDelete(&ui_texture);
        if (ui_gpu_ready) C2D_Fini();
        C3D_Fini();
    }
    free(event_catalog_bytes);free_mesh(&world);free_mesh(&body);road_free(&road);wheel_rig_free(&wheel_rig);road_map_free(&navigation);
    if (program_ready) shaderProgramFree(&program);
    if (world_program_ready) shaderProgramFree(&world_program);
    if (shader) DVLB_Free(shader);
    if (world_shader) DVLB_Free(world_shader);
    mw_ui_assets_free(ui_assets);gfxExit();return 0;
}
