#include "world_collision_runtime.h"
#include <math.h>
#include <string.h>
static uint32_t le32(const unsigned char *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static unsigned be16(const unsigned char *p){return ((unsigned)p[0]<<8)|p[1];}
static uint32_t be32(const unsigned char *p){return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];}
static float bef(const unsigned char *p){uint32_t u=be32(p);float f;memcpy(&f,&u,4);return f;}
static void put16(unsigned char *p,unsigned u){p[0]=(unsigned char)u;p[1]=(unsigned char)(u>>8);}
static unsigned le16(const unsigned char *p){return (unsigned)p[0]|((unsigned)p[1]<<8);}
static int read_at(FILE *f,uint32_t offset,void *out,size_t bytes){return fseek(f,(long)offset,SEEK_SET)==0&&fread(out,1,bytes,f)==bytes;}
static uint32_t crc32_bytes(const unsigned char *p,size_t n){uint32_t crc=~0u;for(size_t i=0;i<n;i++){crc^=p[i];for(unsigned k=0;k<8;k++)crc=(crc>>1)^(0xedb88320u& (0u-(crc&1u)));}return ~crc;}
static int asset_valid(const unsigned char *p,size_t n){
    if(n<16)return 0;
    unsigned nodes=be16(p),mesh=be16(p+2),walls=be16(p+4),wallbytes=be16(p+6),materials=p[9],matbytes=be16(p+10);
    size_t used=16u+mesh+wallbytes+matbytes;
    if(p[8]||wallbytes!=walls*32u||matbytes!=materials*4u||((used+63)&~(size_t)63)!=n||nodes*16u>mesh)return 0;
    for(unsigned i=0;i<nodes;i++){
        const unsigned char *node=p+16+i*16;for(unsigned a=0;a<3;a++)if(!isfinite(bef(node+4*a)))return 0;
        unsigned off=be16(node+14),radius=be16(node+12);
        if(off<nodes*16u||off+24u>mesh)return 0;
        const unsigned char *strip=p+16+off;unsigned count=be16(strip+6),flags=be16(strip+14);
        if(count<3||off+count*8u>mesh||(flags&~3u))return 0;
        for(unsigned j=0;j<count;j++){
            const unsigned char *v=strip+j*8;int x=(int)be16(v),z=(int)be16(v+4);if(x&32768)x-=65536;if(z&32768)z-=65536;
            if(hypotf((float)x,(float)z)/128.0f>(radius+1)/16.0f+.0001f)return 0;
            if(j>=2&&v[6]>=materials)return 0;
        }
    }
    for(unsigned i=0;i<walls;i++){
        const unsigned char *w=p+16+mesh+i*32;
        if(w[12]>=materials)return 0;
        for(unsigned a=0;a<3;a++)if(!isfinite(bef(w+4*a))||!isfinite(bef(w+16+4*a)))return 0;
        float inverse=bef(w+28),length=hypotf(bef(w+16)-bef(w),bef(w+24)-bef(w+8));
        if(!isfinite(inverse)||inverse<=0||length<=0||fabsf(inverse-1.0f/length)>fmaxf(.00001f,inverse*.00001f))return 0;
    }
    return 1;
}
static int payload_valid(unsigned char *p,size_t bytes,const WorldCollisionPackageIndex *package){
    uint32_t instances=package->instances;
    if(bytes<16||memcmp(p,"NWP1",4)||le32(p+4)!=instances||le32(p+8)!=16||instances>(bytes-16)/96||le32(p+12)!=16+instances*96u)return 0;
    uint32_t data=le32(p+12);
    for(uint32_t i=0;i<instances;i++){
        unsigned char *rec=p+16+i*96;const unsigned char *ci=rec+32;uint32_t off=le32(rec),size=le32(rec+4),source_ci=le32(rec+8),source_ca=le32(rec+12);
        uint64_t source_end=(uint64_t)package->source_offset+package->source_bytes;
        if(source_ci<package->source_offset||source_ca<package->source_offset||(uint64_t)source_ci+64>source_end||(uint64_t)source_ca+size>source_end)return 0;
        if(off<data||off>bytes||size>bytes-off||le16(rec+16)||le32(rec+24)||le32(rec+28)||le16(rec+18)!=be16(ci+26))return 0;
        if((be16(ci+18)&3)||bef(ci)!=1||bef(ci+4)!=0||bef(ci+8)!=0||bef(ci+32)!=0||bef(ci+36)!=0||bef(ci+40)!=1)return 0;
        for(unsigned a=0;a<3;a++)if(!isfinite(bef(ci+48+4*a)))return 0;
        const unsigned extent_offsets[3]={12,20,44};for(unsigned a=0;a<3;a++){float e=bef(ci+extent_offsets[a]);if(!isfinite(e)||e<0)return 0;}
        if(!isfinite(bef(ci+60))||!asset_valid(p+off,size)||be32(p+off+12)!=le32(rec+20))return 0;
    }
    /* Apply the actual original 0x802EE544 loader mutations after validation. */
    for(uint32_t i=0;i<instances;i++){
        unsigned char *rec=p+16+i*96,*asset=p+le32(rec);const unsigned char *ci=rec+32;unsigned flags=be16(ci+18);
        if(be16(ci+24)){
            if(!be16(asset))flags|=0xc0;
            unsigned mesh=be16(asset+2),walls=be16(asset+4);for(unsigned j=0;j<walls;j++)asset[16+mesh+j*32+13]|=0xc0;
        }
        put16(rec+16,flags);
    }
    return 1;
}
int world_collision_runtime_open(WorldCollisionRuntime *w,const char *path,void *arena,size_t capacity){
    if(!w||!path||!arena||!capacity)return WORLD_COLLISION_INVALID;
    if(w->file)return WORLD_COLLISION_INVALID;
    memset(w,0,sizeof *w);w->arena=arena;w->arena_capacity=capacity;w->file=fopen(path,"rb");if(!w->file)return WORLD_COLLISION_IO;
    unsigned char h[64];if(!read_at(w->file,0,h,64))goto corrupt;
    uint32_t count=le32(h+8),associations=le32(h+12),table=le32(h+16),at=le32(h+20),data=le32(h+24),bytes=le32(h+28);
    if(memcmp(h,"NWC1",4)||le32(h+4)!=1||count>WORLD_COLLISION_MAX_PACKAGES||associations>WORLD_COLLISION_MAX_ASSOCIATIONS||table!=64||at!=64+count*32u||data!=((at+associations*12u+15u)&~15u)||bytes<data||bytes>0x7fffffffu)goto corrupt;
    if(fseek(w->file,0,SEEK_END)||ftell(w->file)!=(long)bytes)goto corrupt;
    w->file_bytes=bytes;w->package_count=count;w->association_count=associations;memcpy(w->source_sha256,h+32,32);
    uint32_t previous=data;
    for(uint32_t i=0;i<count;i++){
        unsigned char raw[32];if(!read_at(w->file,table+i*32,raw,32))goto corrupt;
        WorldCollisionPackageIndex *p=&w->packages[i];p->id=le32(raw);p->offset=le32(raw+4);p->bytes=le32(raw+8);p->instances=le32(raw+12);p->crc=le32(raw+16);p->source_offset=le32(raw+20);p->source_bytes=le32(raw+24);
        if(p->id>=2700||p->offset!=previous||p->offset>bytes||p->bytes>bytes-p->offset||p->bytes<16||p->instances>(p->bytes-16)/96||p->source_bytes<8||p->source_offset>0xffffffffu-p->source_bytes||le32(raw+28)||(i&&w->packages[i-1].id>=p->id))goto corrupt;
        previous=p->offset+p->bytes;
    }
    if(previous!=bytes)goto corrupt;
    for(uint32_t i=0;i<associations;i++){
        unsigned char raw[12];if(!read_at(w->file,at+i*12,raw,12))goto corrupt;
        uint32_t section=le32(raw),index=le32(raw+4);if(section>65535||index>=count||(i&&section<=w->associations[i-1].section))goto corrupt;
        w->associations[i].section=(uint16_t)section;w->associations[i].index=(uint16_t)index;w->associations[i].source_offset=le32(raw+8);if(w->associations[i].source_offset>0xffffffffu-w->packages[index].source_bytes)goto corrupt;
    }
    return 0;
corrupt:world_collision_runtime_close(w);return WORLD_COLLISION_CORRUPT;
}
void world_collision_runtime_close(WorldCollisionRuntime *w){if(!w)return;if(w->file)fclose(w->file);memset(w,0,sizeof *w);}
static int association(const WorldCollisionRuntime *w,uint16_t id){uint32_t lo=0,hi=w->association_count;while(lo<hi){uint32_t mid=lo+(hi-lo)/2;if(w->associations[mid].section<id)lo=mid+1;else hi=mid;}return lo<w->association_count&&w->associations[lo].section==id?(int)lo:-1;}
static int plan(const WorldCollisionRuntime *w,const uint16_t *ids,size_t count,WorldCollisionLoaded *out,WorldCollisionAdmission *a){
    if(!w||!w->file||(!ids&&count)||!a)return WORLD_COLLISION_INVALID;
    unsigned char seen[WORLD_COLLISION_MAX_PACKAGES]={0};memset(a,0,sizeof *a);
    for(size_t i=0;i<count;i++){
        int found=association(w,ids[i]);if(found<0){a->sections_without_collision++;continue;}unsigned index=w->associations[found].index;if(seen[index])continue;seen[index]=1;
        if(out){out[a->unique_packages].index=(uint16_t)index;out[a->unique_packages].section=ids[i];out[a->unique_packages].source_offset=w->associations[found].source_offset;out[a->unique_packages].arena_offset=(uint32_t)a->required_bytes;}
        int retained=0;if(w->ready)for(uint32_t old=0;old<w->active_count;old++)if(w->active[old].index==index){retained=1;break;}
        if(retained)a->retained_packages++;else a->required_read_bytes+=w->packages[index].bytes;
        a->unique_packages++;a->required_bytes+=w->packages[index].bytes;
    }
    return a->required_bytes>w->arena_capacity?WORLD_COLLISION_BUDGET:0;
}
int world_collision_runtime_admit(const WorldCollisionRuntime *w,const uint16_t *ids,size_t count,WorldCollisionAdmission *a){return plan(w,ids,count,NULL,a);}
int world_collision_runtime_activate(WorldCollisionRuntime *w,const uint16_t *ids,size_t count,WorldCollisionAdmission *a){
    WorldCollisionLoaded next[WORLD_COLLISION_MAX_PACKAGES];WorldCollisionAdmission local;if(!a)a=&local;
    int status=plan(w,ids,count,next,a);if(status)return status;
    int old_for_next[WORLD_COLLISION_MAX_PACKAGES];uint16_t old_order[WORLD_COLLISION_MAX_PACKAGES];uint32_t retained=0;
    for(uint32_t i=0;i<a->unique_packages;i++){
        old_for_next[i]=-1;
        if(w->ready)for(uint32_t j=0;j<w->active_count;j++)if(w->active[j].index==next[i].index){old_for_next[i]=(int)j;old_order[retained++]=(uint16_t)j;break;}
    }
    /* Compact retained source blocks in increasing old physical offset. Every
     * destination is <= its old offset, so memmove cannot destroy a later block.
     * Query traversal still follows the caller's exact new logical section order.
     */
    for(uint32_t i=1;i<retained;i++){uint16_t item=old_order[i];uint32_t j=i;while(j&&w->active[old_order[j-1]].arena_offset>w->active[item].arena_offset){old_order[j]=old_order[j-1];j--;}old_order[j]=item;}
    w->ready=0;w->active_count=0;w->arena_used=0;size_t used=0;
    for(uint32_t i=0;i<retained;i++){
        const WorldCollisionLoaded *old=&w->active[old_order[i]];size_t bytes=w->packages[old->index].bytes;
        memmove(w->arena+used,w->arena+old->arena_offset,bytes);
        for(uint32_t j=0;j<a->unique_packages;j++)if(old_for_next[j]==(int)old_order[i]){next[j].arena_offset=(uint32_t)used;break;}
        used+=bytes;
    }
    for(uint32_t i=0;i<a->unique_packages;i++)if(old_for_next[i]<0){
        const WorldCollisionPackageIndex *p=&w->packages[next[i].index];unsigned char *target=w->arena+used;next[i].arena_offset=(uint32_t)used;
        if(!read_at(w->file,p->offset,target,p->bytes))return WORLD_COLLISION_IO;
        if(crc32_bytes(target,p->bytes)!=p->crc||!payload_valid(target,p->bytes,p))return WORLD_COLLISION_CORRUPT;
        used+=p->bytes;
    }
    memcpy(w->active,next,a->unique_packages*sizeof *next);w->active_count=a->unique_packages;w->arena_used=a->required_bytes;w->ready=1;return 0;
}
static int point_valid(const float p[3]){return p&&isfinite(p[0])&&isfinite(p[1])&&isfinite(p[2]);}
static uint32_t material(const unsigned char *asset,unsigned index){return be32(asset+16+be16(asset+2)+be16(asset+6)+index*4);}
static void provenance(WorldCollisionContact *c,const WorldCollisionRuntime *w,const WorldCollisionLoaded *loaded,const unsigned char *rec){
    c->section_id=loaded->section;c->collision_id=(uint16_t)w->packages[loaded->index].id;c->asset_index=be16(rec+32+26);c->source_ci_offset=le32(rec+8)-w->packages[loaded->index].source_offset+loaded->source_offset;c->source_asset_offset=le32(rec+12)-w->packages[loaded->index].source_offset+loaded->source_offset;c->instance_flags=(uint16_t)le16(rec+16);
}
int world_collision_runtime_ground(const WorldCollisionRuntime *w,const float point[3],uint32_t mask,WorldCollisionContact *out){
    if(!w||!out||!point_valid(point))return WORLD_COLLISION_INVALID;
    if(!w->ready)return WORLD_COLLISION_NOT_READY;
    int hit=0;float best=1.0e38f;WorldCollisionContact result;memset(&result,0,sizeof result);
    for(uint32_t p=0;p<w->active_count;p++){
        const WorldCollisionLoaded *loaded=&w->active[p];const unsigned char *payload=w->arena+loaded->arena_offset;uint32_t count=le32(payload+4);
        for(uint32_t i=0;i<count;i++){
            const unsigned char *rec=payload+16+i*96,*ci=rec+32,*asset=payload+le32(rec);if(!be16(asset))continue;
            float local[3],extent[3]={bef(ci+12),bef(ci+20),bef(ci+44)},translation[3];for(unsigned a=0;a<3;a++){translation[a]=bef(ci+48+4*a);local[a]=point[a]+translation[a];}
            WorldCollisionMeshHit candidate;int found=world_collision_mesh_point_below(asset,le32(rec+4),local,extent,mask,&candidate);if(found<0)return WORLD_COLLISION_CORRUPT;
            if(!found||candidate.height_gap>=best)continue;
            best=candidate.height_gap;hit=1;memset(&result,0,sizeof result);provenance(&result,w,loaded,rec);
            result.kind=1;result.height_gap=best;result.material_index=candidate.triangle.material_index;result.primitive_flags=candidate.triangle.attributes;result.node_index=candidate.node_index;result.primitive_index=candidate.triangle.triangle_index;result.material_key=material(asset,result.material_index);
            const unsigned char *node=asset+16+candidate.node_index*16;result.strip_flags=(uint8_t)be16(asset+16+be16(node+14)+14);
            for(unsigned a=0;a<3;a++){result.point_native[a]=(a==1?local[a]-best:local[a])-translation[a];for(unsigned v=0;v<3;v++)result.triangle_native[v][a]=candidate.triangle.vertices[v][a]-translation[a];}
            world_collision_ground_query_normal(candidate.triangle.vertices,result.normal_native);
        }
    }
    if(hit)*out=result;
    return hit;
}
int world_collision_runtime_wall(const WorldCollisionRuntime *w,const float start[3],const float end[3],uint32_t mask,WorldCollisionContact *out){
    if(!w||!out||!point_valid(start)||!point_valid(end))return WORLD_COLLISION_INVALID;
    if(!w->ready)return WORLD_COLLISION_NOT_READY;
    int hit=0;float best=1.0e38f;WorldCollisionContact result;memset(&result,0,sizeof result);
    for(uint32_t p=0;p<w->active_count;p++){
        const WorldCollisionLoaded *loaded=&w->active[p];const unsigned char *payload=w->arena+loaded->arena_offset;uint32_t count=le32(payload+4);
        for(uint32_t i=0;i<count;i++){
            const unsigned char *rec=payload+16+i*96,*ci=rec+32,*asset=payload+le32(rec);if(!be16(asset+4))continue;
            float local_a[3],local_b[3],translation[3];for(unsigned a=0;a<3;a++){translation[a]=bef(ci+48+4*a);local_a[a]=start[a]+translation[a];local_b[a]=end[a]+translation[a];}
            WorldCollisionWallHit candidate;int found=world_collision_wall_bank_segment(asset,le32(rec+4),local_a,local_b,mask,&candidate);if(found<0)return WORLD_COLLISION_CORRUPT;if(!found)continue;
            float dx=candidate.point[0]-local_a[0],dy=candidate.point[1]-local_a[1],dz=candidate.point[2]-local_a[2];float distance=fmaf(dz,dz,dx*dx+dy*dy);if(distance>=best)continue;
            best=distance;hit=1;memset(&result,0,sizeof result);provenance(&result,w,loaded,rec);result.kind=2;result.distance_squared=best;result.primitive_index=candidate.wall_index;result.material_index=candidate.material_index;result.primitive_flags=candidate.flags;result.material_key=material(asset,candidate.material_index);
            const unsigned char *wall=asset+16+be16(asset+2)+candidate.wall_index*32;float a[3],b[3];for(unsigned k=0;k<3;k++){a[k]=bef(wall+k*4)-translation[k];b[k]=bef(wall+16+k*4)-translation[k];result.point_native[k]=candidate.point[k]-translation[k];}
            if(world_collision_wall_contact_normal(start,result.point_native,a,b,bef(wall+28),result.normal_native)<0)return WORLD_COLLISION_CORRUPT;
        }
    }
    if(hit)*out=result;
    return hit;
}
void world_collision_native_to_viewer(const float n[3],const float o[3],float v[3]){float a=n[2]-o[0],b=n[1]-o[1],c=n[0]-o[2];v[0]=a;v[1]=b;v[2]=c;}
void world_collision_viewer_to_native(const float v[3],const float o[3],float n[3]){float a=v[2]+o[2],b=v[1]+o[1],c=v[0]+o[0];n[0]=a;n[1]=b;n[2]=c;}
void world_collision_native_vector_to_viewer(const float n[3],float v[3]){float a=n[2],b=n[1],c=n[0];v[0]=a;v[1]=b;v[2]=c;}
