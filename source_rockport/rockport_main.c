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
#include "mw_world_state.h"
#include "mw_frontend_top.h"
#include "mw_frontend_scene.h"
#include "mw_free_roam.h"
#include "mw_destination_icons.h"
#include "mw_menu_layout.h"
#include "mw_menu_icons.h"
#include "mw_vehicle_catalog.h"
#include "mw_traffic.h"
#include "vehicle_index.h"
#include "mw_career.h"
#include "mw_playable_race.h"
#include "mw_cinema.h"
#include "mw_chase_source.h"
#include "mw_nis.h"
#include "mw_opening_cinema.h"
#include "mw_opening_actors.h"
#include "mw_story_audio.h"
#include "mw_story_services.h"
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
typedef struct { NfsScene scene;NfsVertex *vertices;void *gpu_vertices;uint16_t *indices;WorldBounds *bounds;C3D_Tex textures[NFS_MAX_TEXTURES];unsigned loaded;uint32_t asset_crc,gpu_vertex_count;C3D_BufInfo buffer;float source_center[3],source_extent,frontend_height,frontend_positions[12];bool source_origin,frontend_stance; } Mesh;
typedef enum { MENU,DRIVE,GARAGE,CONTROLS,QUIT,DISPLAY,MOVIE,NIS } Screen;
static Mesh world,body;
static Mesh pending_body,traffic_body,frontend_platform;
static int frontend_platform_id=-1;
static float frontend_platform_scale;
static WheelRig traffic_rig;
static MwVehicleCatalog vehicle_catalog;
static unsigned char *vehicle_catalog_bytes,*traffic_world_bytes;
static MwTrafficWorld traffic_world;
static MwTrafficCar street_cars[4];
static WheelMotion street_wheels[4];
static float traffic_half_extent,traffic_ground_offset,traffic_accumulator;
static const char *active_car_id="BMWM3GTRE46";
typedef enum { FE_TITLE,FE_ALIASES,FE_MAIN,FE_CAREER,FE_QUICK,FE_CHALLENGE,FE_OPTIONS,FE_DELETE,FE_RACE_SETUP,FE_PAUSE,FE_SAFEHOUSE,FE_SHOP,FE_SHOP_SECTION,FE_CAR_CHOICE,FE_PURCHASE,FE_RACE_RESULT } FrontendPage;
static FrontendPage frontend_page=FE_TITLE;
static MwAliasStore aliases;
static unsigned frontend_selected;
static uint32_t alias_delete_id;
static unsigned char *event_catalog_bytes;
static MwEventCatalog event_catalog;
static MwRaceSession race_session;
static MwPlayableRace playable_race;
static MwCareerPack career_pack;
static MwCareer career;
static unsigned char *career_pack_bytes,*race_state_bytes,*camera_asset_bytes;
static MwChaseAsset camera_asset;
static MwCinema cinema;
static MwOpeningCinema opening_cinema;
static float nis_player_source[16];
static float camera_up[3]={0,1,0};
static bool nis_camera_ready;
static MwStoryAudio story_audio;
static MwStoryEngine story_engine;
static float story_simulation_clock;
static MwOpeningActors opening_actors;
static MwRaceAIPack opponent_pack;
static MwPursuitPack pursuit_pack;
static unsigned char *opponent_pack_bytes,*pursuit_pack_bytes;
typedef struct { Mesh mesh;WheelRig rig;WheelMotion wheels;float extent,ground; } ActorVisual;
static ActorVisual opponent_visuals[MW_RACE_AI_ACTORS],police_visual;
static WheelMotion police_wheels[MW_PURSUIT_COPS];

static bool career_playing,race_spawn_pending,career_phase_pending;
static uint32_t loaded_career_step=UINT32_MAX;
static MwCareerPhase presented_career_phase=MW_CAREER_INACTIVE;
static bool career_save_blocked;
static float original_bmw_extent;
static unsigned race_base_bin=1;
static char career_status[96];
static bool race_results_showing;
static unsigned race_finish_position;
static uint32_t quick_event_keys[512];
static size_t quick_event_count;
static MwFreeRoam free_roam;
static unsigned char *free_roam_bytes;
static MwDestinationIcons destination_icons;
static unsigned char *destination_icon_bytes;
static MwDestination near_destination;
static bool has_near_destination;
static uint32_t frontend_event_key;
static const char *shop_section;
static bool race_from_drive;
static FrontendPage career_back=FE_MAIN;
static MwMenuLayout menu_layout;
static MwMenuIcons menu_icons;
static unsigned char *menu_icon_bytes;
static MwMenuCamera menu_camera;
static MwFrontendScenePack frontend_scene;
static unsigned char *frontend_scene_bytes;
static const char *active_car_name="BMW M3 GTR";
static const char *shop_categories[]={"PARTS","PERFORMANCE","VISUAL","BACK"};
static bool alias_storage_blocked;
static const char *frontend_notice;
static const char *frontend_main_items[]={"CAREER","CHALLENGE SERIES","QUICK RACE","MY CARS","ALIAS MANAGER","OPTIONS"};
#ifdef NFS_STREAMED_WORLD
static StreamedWorld *stream_world;
static MwWorldState world_state;
static unsigned char *world_state_bytes;
static size_t world_state_bytes_size;
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
static const bool piss_filter=true; /* Original-style warm grade is always enabled. */
static unsigned char map_rgb[152*128*3];
/* Rasterize off-screen. The displayed bottom buffer must never be cleared or
   repainted during LCD scanout, even when HUD updates are throttled. */
