#include "mw_frontend_scene.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
static void put(unsigned char *p,uint32_t value){for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(value>>(i*8));}
static void checksum(unsigned char *p,size_t n){put(p+12,crc(p+16,n-16));}
static void rejected(MwFrontendScenePack *out,unsigned char *p,size_t bytes){MwFrontendScenePack before=*out;assert(!mw_frontend_scene_open(out,p,bytes));assert(!memcmp(out,&before,sizeof(before)));}
int main(int argc,char **argv){
    assert(argc==2);FILE *f=fopen(argv[1],"rb");assert(f);assert(!fseek(f,0,SEEK_END));long size=ftell(f);assert(size==2240);rewind(f);unsigned char *p=malloc((size_t)size),*bad=malloc((size_t)size);assert(p&&bad&&fread(p,1,(size_t)size,f)==(size_t)size);assert(!fclose(f));
    MwFrontendScenePack pack={0};assert(mw_frontend_scene_open(&pack,p,(size_t)size));
    const char *const names[]={"angle19","angle3","angle4_d","angle99","angle_career_manager","angle_carlot_car_select","angle_carlot_showcase","angle_challengeseries","angle_entry_backroom","angle_entry_car_lot","angle_entry_career_safehouse","angle_entry_customization_shop","angle_entry_main_fe","angle_final_backroom","angle_final_car_lot","angle_final_career_safehouse","angle_final_customization_shop","angle_final_main_fe"};
    MwFrontendSceneCamera camera={0};for(unsigned i=0;i<18;i++){assert(mw_frontend_scene_camera(&pack,names[i],&camera));assert(camera.fov_degrees>1&&camera.fov_degrees<179);for(unsigned a=0;a<3;a++)assert(isfinite(camera.eye[a])&&isfinite(camera.target[a])&&isfinite(camera.up[a]));}
    assert(mw_frontend_scene_camera(&pack,"angle3",&camera));
    assert(camera.collection_key==0x594f7363&&camera.fov_degrees==55);
    assert(camera.eye[0]==0.28518593311309814453f&&camera.eye[1]==-5.4429936408996582031f&&camera.eye[2]==0.73653674125671386719f);
    assert(camera.target[0]==1.2000000476837158203f&&camera.target[1]==-0.30000001192092895508f&&camera.target[2]==0.30000001192092895508f);
    assert(camera.up[0]==-0.12469775974750518799f&&camera.up[1]==0.021498549729585647583f&&camera.up[2]==0.99196320772171020508f);
    MwFrontendSceneCamera before=camera;assert(!mw_frontend_scene_camera(&pack,"Angle3",&camera)&&!memcmp(&before,&camera,sizeof(camera)));assert(!mw_frontend_scene_camera(&pack,"missing",&camera));
    MwFrontendScenePlacement v;const float angles[]={134.412506103515625f,302.85308837890625f,0,134.412506103515625f,0};
    for(unsigned i=1;i<=5;i++){assert(mw_frontend_scene_placement(&pack,i,&v));assert(v.garage_type==i&&v.geometry_z_degrees==angles[i-1]&&v.car_height_bias==-0.025000000372529029846f);assert(v.geometry_position[0]==0&&v.geometry_position[2]==0);assert(v.geometry_position[1]==(i==5?0.07500000298023223877f:0));assert(v.car_rotation_degrees[2]==(i==5?340:304.96978759765625f));}
    MwFrontendScenePlacement old=v;assert(!mw_frontend_scene_placement(&pack,0,&v)&&!memcmp(&old,&v,sizeof(v)));assert(!mw_frontend_scene_placement(&pack,6,&v));
    rejected(&pack,p,(size_t)size-1);
    for(size_t i=0;i<(size_t)size;i++){memcpy(bad,p,(size_t)size);bad[i]^=1;rejected(&pack,bad,(size_t)size);}
    memcpy(bad,p,(size_t)size);bad[40]^=1;checksum(bad,(size_t)size);rejected(&pack,bad,(size_t)size);
    memcpy(bad,p,(size_t)size);put(bad+192+48,0x7fc00000);checksum(bad,(size_t)size);rejected(&pack,bad,(size_t)size);
    memcpy(bad,p,(size_t)size);memcpy(bad+192+96,bad+192,48);checksum(bad,(size_t)size);rejected(&pack,bad,(size_t)size);
    memcpy(bad,p,(size_t)size);put(bad+1920,6);checksum(bad,(size_t)size);rejected(&pack,bad,(size_t)size);
    memcpy(bad,p,(size_t)size);put(bad+1920+4,0x7f800000);checksum(bad,(size_t)size);rejected(&pack,bad,(size_t)size);
    free(bad);free(p);puts("Frontend scene:18source static cameras, exact main-menu pose,5independent placements,2240byte-corruptions and CRC-valid source/NaN/duplicate/placement rejection pass.");return 0;
}