static unsigned char ui_pixels[MW_UI_BYTES];
static bool ui_pending,ui_gpu_ready,ui_texture_ready;
static C3D_Tex ui_texture,frontend_texture;
static C3D_Tex frontend_logo_texture;
static bool frontend_logo_ready;
static MwFrontendTop frontend_art;
static unsigned char *frontend_art_bytes;
static unsigned char frontend_pixels[MW_FRONTEND_TOP_BYTES];
static bool frontend_pending,frontend_texture_ready;
static Tex3DS_SubTexture frontend_subtexture={.width=400,.height=240,.left=0,.top=1,.right=400.f/512,.bottom=1-240.f/256};
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
    if(frontend_page==FE_PAUSE)return 3;
    if(frontend_page==FE_SAFEHOUSE||frontend_page==FE_SHOP||frontend_page==FE_CAR_CHOICE)return 4;
    if(frontend_page==FE_CAREER||frontend_page==FE_PURCHASE||frontend_page==FE_RACE_SETUP)return 2;
    if(frontend_page==FE_RACE_RESULT)return 3;
    if(frontend_page==FE_QUICK)return quick_event_count?(unsigned)quick_event_count:1;
    return frontend_page==FE_OPTIONS?3:1;
}
static bool frontend_icons(void)
{
    static const MwMenuAction main_actions[]={MW_MENU_CAREER,MW_MENU_CHALLENGE,MW_MENU_QUICK_RACE,MW_MENU_MY_CARS,MW_MENU_ALIAS,MW_MENU_OPTIONS};
    static const MwMenuAction safe_actions[]={MW_MENU_CAREER,MW_MENU_MY_CARS,MW_MENU_RESUME_FREE_ROAM,MW_MENU_MAIN_MENU};
    static const MwMenuAction shop_actions[]={MW_MENU_PARTS,MW_MENU_PERFORMANCE,MW_MENU_VISUAL,MW_MENU_BACK};
    static const MwMenuAction pause_actions[]={MW_MENU_RESUME_FREE_ROAM,MW_MENU_JUMP_SAFEHOUSE,MW_MENU_MAIN_MENU};
    static const MwMenuAction career_actions[]={MW_MENU_NEW_CAREER,MW_MENU_RESUME_CAREER};
    const MwMenuAction *actions=NULL;unsigned count=0;
    if(frontend_page==FE_MAIN){actions=main_actions;count=6;}
    else if(frontend_page==FE_SAFEHOUSE){actions=safe_actions;count=4;}
    else if(frontend_page==FE_SHOP){actions=shop_actions;count=4;}
    else if(frontend_page==FE_PAUSE){actions=pause_actions;count=3;}
    else if(frontend_page==FE_CAREER){actions=career_actions;count=2;}
    return actions&&mw_menu_layout_init(&menu_layout,actions,count,frontend_selected);
}
static void frontend_model(MwUiModel *ui)
{
    ui->mode=frontend_page==FE_TITLE?MW_UI_TITLE:MW_UI_FRONTEND;
    ui->car_name=active_car_name;
    if(frontend_icons()){ui->icon_menu=&menu_layout;ui->menu_icons=&menu_icons;}
    ui->alias_name=mw_alias_selected_name(&aliases);
    if(frontend_page==FE_DELETE)for(unsigned i=0;i<aliases.count;i++)if(aliases.aliases[i].id==alias_delete_id)ui->alias_name=aliases.aliases[i].name;
    ui->frontend_title=(const char*[]){"MOST WANTED","ALIAS MANAGER","MAIN MENU","CAREER","QUICK RACE","CHALLENGE SERIES","OPTIONS","DELETE ALIAS?","RACE SETUP","PAUSED","SAFE HOUSE","PARTS SHOP","PARTS","CHOOSE YOUR CAR","PURCHASE CAR","RACE COMPLETE"}[frontend_page];
    unsigned rows=frontend_rows(),base=frontend_selected>=6?frontend_selected-5:0;
    ui->selected=frontend_selected-base;ui->frontend_count=rows-base>6?6:rows-base;
    for(unsigned i=0;i<ui->frontend_count;i++){
        unsigned row=base+i;
        ui->frontend_rows[i]=frontend_page==FE_ALIASES?(row?aliases.aliases[row-1].name:"CREATE ALIAS"):
            frontend_page==FE_MAIN?frontend_main_items[row]:
            frontend_page==FE_OPTIONS?(const char*[]){"CONTROLS","BACK","EXIT"}[row]:
            frontend_page==FE_DELETE?(row?"CANCEL":"DELETE"):
            frontend_page==FE_PAUSE?(const char*[]){"RESUME","JUMP TO SAFE HOUSE","MAIN MENU"}[row]:
            frontend_page==FE_SAFEHOUSE?(const char*[]){"CAREER","MY CARS","RESUME FREE ROAM","MAIN MENU"}[row]:
            frontend_page==FE_SHOP?shop_categories[row]:
            frontend_page==FE_SHOP_SECTION?"UPGRADES NOT AVAILABLE YET":
            frontend_page==FE_CAREER?(row?"RESUME CAREER":"NEW CAREER"):
            frontend_page==FE_PURCHASE?(row?"CANCEL":"BUY THIS CAR"):
            frontend_page==FE_RACE_RESULT?(const char*[]){"CONTINUE","RETRY","MAIN MENU"}[row]:
            frontend_page==FE_RACE_SETUP?(row?"BACK":"START RACE"):"NOT AVAILABLE IN THIS VERSION";
        if(frontend_page==FE_CAR_CHOICE){MwCareerCar car;MwVehicleSpec spec;if(mw_career_car(&career_pack,row,&car)&&mw_vehicle_catalog_find_frontend(&vehicle_catalog,car.key,&spec))ui->frontend_rows[i]=spec.display_name;}
        if(frontend_page==FE_QUICK&&quick_event_count){MwEventDefinition event;if(mw_event_catalog_find(&event_catalog,quick_event_keys[row],&event))ui->frontend_rows[i]=event.display_title;}
    }
    if(frontend_page==FE_RACE_SETUP){ui->frontend_title_body=true;MwEventDefinition event;if(mw_event_catalog_find(&event_catalog,frontend_event_key,&event))ui->frontend_title=event.display_title;}
    if(frontend_page==FE_SHOP_SECTION)ui->frontend_title=shop_section;
    ui->frontend_hint=frontend_notice?frontend_notice:frontend_page==FE_ALIASES?"A: LOAD  X: RENAME  Y: DELETE":
        frontend_page==FE_MAIN?"A: SELECT  Y: EXPLORE ROCKPORT":"A: SELECT  B: BACK";
    if(frontend_page==FE_CAR_CHOICE||frontend_page==FE_PURCHASE){
        MwCareerCar choice;uint32_t key=career.selected_car;
        if(frontend_page==FE_CAR_CHOICE&&mw_career_car(&career_pack,frontend_selected,&choice))key=choice.key;
        for(unsigned i=0;i<MW_CAREER_CARS;i++)if(mw_career_car(&career_pack,i,&choice)&&choice.key==key){
            snprintf(career_status,sizeof(career_status),"CASH $%lu  PRICE $%lu",(unsigned long)career.cash,(unsigned long)choice.cost);
            if(!frontend_notice)ui->frontend_hint=career_status;
            break;
        }
    }
    if(frontend_page==FE_RACE_RESULT&&!frontend_notice){
        if(race_finish_position)snprintf(career_status,sizeof(career_status),"POSITION %u  TIME %lu.%03lu",race_finish_position,(unsigned long)(race_session.progress.elapsed_us/1000000),(unsigned long)(race_session.progress.elapsed_us/1000%1000));
        else snprintf(career_status,sizeof(career_status),"TIME %lu.%03lu  PRACTICE",(unsigned long)(race_session.progress.elapsed_us/1000000),(unsigned long)(race_session.progress.elapsed_us/1000%1000));
        ui->frontend_hint=career_status;
    }
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
    mesh->gpu_vertex_count=mesh->scene.vertex_count;bool packed_vehicle=false;
    if(!is_world){
        VehicleIndexedVertices indexed={0};
        if(vehicle_index_encode(mesh->scene.vertices,mesh->scene.vertex_count,&indexed)==VEHICLE_INDEX_OK){
            size_t vertex_bytes=indexed.vertex_count*stride,index_offset=(vertex_bytes+127)&~(size_t)127;
            size_t used=index_offset+indexed.index_count*2,total=(used+127)&~(size_t)127;
            mesh->gpu_vertices=linearAlloc(total);
            if(mesh->gpu_vertices){
                memset(mesh->gpu_vertices,0,total);memcpy(mesh->gpu_vertices,indexed.vertices,vertex_bytes);
                mesh->indices=(uint16_t*)((unsigned char*)mesh->gpu_vertices+index_offset);
                memcpy(mesh->indices,indexed.indices,indexed.index_count*2);mesh->gpu_vertex_count=indexed.vertex_count;
                gpu_bytes=total;packed_vehicle=true;
            }
        }
        vehicle_index_free(&indexed);
    }
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
        if(!packed_vehicle)memcpy(mesh->vertices,mesh->scene.vertices,mesh->scene.vertex_count*stride);
        for (uint32_t i=0;i<mesh->gpu_vertex_count;++i) mesh->vertices[i].uv[1]=1-mesh->vertices[i].uv[1];
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
    memset(mesh,0,sizeof(*mesh));
}
static uint32_t origin_crc(const unsigned char *p,size_t n)
{uint32_t c=~0u;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
static bool load_vehicle_origin(Mesh *mesh,const char *path)
{
    size_t bytes;unsigned char *raw=read_file(path,&bytes);if(!raw)return false;
    uint32_t version=0,key=0,crc=0;
    if(bytes==32){memcpy(&version,raw+4,4);memcpy(&key,raw+8,4);memcpy(&crc,raw+28,4);}
    bool ok=bytes==32&&!memcmp(raw,"NVO1",4)&&version==1&&key==mesh->asset_crc&&crc==origin_crc(raw,28);
    if(ok){
        memcpy(&mesh->source_extent,raw+12,4);memcpy(mesh->source_center,raw+16,12);
        ok=isfinite(mesh->source_extent)&&mesh->source_extent>0&&mesh->source_extent<10;
        for(unsigned a=0;a<3;a++)ok=ok&&isfinite(mesh->source_center[a]);
    }
    free(raw);mesh->source_origin=ok;return ok;
}
static bool load_frontend_stance(Mesh *mesh,const char *directory,uint32_t ecar)
{
    char path[192];snprintf(path,sizeof(path),"%sbody.stance",directory);
    size_t bytes;unsigned char *raw=read_file(path,&bytes);if(!raw)return false;
    uint32_t key=0,crc=0;if(bytes==16){memcpy(&key,raw+8,4);memcpy(&crc,raw+12,4);}
    bool ok=bytes==16&&!memcmp(raw,"NFG1",4)&&key==ecar&&crc==origin_crc(raw,12);
    if(ok){memcpy(&mesh->frontend_height,raw+4,4);ok=isfinite(mesh->frontend_height)&&fabsf(mesh->frontend_height)<2;}
    free(raw);if(!ok)return false;
    snprintf(path,sizeof(path),"%swheels.frontend",directory);raw=read_file(path,&bytes);if(!raw)return false;
    uint32_t version=0;if(bytes==64){memcpy(&key,raw+4,4);memcpy(&version,raw+56,4);memcpy(&crc,raw+60,4);}
    ok=bytes==64&&!memcmp(raw,"NFW2",4)&&key==ecar&&version==2&&crc==origin_crc(raw,60);
    if(ok){memcpy(mesh->frontend_positions,raw+8,48);for(unsigned i=0;i<12;i++)ok=ok&&isfinite(mesh->frontend_positions[i])&&fabsf(mesh->frontend_positions[i])<10;}
    free(raw);mesh->frontend_stance=ok;return ok;
}
static bool load_catalog_vehicle(Mesh *mesh,WheelRig *rig,const MwVehicleSpec *spec)
{
    char path[160],textures[160];snprintf(path,sizeof(path),"cars/%s/body.nfm",spec->id);
    snprintf(textures,sizeof(textures),"cars/%s/textures",spec->id);
    if(!load_mesh(mesh,path,textures)||mesh->asset_crc!=spec->body_crc)return false;
    snprintf(path,sizeof(path),ROOT "cars/%s/wheels.nwa",spec->id);
    size_t size;void *raw=read_file(path,&size);if(!raw)return false;
    bool ok=wheel_rig_decode(raw,size,mesh->scene.batch_count,mesh->asset_crc,rig);free(raw);
    snprintf(path,sizeof(path),ROOT "cars/%s/body.origin",spec->id);
    if(!ok||!load_vehicle_origin(mesh,path))return false;
    snprintf(path,sizeof(path),ROOT "cars/%s/",spec->id);
    return load_frontend_stance(mesh,path,spec->ecar_key);
}
static bool select_player_vehicle(const char *id)
{
    if(!strcmp(id,active_car_id))return true;
    bool bmw=!strcmp(id,"BMWM3GTRE46");
    MwVehicleSpec spec={.id="BMWM3GTRE46",.display_name="BMW M3 GTR",.half_extent=original_bmw_extent};
    if(!bmw&&!mw_vehicle_catalog_find_id(&vehicle_catalog,id,&spec))return false;
    C3D_FrameSync();WheelRig rig={0};
    bool loaded;
    if(bmw){
        loaded=load_mesh(&pending_body,"body.nfm","car-textures");
        size_t size=0;void *raw=loaded?read_file(ROOT "wheels.nwa",&size):NULL;
        loaded=raw&&wheel_rig_decode(raw,size,pending_body.scene.batch_count,pending_body.asset_crc,&rig);free(raw);
        loaded=loaded&&load_vehicle_origin(&pending_body,ROOT "body.origin")&&load_frontend_stance(&pending_body,ROOT,0x4e085fb3);
    }else loaded=load_catalog_vehicle(&pending_body,&rig,&spec);
    if(!loaded){
        free_mesh(&pending_body);wheel_rig_free(&rig);return false;
    }
    free_mesh(&body);wheel_rig_free(&wheel_rig);body=pending_body;memset(&pending_body,0,sizeof(pending_body));wheel_rig=rig;
    road.car_half_extent=spec.half_extent;car_ground_offset=0;
    for(uint32_t i=0;i<body.gpu_vertex_count;i++)car_ground_offset=fmaxf(car_ground_offset,-body.vertices[i].position[1]*road.car_half_extent);
    active_car_name=spec.display_name;active_car_id=spec.id;return true;
}
static bool refresh_frontend_platform(Screen screen)
{
    if(screen==DRIVE||screen==QUIT||screen==MOVIE||screen==NIS){
        if(frontend_platform.loaded){C3D_FrameSync();free_mesh(&frontend_platform);}frontend_platform_id=-1;return true;
    }
    int wanted=frontend_page==FE_SAFEHOUSE||frontend_page==FE_CAREER?1:frontend_page==FE_SHOP||frontend_page==FE_SHOP_SECTION?2:frontend_page==FE_CAR_CHOICE||frontend_page==FE_PURCHASE?3:0;
    if(frontend_platform_id==wanted)return true;
    C3D_FrameSync();free_mesh(&frontend_platform);frontend_platform_id=-1;
#ifdef NFS_STREAMED_WORLD
    streamed_world_suspend(stream_world);stream_has_frame=false;stream_load_announced=false;
#endif
    static const char *names[]={"PLATFORMCRIB","CAREER_SAFEHOUSE","CUSTOMIZATION_SHOP","CAR_LOT"};
    char path[160],textures[160];snprintf(path,sizeof(path),ROOT "platforms/%s/placement.bin",names[wanted]);
    size_t bytes;unsigned char *raw=read_file(path,&bytes);
    if(!raw||bytes!=16||memcmp(raw,"NPS1\1\0\0\0",8)){free(raw);return false;}
    float scale;uint32_t crc;memcpy(&scale,raw+8,4);memcpy(&crc,raw+12,4);free(raw);
    if(!isfinite(scale)||scale<=0||scale>1000)return false;
    snprintf(path,sizeof(path),"platforms/%s/platform.nfm",names[wanted]);
    snprintf(textures,sizeof(textures),"platforms/%s/textures",names[wanted]);
    if(!load_mesh(&frontend_platform,path,textures)||frontend_platform.asset_crc!=crc){free_mesh(&frontend_platform);return false;}
    frontend_platform_scale=scale;frontend_platform_id=wanted;return true;
}
static void spawn_street_cars(const DriveState *player,float height)
{
    memset(street_cars,0,sizeof(street_cars));memset(street_wheels,0,sizeof(street_wheels));traffic_accumulator=0;
    if(!traffic_world.data||!traffic_body.loaded)return;
    const float distances[4]={45,95,-55,-105};
    for(unsigned i=0;i<4;i++){
        float point[3]={player->z+road.origin[2]+cosf(player->heading)*distances[i],height+road.origin[1],player->x+road.origin[0]+sinf(player->heading)*distances[i]};
        uint16_t segment;float u;MwTrafficWork work={0};
        if(mw_traffic_nearest(&traffic_world,point,50,&segment,&u,NULL,NULL,&work))
            (void)mw_traffic_start(&traffic_world,street_cars+i,segment,i&1,u,8.0f+(float)i,NULL,NULL,&work);
    }
}
static void update_street_cars(const DriveState *player,float seconds)
{
    traffic_accumulator+=seconds;if(traffic_accumulator<1.f/30)return;
    float dt=fminf(traffic_accumulator,.1f);traffic_accumulator=0;
    for(unsigned i=0;i<4;i++){
        MwTrafficCar *c=street_cars+i;if(!c->active)continue;
        float dx=c->position[2]-road.origin[0]-player->x,dz=c->position[0]-road.origin[2]-player->z;
        if(dx*dx+dz*dz>220.f*220.f)continue;
        MwTrafficCar candidate=*c;MwTrafficWork work={0};
        if(mw_traffic_step(&traffic_world,&candidate,dt,NULL,NULL,&work)<0)continue;
#ifdef NFS_STREAMED_WORLD
        WorldCollisionContact wall;
        float a[3]={c->position[0],c->position[1]+.8f,c->position[2]},b[3]={candidate.position[0],candidate.position[1]+.8f,candidate.position[2]};
        if(collision_world.ready&&world_collision_runtime_wall(&collision_world,a,b,0,&wall)!=0)continue;
#endif
        DriveState old={.x=c->position[2],.z=c->position[0]},next={.x=candidate.position[2],.z=candidate.position[0]};
        (void)wheel_motion_update(&traffic_rig,street_wheels+i,&old,&next);*c=candidate;
    }
}
static void free_actor_visual(ActorVisual *v)
{free_mesh(&v->mesh);wheel_rig_free(&v->rig);memset(v,0,sizeof(*v));}
static bool load_actor_visual(ActorVisual *v,const char *id)
{
    MwVehicleSpec spec;if(!mw_vehicle_catalog_find_id(&vehicle_catalog,id,&spec))return false;
    if(!load_catalog_vehicle(&v->mesh,&v->rig,&spec)){free_actor_visual(v);return false;}
    v->extent=spec.half_extent;
    for(uint32_t i=0;i<v->mesh.gpu_vertex_count;i++)v->ground=fmaxf(v->ground,-v->mesh.vertices[i].position[1]*v->extent);
    return true;
}
static void reset_opening_actors(void)
{
    mw_opening_actors_reset(&opening_actors);
    for(unsigned i=0;i<MW_RACE_AI_ACTORS;i++)free_actor_visual(opponent_visuals+i);
    free_actor_visual(&police_visual);memset(police_wheels,0,sizeof(police_wheels));
}
static bool begin_opening_actors(uint32_t event,uintptr_t actor,const float source[3])
{
    C3D_FrameSync();reset_opening_actors();
    if(!mw_opening_actors_begin(&opening_actors,&opponent_pack,&pursuit_pack,&event_catalog,&traffic_world,event,road.origin,actor,source))return false;
    for(unsigned i=0;i<opening_actors.race.count;i++)
        if(!load_actor_visual(opponent_visuals+i,opening_actors.race.actors[i].spec.model))return false;
    if(opening_actors.pursuit.has_event&&!load_actor_visual(&police_visual,"COPMIDSIZE"))return false;
    return true;
}
#ifdef NFS_STREAMED_WORLD
static int opening_actor_drive(void *context,DriveState *car,float *height,DriveInput input,float dt)
{
    /* The same admitted world collision/ground service as the player. Never
       substitute unchecked kinematic motion when a source section is absent. */
    return streamed_drive_step(context,car,height,input,dt);
}
#endif
static bool scripted_opening(void)
{
    MwCareerStage stage;
    return career_playing&&career.phase==MW_CAREER_RACING&&mw_career_stage(&career_pack,career.step,&stage)&&stage.flags!=0;
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
    original_bmw_extent=road.car_half_extent;
    if(!load_vehicle_origin(&body,ROOT "body.origin")||!load_frontend_stance(&body,ROOT,0x4e085fb3)){snprintf(error,sizeof(error),"Invalid original vehicle origin");return false;}
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
    free_roam_bytes=read_file(ROOT "free-roam.nfd",&size);
    if(!free_roam_bytes||!mw_free_roam_open(&free_roam,free_roam_bytes,size)){snprintf(error,sizeof(error),"Cannot read/validate free-roam.nfd");return false;}
    destination_icon_bytes=read_file(ROOT "destination-icons.nfi",&size);
    if(!destination_icon_bytes||!mw_destination_icons_open(&destination_icons,destination_icon_bytes,size)){snprintf(error,sizeof(error),"Cannot read/validate destination-icons.nfi");return false;}
    menu_icon_bytes=read_file(ROOT "menu-icons.nmi",&size);
    if(!menu_icon_bytes||!mw_menu_icons_open(&menu_icons,menu_icon_bytes,size)){snprintf(error,sizeof(error),"Cannot read/validate menu-icons.nmi");return false;}
    vehicle_catalog_bytes=read_file(ROOT "cars/catalog.nvc",&size);
    if(!vehicle_catalog_bytes||!mw_vehicle_catalog_open(&vehicle_catalog,vehicle_catalog_bytes,size)){snprintf(error,sizeof(error),"Cannot read/validate cars/catalog.nvc");return false;}
    career_pack_bytes=read_file(ROOT "opening-career.nfc",&size);
    if(!career_pack_bytes||!mw_career_pack_open(&career_pack,career_pack_bytes,size)){snprintf(error,sizeof(error),"Cannot read/validate opening-career.nfc");return false;}
    frontend_scene_bytes=read_file(ROOT "frontend-scene.nfp",&size);
    if(!frontend_scene_bytes||!mw_frontend_scene_open(&frontend_scene,frontend_scene_bytes,size)){snprintf(error,sizeof(error),"Invalid frontend-scene.nfp");return false;}
    camera_asset_bytes=read_file(ROOT "camera.ncp",&size);
    if(!camera_asset_bytes||!mw_chase_asset_open(&camera_asset,camera_asset_bytes,size)){snprintf(error,sizeof(error),"Cannot read/validate camera.ncp");return false;}
    if(!mw_opening_cinema_open(&opening_cinema,ROOT "opening-nis.nni",ROOT "opening-nis-actors.nna",ROOT "opening-nis-actions.nac")){
        snprintf(error,sizeof(error),"Cannot validate opening NIS packs");return false;
    }
    opponent_pack_bytes=read_file(ROOT "opponents.nro",&size);
    if(!opponent_pack_bytes||!mw_race_ai_pack_open(&opponent_pack,opponent_pack_bytes,size)){snprintf(error,sizeof(error),"Cannot validate opponents.nro");return false;}
    pursuit_pack_bytes=read_file(ROOT "pursuit.npp",&size);
    if(!pursuit_pack_bytes||!mw_pursuit_pack_open(&pursuit_pack,pursuit_pack_bytes,size)){snprintf(error,sizeof(error),"Cannot validate pursuit.npp");return false;}
    traffic_world_bytes=read_file(ROOT "road-network.mwt",&size);
    if(!traffic_world_bytes||!mw_traffic_open(&traffic_world,traffic_world_bytes,size)){snprintf(error,sizeof(error),"Cannot read/validate road-network.mwt");return false;}
    MwVehicleSpec traffic_spec;
    if(!mw_vehicle_catalog_find_id(&vehicle_catalog,"TRAFHA",&traffic_spec)||!load_catalog_vehicle(&traffic_body,&traffic_rig,&traffic_spec))return false;
    traffic_half_extent=traffic_spec.half_extent;
    for(uint32_t i=0;i<traffic_body.gpu_vertex_count;i++)traffic_ground_offset=fmaxf(traffic_ground_offset,-traffic_body.vertices[i].position[1]*traffic_half_extent);
    for (uint32_t i=0;i<body.gpu_vertex_count;++i)
        car_ground_offset=fmaxf(car_ground_offset,-body.vertices[i].position[1]*road.car_half_extent);
#ifdef NFS_STREAMED_WORLD
    snprintf(error,sizeof(error),"Cannot read/validate exploration.nws");
    world_state_bytes=read_file(ROOT "exploration.nws",&size);
    world_state_bytes_size=size;
    if(!world_state_bytes||!mw_world_state_open(&world_state,world_state_bytes,size)||world_state.bin!=1)return false;
    if(memcmp(free_roam.data+32,world_state.data+96,32)||(event_catalog.data&&memcmp(event_catalog.data+64,world_state.data+96,32))){snprintf(error,sizeof(error),"Free-roam gameplay source differs");return false;}
    snprintf(error,sizeof(error),"Cannot read/validate world.mwp archive");
    if (mw_scene_pack_open(&scene_pack,ROOT "world.mwp",2*1024*1024)!=MW_SCENE_PACK_OK) return false;
    StreamedWorldConfig stream_config={.read_asset=streamed_world_pack_read,.read_context=&scene_pack,
        .metadata_path=ROOT "world-streaming.bin",.normal_bytes=12*1024*1024,
        .linear_bytes=20*1024*1024,.scratch_bytes=4*1024*1024,.cache_entries=2048,
        .object_capacity=4096,.run_capacity=32768,.render_scale=road.scale,
        .lod_mode=STREAMED_WORLD_SOURCE_LOD_COMPONENTS,.alpha_reference=40,
        .comparison_zero_transparent_rgb=false,
        .boot_global_provider_bank=true,.original_missing_texture_hash=0x66994f4a,
        .instance_state=mw_world_state_instance,.instance_state_context=&world_state};
    StreamedWorldResult stream_result=streamed_world_create(&stream_config,&stream_world);
    if (stream_result!=STREAMED_WORLD_OK) {
        snprintf(error,sizeof(error),"Cannot initialize streamed map (%d)",(int)stream_result);return false;
    }
    snprintf(error,sizeof(error),"Cannot read/validate original world.nwc collision");
    if (world_collision_runtime_open(&collision_world,ROOT "world.nwc",collision_arena,sizeof(collision_arena))) return false;
    if(!mw_world_state_source_matches(&world_state,collision_world.source_sha256)||
       world_collision_runtime_bind_groups(&collision_world,mw_world_state_group,&world_state)){snprintf(error,sizeof(error),"Collision activation source differs");return false;}
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
    snprintf(error,sizeof(error),"Cannot load frontend-top.nut");
    frontend_art_bytes=read_file(ROOT "frontend-top.nut",&size);
    if(!frontend_art_bytes||!mw_frontend_top_open(&frontend_art,frontend_art_bytes,size)||!C3D_TexInit(&frontend_texture,512,256,GPU_RGBA8))return false;
    frontend_texture_ready=true;C3D_TexSetFilter(&frontend_texture,GPU_NEAREST,GPU_NEAREST);C3D_TexSetWrap(&frontend_texture,GPU_CLAMP_TO_EDGE,GPU_CLAMP_TO_EDGE);
    if(!C3D_TexInit(&frontend_logo_texture,256,64,GPU_RGBA8))return false;
    frontend_logo_ready=true;
    static const unsigned morton[8]={0,1,4,5,16,17,20,21};unsigned char *logo=frontend_logo_texture.data;
    for(unsigned y=0;y<64;y++)for(unsigned x=0;x<256;x++){
        const unsigned char *source=frontend_art.logo+(y*256+x)*4;
        unsigned at=(((y/8)*32+x/8)*64+morton[x&7]+2*morton[y&7])*4;
        logo[at]=source[3];logo[at+1]=source[2];logo[at+2]=source[1];logo[at+3]=source[0];
    }
    C3D_TexFlush(&frontend_logo_texture);C3D_TexSetFilter(&frontend_logo_texture,GPU_LINEAR,GPU_LINEAR);
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
static void draw_vehicle(Mesh *mesh,const WheelRig *rig,const C3D_Mtx *parent,const WheelMotion *motion,float steering,const float *frontend_positions)
{
    C3D_BindProgram(&program);C3D_SetAttrInfo(&car_attributes);
    C3D_AlphaTest(true,GPU_GREATER,0);
    C3D_AlphaBlend(GPU_BLEND_ADD,GPU_BLEND_ADD,GPU_SRC_ALPHA,GPU_ONE_MINUS_SRC_ALPHA,GPU_ONE,GPU_ONE_MINUS_SRC_ALPHA);
    C3D_Mtx models[5];models[0]=*parent;
    for (unsigned i=0;i<4;++i) {
        const Wheel *wheel=&rig->wheels[i];const float *p=wheel->pivot;
        C3D_Mtx local;Mtx_Identity(&local);
        float target[3]={p[0],p[1],p[2]};
        if(frontend_positions){
            /* Older fitted rigs iterate side then axle; the original ecar
               providers iterate axle then side. Bind by real front/side,
               then translate FROM the rig's actual existing art pivot. */
            unsigned slot=wheel->front?0:2;
            float source_y=-(p[2]*mesh->source_extent+mesh->source_center[2]);
            if(fabsf(frontend_positions[slot*3+1]-source_y)>fabsf(frontend_positions[(slot+1)*3+1]-source_y))slot++;
            target[0]=(frontend_positions[slot*3]-mesh->source_center[0])/mesh->source_extent;
            target[1]=(frontend_positions[slot*3+2]-mesh->source_center[1])/mesh->source_extent;
            target[2]=(-frontend_positions[slot*3+1]-mesh->source_center[2])/mesh->source_extent;
        }
        Mtx_Translate(&local,target[0],target[1],target[2],true);
        if (wheel->front) Mtx_RotateY(&local,steering,true);
        Mtx_RotateZ(&local,motion->angle[i],true);
        Mtx_Translate(&local,-p[0],-p[1],-p[2],true);
        Mtx_Multiply(&models[i+1],parent,&local);
    }
    C3D_SetBufInfo(&mesh->buffer);
    for (unsigned pass=0;pass<2;++pass) {
        C3D_DepthTest(true,GPU_GREATER,pass?GPU_WRITE_COLOR:GPU_WRITE_ALL);
        unsigned current=5;
        for (uint32_t i=0;i<mesh->scene.batch_count;++i) {
            NfsBatch *b=&mesh->scene.batches[i];
            if ((bool)(mesh->scene.textures[b->texture].flags&1)!=(bool)pass) continue;
            unsigned group=rig->groups[i];
            if (group!=current) { C3D_FVUnifMtx4x4(GPU_VERTEX_SHADER,model_loc,&models[group]);current=group; }
            C3D_TexBind(0,&mesh->textures[b->texture]);
            if(mesh->indices)C3D_DrawElements(GPU_TRIANGLES,(int)b->count,C3D_UNSIGNED_SHORT,mesh->indices+b->first);
            else C3D_DrawArrays(GPU_TRIANGLES,b->first,b->count);
        }
    }
}
static void draw_car(const C3D_Mtx *parent,const WheelMotion *motion,float steering,bool frontend)
{draw_vehicle(&body,&wheel_rig,parent,motion,steering,frontend?body.frontend_positions:NULL);}

static void draw_actor(ActorVisual *visual,const DriveState *car,float height,const WheelMotion *wheels,const C3D_Mtx *view)
{
    if(!visual->mesh.loaded)return;
    float dx=car->x-chase.eye[0],dz=car->z-chase.eye[2];
    float fx=chase.target[0]-chase.eye[0],fz=chase.target[2]-chase.eye[2];
    if(dx*dx+dz*dz>180.f*180.f||dx*fx+dz*fz < -8.f)return;
    C3D_Mtx model,combined;float scale=road.scale;
    Mtx_Identity(&model);Mtx_Translate(&model,car->x*scale,(height+visual->ground)*scale,car->z*scale,true);
    Mtx_RotateY(&model,car->heading-1.5707963f,true);
    Mtx_Scale(&model,visual->extent*scale,visual->extent*scale,visual->extent*scale);
    Mtx_Multiply(&combined,view,&model);draw_vehicle(&visual->mesh,&visual->rig,&combined,wheels,car->steering,NULL);
}
static bool draw_nis_actor(Mesh *mesh,const WheelRig *rig,const WheelMotion *wheels,unsigned slot,const C3D_Mtx *view)
{
    if(slot>=MW_OPENING_NIS_ACTORS||!opening_cinema.actors[slot].present||!mesh->source_origin)return false;
    const float *m=opening_cinema.actors[slot].source_world;
    /* Geometry is normalized viewerXYZ; source row-vector transform is
       conjugated by viewer=(sourceX,sourceZ,-sourceY). Restore the real art
       bbox center before applying it. This raw-pose preview deliberately
       does not render SuspensionSpline's ground+5 temporary body position. */
    static const unsigned axis[3]={0,2,1};static const float sign[3]={1,1,-1};
    C3D_Mtx model,combined;Mtx_Identity(&model);
    for(unsigned row=0;row<3;row++){
        float translation=sign[row]*m[12+axis[row]];
        for(unsigned col=0;col<3;col++){
            float rotation=sign[row]*sign[col]*m[axis[col]*4+axis[row]];
            model.r[row].c[3-col]=rotation*mesh->source_extent*road.scale;
            translation+=rotation*mesh->source_center[col];
        }
        model.r[row].w=(translation-road.origin[row])*road.scale;
    }
    Mtx_Multiply(&combined,view,&model);draw_vehicle(mesh,rig,&combined,wheels,0,NULL);return true;
}
static void render(Screen screen,const DriveState *car,float height,float rotation,
                   const WheelMotion *motion,float garage_steering,const RoadPose *pose)
{
    if(screen==MOVIE){mw_cinema_draw(&cinema,target);return;}
    C3D_RenderTargetClear(target,C3D_CLEAR_ALL,mw_color_grade_clear(screen==DRIVE?0x718699ff:0x141414ff,piss_filter),0);
    C3D_FrameDrawOn(target);
    if(screen!=DRIVE&&frontend_texture_ready&&!frontend_platform.loaded){
        C2D_Prepare();C2D_SceneBegin(target);C3D_DepthTest(false,GPU_ALWAYS,GPU_WRITE_COLOR);C3D_AlphaTest(false,GPU_ALWAYS,0);
        C2D_Image backdrop={.tex=&frontend_texture,.subtex=&frontend_subtexture};C2D_DrawImageAt(backdrop,0,0,0,NULL,1,1);C2D_Flush();
    }
    mw_color_grade_apply(piss_filter);C3D_CullFace(GPU_CULL_NONE);C3D_Mtx projection,model;
    C3D_BindProgram(&program);
    C3D_FVUnifSet(GPU_VERTEX_SHADER,lighting_loc,.5f,.5f,0,0);
    if (screen==DRIVE||screen==NIS) {
        (void)height;float scale=road.scale;
        float camera_eye[3],camera_at[3];
        for (unsigned a=0;a<3;++a) { camera_eye[a]=chase.eye[a]*scale;camera_at[a]=chase.target[a]*scale; }
        C3D_FVec eye=FVec3_New(camera_eye[0],camera_eye[1],camera_eye[2]);
        C3D_FVec at=FVec3_New(camera_at[0],camera_at[1],camera_at[2]);
        C3D_FVec up=FVec3_New(camera_up[0],camera_up[1],camera_up[2]);
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
        C3D_Mtx combined;Mtx_Multiply(&combined,&view,&model);
        if(screen!=NIS||!draw_nis_actor(&body,&wheel_rig,motion,0,&view))draw_car(&combined,motion,car->steering,false);
        if(opening_actors.prepared){
            for(unsigned i=0;i<opening_actors.race.count;i++){
                const MwRaceAIActor *actor=opening_actors.race.actors+i;
                if(screen!=NIS||!draw_nis_actor(&opponent_visuals[i].mesh,&opponent_visuals[i].rig,&opponent_visuals[i].wheels,i+1,&view))draw_actor(opponent_visuals+i,&actor->motion,actor->height,&opponent_visuals[i].wheels,&view);
            }
            for(unsigned i=0;i<MW_PURSUIT_COPS;i++){
                const MwPursuitCar *actor=opening_actors.pursuit.actors+i;
                if(screen==NIS&&draw_nis_actor(&police_visual.mesh,&police_visual.rig,police_wheels+i,i+8,&view))continue;
                if(actor->active)draw_actor(&police_visual,&actor->motion,actor->height,police_wheels+i,&view);
            }
        }
        /* One cached900-triangle source traffic mesh, shared by at most four
           actors. Cull before model/uniform work; no per-actor asset loads. */
        for(unsigned i=0;i<4;i++){
            const MwTrafficCar *actor=street_cars+i;if(!actor->active)continue;
            float x=actor->position[2]-road.origin[0],z=actor->position[0]-road.origin[2],y=actor->position[1]-road.origin[1];
            float dx=x-chase.eye[0],dz=z-chase.eye[2],fx=chase.target[0]-chase.eye[0],fz=chase.target[2]-chase.eye[2];
            if(dx*dx+dz*dz>140.f*140.f||dx*fx+dz*fz<0)continue;
            Mtx_Identity(&model);Mtx_Translate(&model,x*scale,(y+traffic_ground_offset)*scale,z*scale,true);
            Mtx_RotateY(&model,atan2f(actor->forward[2],actor->forward[0])-1.5707963f,true);
            Mtx_Scale(&model,traffic_half_extent*scale,traffic_half_extent*scale,traffic_half_extent*scale);
            Mtx_Multiply(&combined,&view,&model);draw_vehicle(&traffic_body,&traffic_rig,&combined,street_wheels+i,0,NULL);
        }
    } else {
        C3D_Mtx environment;
        MwFrontendSceneCamera original_camera;MwFrontendScenePlacement placement;
        const char *camera_name=screen==GARAGE?"angle19":frontend_platform_id==1?"angle_final_career_safehouse":frontend_platform_id==2?"angle_final_customization_shop":frontend_platform_id==3?"angle_carlot_car_select":frontend_page==FE_CHALLENGE?"angle_challengeseries":frontend_page==FE_QUICK||frontend_page==FE_OPTIONS||frontend_page==FE_ALIASES?"angle99":"angle3";
        const unsigned garage_types[]={1,2,3,5};
        bool source_view=frontend_platform.loaded&&frontend_platform_id>=0&&frontend_platform_id<4&&
            mw_frontend_scene_camera(&frontend_scene,camera_name,&original_camera)&&
            mw_frontend_scene_placement(&frontend_scene,garage_types[frontend_platform_id],&placement);
        if(source_view){
            C3D_FVec eye=FVec3_New(original_camera.eye[0],original_camera.eye[2],-original_camera.eye[1]);
            C3D_FVec at=FVec3_New(original_camera.target[0],original_camera.target[2],-original_camera.target[1]);
            C3D_FVec up=FVec3_New(original_camera.up[0],original_camera.up[2],-original_camera.up[1]);
            C3D_Mtx view,local;Mtx_LookAt(&view,eye,at,up,false);
            Mtx_PerspTilt(&projection,C3D_AngleFromDegrees(original_camera.fov_degrees),C3D_AspectRatioTop,.05f,400,false);
            Mtx_Identity(&local);Mtx_Translate(&local,placement.geometry_position[0],placement.geometry_position[2],-placement.geometry_position[1],true);
            Mtx_RotateY(&local,C3D_AngleFromDegrees(placement.geometry_z_degrees),true);
            Mtx_Scale(&local,frontend_platform_scale,frontend_platform_scale,frontend_platform_scale);
            Mtx_Multiply(&environment,&view,&local);
            /* Original RenderingCar providers: source tire offsets/radii and
               FECompressions determine body height and each wheel translation. */
            float height=body.frontend_height;
            Mtx_Identity(&local);Mtx_Translate(&local,0,height,0,true);
            Mtx_RotateY(&local,C3D_AngleFromDegrees(placement.car_rotation_degrees[2])+(screen==GARAGE?rotation:0),true);
            Mtx_RotateZ(&local,-C3D_AngleFromDegrees(placement.car_rotation_degrees[1]),true);
            Mtx_RotateX(&local,C3D_AngleFromDegrees(placement.car_rotation_degrees[0]),true);
            Mtx_Translate(&local,body.source_center[0],body.source_center[1],body.source_center[2],true);
            Mtx_Scale(&local,road.car_half_extent,road.car_half_extent,road.car_half_extent);
            Mtx_Multiply(&model,&view,&local);
        }else{
            MwMenuCameraPose camera=menu_camera.current;
            Mtx_PerspTilt(&projection,C3D_AngleFromDegrees(camera.fov),C3D_AspectRatioTop,.1f,20,false);
            Mtx_Identity(&model);Mtx_Translate(&model,camera.x,camera.y,-camera.distance,true);Mtx_RotateX(&model,camera.pitch,true);Mtx_RotateY(&model,camera.yaw+(screen==GARAGE?rotation:0),true);Mtx_RotateZ(&model,camera.roll,true);
            environment=model;Mtx_Translate(&environment,0,-car_ground_offset/road.car_half_extent,0,true);
            float scale=frontend_platform_scale/road.car_half_extent;Mtx_Scale(&environment,scale,scale,scale);
        }
        C3D_FVUnifMtx4x4(GPU_VERTEX_SHADER,projection_loc,&projection);
        if(frontend_platform.loaded){
            C3D_SetAttrInfo(&car_attributes);C3D_SetBufInfo(&frontend_platform.buffer);
            C3D_FVUnifMtx4x4(GPU_VERTEX_SHADER,model_loc,&environment);C3D_FVUnifSet(GPU_VERTEX_SHADER,lighting_loc,1,0,0,0);
            C3D_AlphaTest(true,GPU_GREATER,40);
            for(unsigned pass=0;pass<2;pass++){
                C3D_DepthTest(true,GPU_GREATER,pass?GPU_WRITE_COLOR:GPU_WRITE_ALL);
                C3D_AlphaBlend(GPU_BLEND_ADD,GPU_BLEND_ADD,pass?GPU_SRC_ALPHA:GPU_ONE,pass?GPU_ONE_MINUS_SRC_ALPHA:GPU_ZERO,GPU_ONE,GPU_ZERO);
                for(uint32_t i=0;i<frontend_platform.scene.batch_count;i++){
                    NfsBatch *b=frontend_platform.scene.batches+i;
                    if((bool)(frontend_platform.scene.textures[b->texture].flags&1)!=(bool)pass)continue;
                    C3D_TexBind(0,&frontend_platform.textures[b->texture]);
                    if(frontend_platform.indices)C3D_DrawElements(GPU_TRIANGLES,(int)b->count,C3D_UNSIGNED_SHORT,frontend_platform.indices+b->first);
                    else C3D_DrawArrays(GPU_TRIANGLES,b->first,b->count);
                }
            }
            C3D_FVUnifSet(GPU_VERTEX_SHADER,lighting_loc,.5f,.5f,0,0);
        }
        draw_car(&model,motion,garage_steering,true);
        if(frontend_platform.loaded&&frontend_logo_ready){
            static const Tex3DS_SubTexture sub={.width=256,.height=64,.left=0,.top=1,.right=1,.bottom=0};
            C2D_Prepare();C2D_SceneBegin(target);C3D_DepthTest(false,GPU_ALWAYS,GPU_WRITE_COLOR);C3D_AlphaTest(false,GPU_ALWAYS,0);
            C2D_Image image={.tex=&frontend_logo_texture,.subtex=&sub};C2D_DrawImageAt(image,208,6,0,NULL,.7f,.7f);C2D_Flush();
        }
    }
}
#ifdef NFS_STREAMED_WORLD
static StreamedWorldResult prepare_streamed_world(const DriveState *car)
{
    StreamedWorldView view={.up_viewer={camera_up[0],camera_up[1],camera_up[2]},
        .vertical_fov_radians=C3D_AngleFromDegrees(chase.fov),.aspect=C3D_AspectRatioTop,
        .near_world=.15f,.far_world=DRIVE_FAR_WORLD,
        .original_fov_turn=(uint16_t)lroundf(chase.fov*(65536.0f/360.0f)),
        .original_context_flags=world_state.context};
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
    mw_opening_cinema_invalidate_ground(&opening_cinema);
    memcpy(collision_sections,sections,count*sizeof(*sections));collision_section_count=count;
    return STREAMED_WORLD_OK;
}
#endif
static MwUiModel ui_model(Screen screen,unsigned selected,const DriveState *car,
                          float height,bool edge,MwUiPanel panel,u32 held)
{
    MwUiModel ui={.mode=screen==MENU?MW_UI_MENU:screen==MOVIE?MW_UI_MOVIE:screen==DRIVE||screen==NIS?MW_UI_DRIVE:
        screen==GARAGE?MW_UI_GARAGE:screen==DISPLAY?MW_UI_DISPLAY:MW_UI_CONTROLS,.panel=panel,.selected=selected,
        .speed_mps=car->speed,.handbrake=screen==DRIVE && (held&KEY_R),
        .road_status=edge?MW_UI_EDGE_REACHED:MW_UI_ROAD_LOADED,
        .assets=ui_assets,.piss_filter=piss_filter,.fps=measured_fps,.triangles=world_triangles_drawn,.draw_calls=world_draw_calls,
        .gpu_ms=C3D_GetDrawingTime(),.draw_ms=C3D_GetProcessingTime(),.logic_ms=simulation_ms,
        .slip_degrees=atan2f(car->lateral_speed,fmaxf(fabsf(car->speed),.01f))*57.29578f};
#ifdef NFS_STREAMED_WORLD
    (void)height;
    ui.streamed_map=true;ui.exploration=world_state.bin==1;
    if (screen==DRIVE && stream_blocked) ui.road_status=MW_UI_MAP_PAUSED;
    else if (screen==DRIVE && !stream_has_frame) ui.road_status=MW_UI_MAP_LOADING;
#else
    if (screen==DRIVE && !edge && road_edge_ahead(&road,car,height))
        ui.road_status=car->speed<0?MW_UI_EDGE_BEHIND:MW_UI_EDGE_AHEAD;
#endif
    if(screen==MENU)frontend_model(&ui);
    if(screen==MOVIE)ui.movie_muted=cinema.audio.muted_fallback;
    if(screen==DRIVE&&has_near_destination)ui.interaction_prompt=near_destination.kind==MW_DEST_SAFEHOUSE?"UP: ENTER SAFE HOUSE":near_destination.kind==MW_DEST_SHOP?"UP: ENTER PARTS SHOP":near_destination.kind==MW_DEST_CARLOT?"UP: ENTER CAR LOT":"UP: ENTER RACE";
    if(screen==DRIVE&&playable_race.phase==MW_PLAYABLE_COUNTDOWN){
        snprintf(career_status,sizeof(career_status),"READY %lu",(unsigned long)((playable_race.countdown_us+999999)/1000000));ui.interaction_prompt=career_status;
    }else if(screen==DRIVE&&playable_race.phase==MW_PLAYABLE_RUNNING){
        snprintf(career_status,sizeof(career_status),"CHECKPOINT %u/%u  LAP %u/%u",(unsigned)race_session.progress.next,(unsigned)race_session.route.count,race_session.progress.lap,race_session.route.laps);ui.interaction_prompt=career_status;
    }else if(screen==NIS)ui.interaction_prompt=nis_camera_ready?"START: SKIP CINEMATIC":"CINEMATIC BINDING UNAVAILABLE - START: SKIP";
    return ui;
}
static void draw_ui(const MwUiModel *ui,const DriveState *car)
{
    const unsigned char *map=NULL;
    if (ui->mode==MW_UI_DRIVE && ui->panel==MW_UI_NAVIGATION &&
        road_map_render(&navigation,&road,car,map_rgb,152,128)) {
        /* Same north-up projection as road_map_render. Authentic source glyphs
           identify destinations; original unlock availability remains separate. */
        for(uint32_t i=0;i<free_roam.count;i++){
            MwDestination d;if(!mw_free_roam_get(&free_roam,i,&d))continue;
            float x=(car->x-(d.position[0]-road.origin[0]))/navigation.step+76;
            float y=(car->z-(-d.position[1]-road.origin[2]))/navigation.step+64;
            if(x < -16 || y < -16 || x > 168 || y > 144)continue;
            int32_t type=-1;
            if(d.kind==MW_DEST_RACE){MwEventDefinition event;if(mw_event_catalog_find(&event_catalog,d.event,&event))type=event.original_type;}
            (void)mw_destination_icon_blit(&destination_icons,d.kind,type,map_rgb,sizeof(map_rgb),152,128,(int)lroundf(x),(int)lroundf(y));
        }
        (void)road_map_player_overlay(car,map_rgb,152,128);
        map=map_rgb;
    }
    if (mw_ui_render(ui_pixels,sizeof(ui_pixels),ui,map)) ui_pending=true;
#ifdef NFS_CAPTURE_UI
    static bool captured;
    if(!captured&&ui->mode==MW_UI_DRIVE&&ui->road_status==MW_UI_ROAD_LOADED){
        FILE *capture=fopen(ROOT "ui-diagnostic.rgb565","wb");
        if(capture){(void)fwrite(ui_pixels,1,sizeof(ui_pixels),capture);fclose(capture);captured=true;}
    }
#endif
    if(ui->mode!=MW_UI_DRIVE&&ui->mode!=MW_UI_MOVIE&&!frontend_platform.loaded&&frontend_art.data){
        const char *selection=ui->mode==MW_UI_GARAGE?active_car_name:ui->mode==MW_UI_TITLE?"PRESS START":ui->selected<ui->frontend_count?ui->frontend_rows[ui->selected]:"";
        MwFrontendTopModel top={.page=ui->mode==MW_UI_GARAGE?"MY CARS":ui->frontend_title,.alias=mw_alias_selected_name(&aliases),.selection=selection,.detail=ui->frontend_hint};
        if(mw_frontend_top_render(&frontend_art,frontend_pixels,sizeof(frontend_pixels),&top))frontend_pending=true;
    }
}
static void upload_ui(void)
{
    if (!ui_pending&&!frontend_pending) return;
    /* Called outside a frame: never modify the texture while a previous UI
       draw reads it. Both LCD swaps now belong to the GPU completion queue. */
    C3D_FrameSync();
    if(frontend_pending&&frontend_texture_ready&&mw_frontend_top_pack(frontend_texture.data,frontend_texture.size,frontend_pixels,sizeof(frontend_pixels))){C3D_TexFlush(&frontend_texture);frontend_pending=false;}
    if (!ui_pending) return;
    if (!mw_ui_texture_pack(ui_texture.data,ui_texture.size,ui_pixels,sizeof(ui_pixels))) return;
    C3D_TexFlush(&ui_texture);ui_pending=false;
}
static void present_ui(void)
{
    if (!ui_texture_ready||!ui_gpu_ready) return;
    /* Present the cached HUD every frame so both LCD buffers receive the same
       complete image. CPU rasterization and texture uploads remain throttled.
       C2D screen targets include a depth buffer. Never let uninitialized or
       previously written depth mask portions of the complete HUD image. */
    C3D_RenderTargetClear(ui_target,C3D_CLEAR_ALL,0x000000ff,0);
    C2D_Prepare();C2D_SceneBegin(ui_target);
    /* This is one opaque full-screen image, with no depth layering or alpha
       rejection. Do not inherit either test from the car/world passes. */
    C3D_DepthTest(false,GPU_ALWAYS,GPU_WRITE_COLOR);
    C3D_AlphaTest(false,GPU_ALWAYS,0);
    C3D_AlphaBlend(GPU_BLEND_ADD,GPU_BLEND_ADD,GPU_ONE,GPU_ZERO,GPU_ONE,GPU_ZERO);
    C2D_Image image={.tex=&ui_texture,.subtex=&ui_subtexture};
    C2D_DrawImageAt(image,0,0,0,NULL,1,1);C2D_Flush();
}
static void reset_player_camera(const DriveState *car,float height)
{
    (void)chase_reset(&chase,car,height);uint32_t ecar=0x4e085fb3;
    MwVehicleSpec spec;if(mw_vehicle_catalog_find_id(&vehicle_catalog,active_car_id,&spec))ecar=spec.ecar_key;
    (void)chase_bind_source(&chase,&camera_asset,ecar,3,0);
}
static bool save_career_state(const MwCareer *state)
{
    if(career_save_blocked||!state||!state->alias_id)return false;
    unsigned char data[MW_CAREER_SAVE_BYTES];
    if(!mw_career_save(state,&career_pack,data,sizeof(data)))return false;
    char path[160],pending[160],backup[160];
    snprintf(path,sizeof(path),ROOT "career-%08lx.ncs",(unsigned long)state->alias_id);
    snprintf(pending,sizeof(pending),ROOT "career-%08lx.pending",(unsigned long)state->alias_id);
    snprintf(backup,sizeof(backup),ROOT "career-%08lx.bak",(unsigned long)state->alias_id);
    FILE *f=fopen(pending,"wb");if(!f)return false;
    bool ok=fwrite(data,1,sizeof(data),f)==sizeof(data);if(fflush(f))ok=false;if(fclose(f))ok=false;if(!ok)return false;
    struct stat st;bool previous=!stat(path,&st);
    if(previous&&rename(path,backup))return false;
    if(rename(pending,path)){if(previous)(void)rename(backup,path);return false;}
    return true;
}
static bool save_career(void){return save_career_state(&career);}
static bool load_career(void)
{
    memset(&career,0,sizeof(career));career_save_blocked=false;
    if(!aliases.selected)return false;
    char path[160];snprintf(path,sizeof(path),ROOT "career-%08lx.ncs",(unsigned long)aliases.selected);
    struct stat st;if(stat(path,&st)){if(errno!=ENOENT)career_save_blocked=true;return false;}
    size_t bytes;void *raw=read_file(path,&bytes);
    bool ok=raw&&mw_career_load(&career,&career_pack,aliases.selected,raw,bytes);free(raw);
    if(!ok){
        career_save_blocked=true;frontend_notice="CAREER SAVE COULD NOT BE READ";
        snprintf(path,sizeof(path),ROOT "career-%08lx.bak",(unsigned long)aliases.selected);
        raw=read_file(path,&bytes);ok=raw&&mw_career_load(&career,&career_pack,aliases.selected,raw,bytes);free(raw);
    }
    return ok;
}
static bool switch_world_snapshot(const char *path,uint32_t event)
{
#ifdef NFS_STREAMED_WORLD
    size_t bytes;unsigned char *raw=read_file(path,&bytes);MwWorldState next;
    if(!raw||!mw_world_state_open(&next,raw,bytes)||next.event!=event||
       !mw_world_state_source_matches(&next,collision_world.source_sha256)||
       memcmp(next.data+96,world_state.data+96,32)){free(raw);return false;}
    world_state=next;free(race_state_bytes);race_state_bytes=raw;
    streamed_world_invalidate_instances(stream_world);stream_has_frame=false;stream_blocked=false;stream_load_announced=false;return true;
#else
    (void)path;(void)event;return false;
#endif
}
static bool restore_exploration(void)
{
#ifdef NFS_STREAMED_WORLD
    if(!mw_world_state_open(&world_state,world_state_bytes,world_state_bytes_size))return false;
    streamed_world_invalidate_instances(stream_world);stream_has_frame=false;stream_blocked=false;stream_load_announced=false;
    free(race_state_bytes);race_state_bytes=NULL;return true;
#else
    return false;
#endif
}
static bool start_native_race(uint32_t event,bool opening,uintptr_t actor)
{
    if(playable_race.phase!=MW_PLAYABLE_EMPTY&&playable_race.phase!=MW_PLAYABLE_CANCELLED&&playable_race.phase!=MW_PLAYABLE_FINISHED)
        (void)mw_playable_race_cancel(&playable_race);
    (void)mw_race_session_cancel(&race_session);memset(&playable_race,0,sizeof(playable_race));
    if(!mw_playable_race_prepare(&playable_race,&race_session,&event_catalog,event,&aliases,actor,1))return false;
    char path[192];const char *base=opening?"intro":race_from_drive&&race_base_bin==15?"career":"exploration";
    snprintf(path,sizeof(path),ROOT "race-state/%s/%08lx.nws",base,(unsigned long)event);
    if(!switch_world_snapshot(path,event)){(void)mw_playable_race_cancel(&playable_race);return false;}
    if(opening){
        float source[3],yaw;
        if(!mw_playable_race_start_pose(&playable_race,source,&yaw)||!begin_opening_actors(event,actor,source)){
            (void)mw_playable_race_cancel(&playable_race);return false;
        }
    }else {C3D_FrameSync();reset_opening_actors();}
    mw_story_audio_stop(&story_audio);mw_story_engine_reset(&story_engine);story_simulation_clock=0;
    frontend_event_key=event;race_spawn_pending=true;race_finish_position=0;return true;
}
static bool place_race_player(DriveState *car,float *height,RoadPose *pose,WheelMotion *motion,bool recover)
{
    float source[3],yaw;
    bool ok=recover?mw_playable_race_recovery_pose(&playable_race,source,&yaw):mw_playable_race_start_pose(&playable_race,source,&yaw);
    if(!ok)return false;
    drive_reset(car,source[0]-road.origin[0],-source[1]-road.origin[2],yaw);*height=source[2]-road.origin[1];
    *pose=(RoadPose){.height=*height,.normal={0,1,0}};wheel_motion_reset(motion);reset_player_camera(car,*height);
    if(recover){(void)mw_playable_race_relocate(&playable_race,(uintptr_t)car,source);(void)mw_opening_actors_relocate(&opening_actors,source);}
    spawn_street_cars(car,*height);return true;
}
static bool finish_career_media(void)
{
    MwCareer next=career;
    if(!mw_career_media_finished(&next,&career_pack)||!save_career_state(&next))return false;
    career=next;career_phase_pending=true;return true;
}
static uint16_t source_heading(float heading)
{
    float turns=fmodf(heading*(65536.f/6.283185307179586f),65536.f);
    if(turns<0)turns+=65536.f;
    return (uint16_t)turns;
}
static void player_source_matrix(const DriveState *car,float height,float matrix[16])
{
    float position[3]={car->x+road.origin[0],-(car->z+road.origin[2]),height+road.origin[1]};
    (void)mw_nis_director_scene_frame(matrix,position,source_heading(car->heading),0);
}
static bool nis_ground(void *context,const float source[3],float *height)
{
    (void)context;
#ifdef NFS_STREAMED_WORLD
    if(!collision_world.ready)return false;
    float native[3]={-source[1],source[2],source[0]};WorldCollisionContact contact;
    if(world_collision_runtime_ground(&collision_world,native,0,&contact)!=1)return false;
    *height=contact.point_native[1];return true;
#else
    (void)source;(void)height;return false;
#endif
}
static bool present_career_phase(Screen *screen,DriveState *car,float *height,RoadPose *pose,WheelMotion *motion)
{
    if(!career_playing||race_results_showing)return true;
    if(!career_phase_pending&&presented_career_phase==career.phase)return true;
    if(career.step<MW_CAREER_STAGES&&loaded_career_step!=career.step){
        MwCareerStage stage;if(!mw_career_stage(&career_pack,career.step,&stage)||
            !select_player_vehicle("BMWM3GTRE46")||!start_native_race(stage.event,true,(uintptr_t)car)||
            !place_race_player(car,height,pose,motion,false))return false;
        race_spawn_pending=false;loaded_career_step=career.step;
    }
    career_phase_pending=false;presented_career_phase=career.phase;
    if(career.phase==MW_CAREER_INTRO_MOVIE||career.phase==MW_CAREER_OUTRO_MOVIE){
        const char *name=mw_career_media(&career,&career_pack);if(!name||!*name)return false;
        for(const char *s=name;*s;s++)if(!((*s>='a'&&*s<='z')||(*s>='0'&&*s<='9')||*s=='_'))return false;
        char path[192];snprintf(path,sizeof(path),ROOT "movies/%s.nvm",name);
        mw_story_audio_stop(&story_audio);mw_cinema_stop(&cinema);
        if(!mw_cinema_start(&cinema,path))return false;
        *screen=MOVIE;return true;
    }
    if(career.phase==MW_CAREER_INTRO_NIS||career.phase==MW_CAREER_OUTRO_NIS){
        const char *name=mw_career_media(&career,&career_pack);
        player_source_matrix(car,*height,nis_player_source);
        float origin[3]={nis_player_source[12],nis_player_source[13],nis_player_source[14]},ground;
        if(nis_ground(NULL,origin,&ground))origin[2]=ground;
        if(!name||!mw_opening_cinema_begin(&opening_cinema,name,nis_player_source,origin,source_heading(car->heading),nis_ground,NULL,NULL,NULL))return false;
        nis_camera_ready=false;*screen=NIS;return true;
    }
    if(career.phase==MW_CAREER_RACING){race_spawn_pending=true;*screen=DRIVE;return true;}
    if(career.phase==MW_CAREER_CAR_CHOICE){
        (void)mw_playable_race_cancel(&playable_race);*screen=MENU;frontend_page=FE_CAR_CHOICE;frontend_selected=0;return true;
    }
    if(career.phase==MW_CAREER_FREE_ROAM){
        MwVehicleSpec spec;if(!mw_vehicle_catalog_find_frontend(&vehicle_catalog,career.owned_car,&spec)||!select_player_vehicle(spec.id))return false;
        (void)mw_playable_race_cancel(&playable_race);
        if(!switch_world_snapshot(ROOT "career-bin15.nws",0))return false;
        *screen=MENU;frontend_page=FE_SAFEHOUSE;frontend_selected=2;return true;
    }
    return false;
}
static bool start_or_resume_career(bool resume)
{
    bool exists=load_career();if(career_save_blocked){frontend_notice="CAREER SAVE IS READ ONLY";return false;}
    if(resume){
        if(!exists){frontend_notice="NO SAVED CAREER FOR THIS ALIAS";return false;}
        if(career.phase==MW_CAREER_RACING&&!mw_career_retry(&career,&career_pack))return false;
    }else{
        if(exists){frontend_notice="LOAD THIS CAREER OR CREATE A NEW ALIAS";return false;}
        if(!mw_career_start(&career,&career_pack,aliases.selected)||!save_career())return false;
    }
    loaded_career_step=UINT32_MAX;career_phase_pending=true;presented_career_phase=MW_CAREER_INACTIVE;
    career_playing=true;race_results_showing=false;return true;
}
static bool race_active(void)
{
    return scripted_opening()||(playable_race.phase!=MW_PLAYABLE_EMPTY&&playable_race.phase!=MW_PLAYABLE_CANCELLED&&playable_race.phase!=MW_PLAYABLE_FINISHED);
}
static bool restore_race_base(void)
{
    if(race_base_bin==15)return switch_world_snapshot(ROOT "career-bin15.nws",0);
    return restore_exploration();
}
static void cancel_race(void)
{
    (void)mw_playable_race_cancel(&playable_race);(void)mw_race_session_cancel(&race_session);
    mw_story_audio_stop(&story_audio);mw_story_engine_reset(&story_engine);
    C3D_FrameSync();reset_opening_actors();
    career_playing=false;career_phase_pending=false;race_results_showing=false;
    (void)restore_race_base();
}
int main(void)
{
    gfxInitDefault();gfxSet3D(false);consoleInit(GFX_BOTTOM,NULL);gfxSetDoubleBuffering(GFX_BOTTOM,false);
    bool ok=initialize();load_aliases();Screen screen=MENU;unsigned selected=0;
    (void)mw_menu_camera_focus(&menu_camera,MW_MENU_CAREER,true);
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
        hidScanInput();u32 down=hidKeysDown(),held=hidKeysHeld();Screen before=screen;bool ui_changed=false,resume_drive=false;
        if (!ok) { if (down&KEY_START) break;gfxFlushBuffers();gfxSwapBuffers();gspWaitForVBlank();continue; }
        float source_player[3]={car.x+road.origin[0],-(car.z+road.origin[2]),height+road.origin[1]};
        bool old_near=has_near_destination;uint32_t old_key=near_destination.key;
        has_near_destination=screen==DRIVE&&mw_free_roam_near(&free_roam,source_player,&near_destination);
        ui_changed=old_near!=has_near_destination||(has_near_destination&&old_key!=near_destination.key);
        if (screen==MENU) {
            bool accept=!!(down&KEY_A);
            if((down&KEY_TOUCH)&&!(down&(KEY_A|KEY_B|KEY_START|KEY_SELECT|KEY_UP|KEY_DOWN|KEY_CPAD_UP|KEY_CPAD_DOWN|KEY_X|KEY_Y))){
                touchPosition touch;hidTouchRead(&touch);
                if(frontend_page==FE_TITLE)accept=true;
                else if(frontend_icons()){
                    MwMenuAction action;MwMenuTouch intent=mw_menu_layout_touch(&menu_layout,touch.px,touch.py,&action);
                    if(intent!=MW_MENU_TOUCH_NONE)frontend_selected=menu_layout.selected;
                    accept=intent==MW_MENU_TOUCH_ACTIVATE;
                }
                else if(touch.px>=12&&touch.px<308&&touch.py>=73&&touch.py<205){
                    unsigned base=frontend_selected>=6?frontend_selected-5:0;
                    unsigned row=base+(touch.py-73)/22;
                    if(row<frontend_rows()){frontend_selected=row;accept=true;}
                }
            }
            unsigned rows=frontend_rows();
            if(rows&&(down&(KEY_UP|KEY_CPAD_UP)))frontend_selected=(frontend_selected+rows-1)%rows;
            if(rows&&(down&(KEY_DOWN|KEY_CPAD_DOWN)))frontend_selected=(frontend_selected+1)%rows;
            if(frontend_icons()&&rows){
                if(down&(KEY_LEFT|KEY_CPAD_LEFT))frontend_selected=(frontend_selected+rows-1)%rows;
                if(down&(KEY_RIGHT|KEY_CPAD_RIGHT))frontend_selected=(frontend_selected+1)%rows;
            }
            if(frontend_page==FE_TITLE&&(accept||(down&KEY_START))){frontend_page=aliases.count?FE_MAIN:FE_ALIASES;frontend_selected=0;}
            else if(frontend_page==FE_MAIN&&(down&KEY_Y)){
                cancel_race();race_base_bin=1;(void)restore_exploration();screen=DRIVE;
            }
            else if(frontend_page==FE_ALIASES&&(down&KEY_X)&&frontend_selected)edit_alias(true);
            else if(frontend_page==FE_ALIASES&&(down&KEY_Y)&&frontend_selected){alias_delete_id=aliases.aliases[frontend_selected-1].id;frontend_page=FE_DELETE;frontend_selected=1;}
            else if(down&KEY_B){
                if(frontend_page==FE_RACE_SETUP){
                    (void)mw_race_session_cancel(&race_session);
                    if(race_from_drive){screen=DRIVE;resume_drive=true;}else frontend_page=FE_QUICK;
                }else if(frontend_page==FE_CAREER)frontend_page=career_back;
                else if(frontend_page==FE_PAUSE){
                    if(playable_race.phase==MW_PLAYABLE_PAUSED)(void)mw_playable_race_resume(&playable_race);
                    screen=DRIVE;resume_drive=true;
                }
                else if(frontend_page==FE_CAR_CHOICE||frontend_page==FE_PURCHASE)frontend_page=FE_CAR_CHOICE;
                else if(frontend_page==FE_SHOP_SECTION)frontend_page=FE_SHOP;
                else if(frontend_page==FE_SHOP||frontend_page==FE_SAFEHOUSE)frontend_page=FE_PAUSE;
                else frontend_page=aliases.count?FE_MAIN:FE_TITLE;
                frontend_selected=0;frontend_notice=NULL;
            }
            else if(accept){
                if(frontend_page==FE_ALIASES){
                    if(!frontend_selected)edit_alias(false);
                    else {MwAliasStore next=aliases;if(mw_alias_select(&next,next.aliases[frontend_selected-1].id)&&save_aliases(&next)){frontend_page=FE_MAIN;frontend_selected=0;}}
                }else if(frontend_page==FE_MAIN){
                    if(frontend_selected==3)screen=GARAGE;
                    else {career_back=FE_MAIN;frontend_page=(FrontendPage[]){FE_CAREER,FE_CHALLENGE,FE_QUICK,FE_MAIN,FE_ALIASES,FE_OPTIONS}[frontend_selected];frontend_selected=0;}
                }else if(frontend_page==FE_QUICK&&quick_event_count){
                    if(mw_race_session_prepare(&race_session,&event_catalog,quick_event_keys[frontend_selected],&aliases,(uintptr_t)&car)){
                        frontend_event_key=quick_event_keys[frontend_selected];race_from_drive=false;
                        frontend_page=FE_RACE_SETUP;frontend_selected=0;frontend_notice=NULL;
                    }else frontend_notice="SELECT AN ALIAS FIRST";
                }else if(frontend_page==FE_RACE_SETUP){
                    if(!frontend_selected){
                        career_playing=false;
                        if(start_native_race(frontend_event_key,false,(uintptr_t)&car)){screen=DRIVE;resume_drive=true;}
                        else frontend_notice="RACE DATA COULD NOT BE LOADED";
                    }else{
                        (void)mw_race_session_cancel(&race_session);
                        if(race_from_drive){screen=DRIVE;resume_drive=true;}else frontend_page=FE_QUICK;frontend_selected=0;
                    }
                }else if(frontend_page==FE_PAUSE){
                    if(frontend_selected==0){
                        if(playable_race.phase==MW_PLAYABLE_PAUSED)(void)mw_playable_race_resume(&playable_race);
                        screen=DRIVE;resume_drive=true;
                    }else if(frontend_selected==1){
                        if(race_active()){cancel_race();frontend_page=FE_MAIN;}
                        else frontend_page=FE_SAFEHOUSE;
                    }else {cancel_race();frontend_page=FE_MAIN;}
                    frontend_selected=0;
                }else if(frontend_page==FE_SAFEHOUSE){
                    if(frontend_selected==0){career_back=FE_SAFEHOUSE;frontend_page=FE_CAREER;}
                    else if(frontend_selected==1)screen=GARAGE;
                    else if(frontend_selected==2){screen=DRIVE;resume_drive=true;}
                    else frontend_page=FE_MAIN;
                    frontend_selected=0;
                }else if(frontend_page==FE_SHOP){
                    if(frontend_selected==3)frontend_page=FE_PAUSE;
                    else {shop_section=shop_categories[frontend_selected];frontend_page=FE_SHOP_SECTION;}
                    frontend_selected=0;
                }else if(frontend_page==FE_CAREER){
                    if(start_or_resume_career(frontend_selected==1)){frontend_notice=NULL;ui_changed=true;}
                }else if(frontend_page==FE_CAR_CHOICE){
                    MwCareerCar choice;MwVehicleSpec spec;
                    if(mw_career_car(&career_pack,frontend_selected,&choice)&&
                       mw_career_select_car(&career,&career_pack,choice.key)&&
                       mw_vehicle_catalog_find_frontend(&vehicle_catalog,choice.key,&spec)&&select_player_vehicle(spec.id)){
                        frontend_page=FE_PURCHASE;frontend_selected=1;
                    }else frontend_notice="CAR DATA COULD NOT BE LOADED";
                }else if(frontend_page==FE_PURCHASE){
                    if(frontend_selected){frontend_page=FE_CAR_CHOICE;frontend_selected=0;}
                    else{
                        MwCareer next=career;
                        if(!mw_career_purchase(&next,&career_pack))frontend_notice="NOT ENOUGH CASH";
                        else if(!save_career_state(&next))frontend_notice="CAREER COULD NOT BE SAVED";
                        else {career=next;career_playing=true;career_phase_pending=true;frontend_notice=NULL;}
                    }
                }else if(frontend_page==FE_RACE_RESULT){
                    if(!frontend_selected){
                        race_results_showing=false;
                        if(career_playing&&race_finish_position==1){
                            MwCareer next=career;
                            if(mw_career_race_result(&next,&career_pack,frontend_event_key,true)&&save_career_state(&next)){
                                career=next;career_phase_pending=true;
                            }else {race_results_showing=true;frontend_notice="CAREER RESULT COULD NOT BE SAVED";}
                        }else if(career_playing){race_results_showing=true;frontend_notice="WIN THIS RACE TO CONTINUE CAREER";}
                        else {(void)restore_race_base();screen=DRIVE;resume_drive=true;}
                    }else if(frontend_selected==1){
                        race_results_showing=false;
                        if(career_playing){
                            (void)mw_career_retry(&career,&career_pack);loaded_career_step=UINT32_MAX;career_phase_pending=true;
                        }else if(start_native_race(frontend_event_key,false,(uintptr_t)&car)){screen=DRIVE;resume_drive=true;}
                    }else {cancel_race();frontend_page=FE_MAIN;frontend_selected=0;}
                }else if(frontend_page==FE_SHOP_SECTION){frontend_page=FE_SHOP;frontend_selected=0;
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
            if(down&(KEY_START|KEY_SELECT)){
                if(playable_race.phase==MW_PLAYABLE_RUNNING||playable_race.phase==MW_PLAYABLE_COUNTDOWN)(void)mw_playable_race_pause(&playable_race);
                screen=MENU;frontend_page=FE_PAUSE;frontend_selected=0;
            }
            else if((down&KEY_UP)&&has_near_destination&&!race_active()){
                screen=MENU;frontend_selected=0;
                if(near_destination.kind==MW_DEST_SAFEHOUSE)frontend_page=FE_SAFEHOUSE;
                else if(near_destination.kind==MW_DEST_SHOP)frontend_page=FE_SHOP;
                else if(near_destination.kind==MW_DEST_CARLOT){frontend_page=FE_PAUSE;screen=GARAGE;}
                else {
                    frontend_event_key=near_destination.event;race_from_drive=true;
#ifdef NFS_STREAMED_WORLD
                    race_base_bin=world_state.bin;
#endif
                    (void)mw_race_session_prepare(&race_session,&event_catalog,frontend_event_key,&aliases,(uintptr_t)&car);
                    frontend_page=FE_RACE_SETUP;
                }
            }
        } else if(screen==MOVIE){
            int status=mw_cinema_update(&cinema);
            if(status==1||((down&KEY_START)&&cinema.frame!=UINT32_MAX)){
                if(finish_career_media()){mw_cinema_stop(&cinema);screen=MENU;ui_changed=true;}
                else frontend_notice="CAREER COULD NOT BE SAVED";
            }else if(status<0){
                mw_cinema_stop(&cinema);career_playing=false;career_phase_pending=true;
                screen=MENU;frontend_page=FE_CAREER;frontend_selected=1;frontend_notice="MOVIE COULD NOT BE PLAYED";
            }
        }else if(screen==NIS){
            if((down&KEY_START)&&finish_career_media()){screen=MENU;ui_changed=true;}
        }else if (down&(KEY_B|KEY_START) || (screen==CONTROLS && (down&KEY_A))) screen=MENU;
        /* A controller-driven screen transition takes precedence over touch. */
        if (before!=MENU && (down&KEY_TOUCH) && screen==before && !(down&(KEY_A|KEY_B|KEY_START|KEY_SELECT))) {
            touchPosition touch;hidTouchRead(&touch);
            MwUiModel ui=ui_model(screen,selected,&car,height,edge,panel,held);
            MwUiAction action=mw_ui_touch(&ui,touch.px,touch.py);
            switch (action) {
            case MW_UI_OPEN_MENU:screen=MENU;if(before==DRIVE){frontend_page=FE_PAUSE;frontend_selected=0;}break;
            case MW_UI_SELECT_DRIVE:selected=0;screen=DRIVE;break;
            case MW_UI_SELECT_GARAGE:selected=1;screen=GARAGE;break;
            case MW_UI_SELECT_CONTROLS:selected=2;screen=CONTROLS;break;
            case MW_UI_SELECT_DISPLAY:selected=3;screen=DISPLAY;break;
            case MW_UI_TOGGLE_PISS_FILTER:break;
            case MW_UI_QUIT:selected=4;screen=QUIT;break;
            case MW_UI_TOGGLE_HELP:panel=panel==MW_UI_HELP?MW_UI_NAVIGATION:MW_UI_HELP;break;
            case MW_UI_TOGGLE_DIAGNOSTICS:panel=panel==MW_UI_DIAGNOSTICS?MW_UI_NAVIGATION:MW_UI_DIAGNOSTICS;break;
            default:break;
            }
            ui_changed=ui_changed || action!=MW_UI_NONE;
        }
        if (screen==QUIT) break;
        if(!present_career_phase(&screen,&car,&height,&pose,&motion)){
            career_playing=false;screen=MENU;frontend_page=FE_CAREER;frontend_selected=1;
            frontend_notice="CAREER ASSET COULD NOT BE LOADED";ui_changed=true;
        }
        if (screen==DRIVE && ((before!=DRIVE&&!resume_drive&&!race_active()) || (down&KEY_X))) {
#ifdef NFS_STREAMED_WORLD
            stream_has_frame=false;stream_blocked=false;stream_load_announced=false;
#endif
            drive_reset(&car,road.spawn[0],road.spawn[2],road.heading);height=road.spawn[1];edge=false;
#ifdef NFS_DESTINATION_PROBE_KEY
            /* Emulator admission probe only: start at an actual original
               destination center. Never enabled in the packaged application. */
            for(uint32_t i=0;i<free_roam.count;i++){
                MwDestination d;if(!mw_free_roam_get(&free_roam,i,&d)||d.key!=NFS_DESTINATION_PROBE_KEY)continue;
                drive_reset(&car,d.position[0]-road.origin[0],-d.position[1]-road.origin[2],road.heading);
                height=d.position[2]-road.origin[1];break;
            }
#endif
            wheel_motion_reset(&motion);
            pose=(RoadPose){.height=height,.normal={0,1,0}};
            (void)road_pose_sample(&road,&wheel_rig,&car,height,&pose);
            reset_player_camera(&car,height);
            spawn_street_cars(&car,height);
        }
        if(race_spawn_pending){
            if(!place_race_player(&car,&height,&pose,&motion,false)){
                screen=MENU;frontend_page=FE_CAREER;frontend_notice="RACE START COULD NOT BE PLACED";
            }
            race_spawn_pending=false;ui_changed=true;
        }else if(screen==DRIVE&&(down&KEY_X)&&race_active()){
            (void)place_race_player(&car,&height,&pose,&motion,true);
        }
        if(!refresh_frontend_platform(screen))frontend_notice="GARAGE SCENE COULD NOT BE LOADED";
        u64 now=osGetTime();float dt=(now-previous)*.001f;previous=now;if (dt>.1f) dt=.1f;
        if(screen==NIS){
            MwNisCamera camera;
            /* Native registry order is explicit: controlled player, then the
               admitted racers. It is not a claim about every source list. */
#ifdef NFS_STREAMED_WORLD
            bool stepped=!stream_has_frame||mw_opening_cinema_step(&opening_cinema,dt,NULL,NULL);
#else
            bool stepped=mw_opening_cinema_step(&opening_cinema,dt,NULL,NULL);
#endif
            if(opening_cinema.actors[0].present)memcpy(nis_player_source,opening_cinema.actors[0].source_world,sizeof(nis_player_source));
            nis_camera_ready=stepped&&mw_opening_cinema_camera(&opening_cinema,nis_player_source,&camera);
            if(nis_camera_ready){
                for(unsigned a=0;a<3;a++){
                    float eye=a==0?camera.eye[0]:a==1?camera.eye[2]:-camera.eye[1];
                    float at=a==0?camera.target[0]:a==1?camera.target[2]:-camera.target[1];
                    chase.eye[a]=eye-road.origin[a];chase.target[a]=at-road.origin[a];
                }
                chase.fov=camera.fov_turn*(360.f/65536);
                float f[3],length=0;for(unsigned a=0;a<3;a++){f[a]=chase.target[a]-chase.eye[a];length+=f[a]*f[a];}
                length=sqrtf(length);if(length>0){
                    for(unsigned a=0;a<3;a++)f[a]/=length;
                    float roll=camera.roll_source*6.283185307179586f,co=cosf(roll),si=sinf(roll);
                    camera_up[0]=-f[2]*si+f[0]*f[1]*(1-co);
                    camera_up[1]=co+f[1]*f[1]*(1-co);
                    camera_up[2]=f[0]*si+f[2]*f[1]*(1-co);
                }
                if(opening_cinema.finished&&finish_career_media()){screen=MENU;ui_changed=true;}
            }
        }else {camera_up[0]=camera_up[2]=0;camera_up[1]=1;}
#ifdef NFS_STREAMED_WORLD
        DriveState saved_car=car;float saved_height=height;
        WheelMotion saved_motion=motion;RoadPose saved_pose=pose;ChaseCamera saved_chase=chase;
#endif
        bool advance_drive=screen==DRIVE && before==DRIVE && dt>0 && !(down&KEY_X)&&
            (!race_active()||playable_race.phase==MW_PLAYABLE_RUNNING||(scripted_opening()&&playable_race.phase==MW_PLAYABLE_FINISHED));
#ifdef NFS_STREAMED_WORLD
        advance_drive=advance_drive && !stream_blocked && stream_has_frame;
#endif
        if (advance_drive) {
            circlePosition pad;hidCircleRead(&pad);
            float steering=abs(pad.dx)>15?pad.dx/156.0f:0;
            steering+=!!(held&KEY_RIGHT)-!!(held&KEY_LEFT);
            DriveInput input={.throttle=!!(held&KEY_A)-!!(held&KEY_Y),.brake=!!(held&KEY_B),.steering=-steering,.handbrake=held&KEY_R};
            if(story_engine.blown)input.throttle=0;
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
        if(advance_drive)update_street_cars(&car,dt);
#ifdef NFS_STREAMED_WORLD
        if(advance_drive&&opening_actors.running){
            StreamedDriveSurface surface={&collision_world,&road};
            float source[3]={car.x+road.origin[0],-(car.z+road.origin[2]),height+road.origin[1]};
            DriveState old_racers[MW_RACE_AI_ACTORS],old_police[MW_PURSUIT_COPS];
            for(unsigned i=0;i<opening_actors.race.count;i++)old_racers[i]=opening_actors.race.actors[i].motion;
            for(unsigned i=0;i<MW_PURSUIT_COPS;i++)old_police[i]=opening_actors.pursuit.actors[i].motion;
            MwOpeningActorsWork work={0};
            (void)mw_opening_actors_pause(&opening_actors,false);
            (void)mw_opening_actors_update(&opening_actors,&car,height,source,1,(uint64_t)lroundf(dt*1000000),opening_actor_drive,&surface,&work);
            for(unsigned i=0;i<opening_actors.race.count;i++)(void)wheel_motion_update(&opponent_visuals[i].rig,&opponent_visuals[i].wheels,old_racers+i,&opening_actors.race.actors[i].motion);
            for(unsigned i=0;i<MW_PURSUIT_COPS;i++)if(opening_actors.pursuit.actors[i].active)(void)wheel_motion_update(&police_visual.rig,police_wheels+i,old_police+i,&opening_actors.pursuit.actors[i].motion);
        }
#endif
        mw_story_audio_pause(&story_audio,screen!=DRIVE);
        if(story_audio.active&&screen==DRIVE){
            if(!mw_story_audio_update(&story_audio)){frontend_notice="PHONE AUDIO COULD NOT BE PLAYED";mw_story_audio_stop(&story_audio);}
            else if(mw_story_audio_issued_playback(&story_audio)) (void)mw_career_call_started(&career);
            if(mw_story_audio_finished(&story_audio))mw_story_audio_stop(&story_audio);
        }
        if(advance_drive){
            story_simulation_clock+=dt;
            if(mw_story_engine_tick(&story_engine,story_simulation_clock))(void)mw_career_engine_blown(&career);
        }
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
        MwMenuAction camera_action=screen==GARAGE?MW_MENU_MY_CARS:frontend_page==FE_RACE_SETUP||frontend_page==FE_QUICK?MW_MENU_QUICK_RACE:frontend_page==FE_CAREER||frontend_page==FE_SAFEHOUSE?MW_MENU_CAREER:MW_MENU_OPTIONS;
        if(screen==MENU&&frontend_icons())camera_action=menu_layout.actions[menu_layout.selected];
        (void)mw_menu_camera_focus(&menu_camera,camera_action,false);
        (void)mw_menu_camera_step(&menu_camera,dt);
#ifdef NFS_STREAMED_WORLD_PROBE
        if (screen==DRIVE) {
            const float eye[3]={360,180,-2410};
            for (unsigned a=0;a<3;++a) { chase.eye[a]=eye[a]-road.origin[a];chase.target[a]=chase.eye[a]; }
            chase.target[2]+=10;chase.fov=57.2957795f;
        }
#endif
#ifdef NFS_STREAMED_WORLD
        if ((screen==DRIVE||screen==NIS) && !stream_blocked) {
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
        if(screen==DRIVE&&playable_race.phase==MW_PLAYABLE_LOADING){
#ifdef NFS_STREAMED_WORLD
            bool admitted=stream_has_frame&&collision_world.ready&&world_state.event==frontend_event_key;
            if(admitted&&career_playing){
                for(unsigned i=0;i<opening_actors.race.count;i++)(void)mw_opening_actors_admit_racer(&opening_actors,i,opponent_visuals[i].mesh.loaded!=0);
                (void)mw_opening_actors_admit_police(&opening_actors,!opening_actors.pursuit.has_event||police_visual.mesh.loaded!=0);
            }
            if(admitted&&mw_playable_race_admit(&playable_race,true,true,true)){
                float p[3]={car.x+road.origin[0],-(car.z+road.origin[2]),height+road.origin[1]};
                /* Explicit native countdown presentation policy. Original race
                   intro/script timing remains owned by the career flow. */
                (void)mw_playable_race_countdown(&playable_race,3000000,p);ui_changed=true;
            }
#endif
        }
        if(screen==DRIVE&&(playable_race.phase==MW_PLAYABLE_RUNNING||playable_race.phase==MW_PLAYABLE_COUNTDOWN)){
            float p[3]={car.x+road.origin[0],-(car.z+road.origin[2]),height+road.origin[1]};MwPlayableRaceUpdate update={0};
            if(mw_playable_race_update(&playable_race,(uintptr_t)&car,p,(uint64_t)lroundf(dt*1000000),&update)&&update.finished&&!scripted_opening()){
                race_finish_position=0;
                if(career_playing)(void)mw_opening_actors_rank(&opening_actors,&race_session.progress,p,&race_finish_position);
                race_results_showing=true;screen=MENU;frontend_page=FE_RACE_RESULT;frontend_selected=0;ui_changed=true;
            }
            if(update.started&&career_playing&&!mw_opening_actors_start(&opening_actors)){
                frontend_notice="RACE ACTORS COULD NOT BE ADMITTED";stream_blocked=true;
            }
        }
        if(screen==DRIVE&&career_playing&&career.phase==MW_CAREER_RACING&&advance_drive){
            float p[3]={car.x+road.origin[0],-(car.z+road.origin[2]),height+road.origin[1]};
            {
                MwCareerStage stage;MwCareerTrigger trigger;
                if(mw_career_stage(&career_pack,career.step,&stage)&&stage.trigger&&
                   mw_career_trigger_get(&career_pack,stage.trigger,&trigger)){
                    MwEventNode node={.key=trigger.key,.present=trigger.present,.rotation=trigger.rotation,.radius=trigger.radius};
                    memcpy(node.position,trigger.position,sizeof(node.position));memcpy(node.dimensions,trigger.dimensions,sizeof(node.dimensions));
                    double entry;bool entered=trigger.present&16u?
                        mw_playable_race_width_sweep(&node,trigger.width,source_player,p,1,&entry):mw_playable_race_sweep(&node,source_player,p,1,&entry);
                    if(entered&&mw_career_trigger_enter(&career,&career_pack,trigger.key)){
                        if(career.flags&MW_CAREER_CALL_REQUEST){
                            if(!mw_story_audio_start(&story_audio,ROOT "speech/cellcall10.nvs",10))frontend_notice="PHONE AUDIO COULD NOT BE OPENED";
                        }
                        if(career.flags&MW_CAREER_SABOTAGE)(void)mw_story_engine_sabotage(&story_engine,story_simulation_clock,5);
                        ui_changed=true;
                    }
                }
                MwCareerPhase phase=career.phase;
                if(mw_career_tick(&career,&career_pack,(uint64_t)lroundf(dt*1000000))&&career.phase!=phase){
                    (void)save_career();(void)mw_playable_race_cancel(&playable_race);
                    race_results_showing=false;career_phase_pending=true;screen=MENU;ui_changed=true;
                }
            }
        }
        if (before!=screen || ui_changed || (screen==MENU && down) ||
            ((screen==DRIVE||screen==NIS||screen==MOVIE) && (now-last_status>=200 || (down&KEY_X)))) {
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
        if ((screen==DRIVE||screen==NIS) && !stream_has_frame) render_screen=MENU;
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
    free(world_state_bytes);
    mw_scene_pack_close(&scene_pack);
#endif
    if(gpu_ready)C3D_FrameSync();
    mw_story_audio_stop(&story_audio);mw_cinema_stop(&cinema);
    reset_opening_actors();free_mesh(&frontend_platform);free_mesh(&traffic_body);
    free_mesh(&pending_body);free_mesh(&world);free_mesh(&body);
    wheel_rig_free(&traffic_rig);wheel_rig_free(&wheel_rig);
    if(gpu_ready){
        if(ui_texture_ready)C3D_TexDelete(&ui_texture);
        if(frontend_texture_ready)C3D_TexDelete(&frontend_texture);
        if(frontend_logo_ready)C3D_TexDelete(&frontend_logo_texture);
        if(ui_gpu_ready)C2D_Fini();
        C3D_Fini();
    }
    free(opponent_pack_bytes);free(pursuit_pack_bytes);free(career_pack_bytes);
    free(frontend_scene_bytes);free(camera_asset_bytes);mw_opening_cinema_close(&opening_cinema);free(race_state_bytes);
    free(traffic_world_bytes);free(vehicle_catalog_bytes);free(menu_icon_bytes);
    free(destination_icon_bytes);free(free_roam_bytes);free(frontend_art_bytes);free(event_catalog_bytes);
    road_free(&road);road_map_free(&navigation);
    if (program_ready) shaderProgramFree(&program);
    if (world_program_ready) shaderProgramFree(&world_program);
    if (shader) DVLB_Free(shader);
    if (world_shader) DVLB_Free(world_shader);
    mw_ui_assets_free(ui_assets);gfxExit();return 0;
}
