#include "world_collision_query.h"
#include "mw_gekko_math.h"
#include <math.h>
#include <string.h>
static unsigned be16(const unsigned char *p) { return ((unsigned)p[0]<<8)|p[1]; }
static int signed16(const unsigned char *p) {
    unsigned u=be16(p); return u&32768 ? (int)u-65536 : (int)u;
}
static void vertex(const unsigned char *p, const float center[3], float out[3]) {
    for (unsigned a=0;a<3;a++) out[a]=center[a]+signed16(p+2*a)*(1.0f/128.0f);
}
static float edge(const float a[3],const float b[3],const float p[3]) {
    return fmaf(a[0]-b[0],p[2]-b[2],-(p[0]-b[0])*(a[2]-b[2]));
}
int world_collision_strip_candidate(const unsigned char *strip,size_t bytes,
    const float center[3],const float point[3],uint32_t mask,WorldCollisionCandidate *out) {
    if(!strip||!center||!point||!out||bytes<24)return -1;
    unsigned count=be16(strip+6),flags=be16(strip+14);
    if(count<3||count>bytes/8||(flags&~3u))return -1;
    for(unsigned a=0;a<3;a++)if(!isfinite(center[a])||!isfinite(point[a]))return -1;
    if(mask&flags)return 0;
    float v[3][3];vertex(strip,center,v[0]);vertex(strip+8,center,v[1]);
    for(unsigned i=0;i<count-2;i++) {
        const unsigned char *next=strip+(i+2)*8;vertex(next,center,v[2]);
        unsigned attr=next[7];
        if(!(attr&8)&&!(attr&mask)) {
            float e0=edge(v[0],v[1],point),e1=edge(v[1],v[2],point),e2=edge(v[2],v[0],point);
            int inside;
            if(flags&2) {
                inside=e0<=0 ? e1<=0&&e2<=0 : e1>=0&&e2>=0;
                float low=fminf(v[0][1],fminf(v[1][1],v[2][1]));
                inside=inside&&(low<point[1]+1.0f);
            } else if((flags^i)&1) inside=e0<=0&&e1<=0&&e2<=0;
            else inside=e0>=0&&e1>=0&&e2>=0;
            if(inside) {
                for(unsigned j=0;j<3;j++)for(unsigned a=0;a<3;a++)out->vertices[j][a]=v[j][a];
                out->material_index=next[6];out->attributes=(uint8_t)attr;out->triangle_index=(uint16_t)i;
                return 1;
            }
        }
        for(unsigned a=0;a<3;a++){v[0][a]=v[1][a];v[1][a]=v[2][a];}
    }
    return 0;
}

/* Independent original-function reconstruction; no original code is bundled. */
static float befloat(const unsigned char *p) {
    uint32_t bits=((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];
    float value;memcpy(&value,&bits,sizeof value);return value;
}
static int segment_xz(const float a[3],const float b[3],const float c[3],const float d[3],float out[3]) {
    float dz=b[2]-a[2],dx=b[0]-a[0],wx=d[0]-c[0],wz=d[2]-c[2];
    float determinant=fmaf(wz,dx,-wx*dz);
    if(determinant==0)return 0;
    float rx=a[0]-c[0],rz=a[2]-c[2];
    float numerator=fmaf(wx,rz,-wz*rx);
    const float epsilon=0.0001f;
    if(!((numerator>=-epsilon&&numerator<=determinant)||(numerator<=epsilon&&numerator>=determinant)))return 0;
    float wall_numerator=fmaf(dx,rz,-dz*rx);
    if(!((wall_numerator>=-epsilon&&wall_numerator<=determinant)||(wall_numerator<=epsilon&&wall_numerator>=determinant)))return 0;
    float t=numerator/determinant;
    out[0]=fmaf(t,dx,a[0]);out[2]=fmaf(t,dz,a[2]);out[1]=fmaf(t,b[1]-a[1],a[1]);
    return 1;
}
int world_collision_wall_bank_segment(const unsigned char *asset,size_t bytes,
    const float a[3],const float b[3],uint32_t mask,WorldCollisionWallHit *out) {
    if(!asset||!a||!b||!out||bytes<16)return -1;
    unsigned mesh_bytes=be16(asset+2),count=be16(asset+4),wall_bytes=be16(asset+6);
    unsigned material_count=asset[9],material_bytes=be16(asset+10);
    size_t used=16u+mesh_bytes+wall_bytes+material_bytes;
    if(wall_bytes!=count*32u||material_bytes!=material_count*4u||used>bytes)return -1;
    for(unsigned k=0;k<3;k++)if(!isfinite(a[k])||!isfinite(b[k]))return -1;
    int hit=0;float closest=1.0e38f;
    for(unsigned i=0;i<count;i++) {
        const unsigned char *wall=asset+16+mesh_bytes+i*32;
        if(wall[12]>=material_count)return -1;
        float c[3],d[3];for(unsigned k=0;k<3;k++) {
            c[k]=befloat(wall+k*4);d[k]=befloat(wall+16+k*4);
            if(!isfinite(c[k])||!isfinite(d[k]))return -1;
        }
        if(mask&wall[13])continue;
        float point[3];if(!segment_xz(a,b,c,d,point))continue;
        if(point[1]<=fminf(c[1],d[1])||point[1]>=fmaxf(c[1],d[1]))continue;
        float dx=point[0]-a[0],dy=point[1]-a[1],dz=point[2]-a[2];
        float distance=fmaf(dz,dz,dx*dx+dy*dy);
        if(distance<closest) {
            closest=distance;hit=1;for(unsigned k=0;k<3;k++)out->point[k]=point[k];
            out->wall_index=(uint16_t)i;out->material_index=wall[12];out->flags=wall[13];
        }
    }
    return hit;
}

int world_collision_mesh_point_below(const unsigned char *asset,size_t bytes,
    const float point[3],const float extents[3],uint32_t mask,WorldCollisionMeshHit *out) {
    if(!asset||!point||!extents||!out||bytes<16)return -1;
    unsigned nodes=be16(asset),mesh_bytes=be16(asset+2),wall_bytes=be16(asset+6);
    unsigned material_count=asset[9],material_bytes=be16(asset+10);
    if(nodes*16u>mesh_bytes||16u+mesh_bytes+wall_bytes+material_bytes>bytes||material_bytes!=material_count*4u)return -1;
    for(unsigned a=0;a<3;a++)if(!isfinite(point[a])||!isfinite(extents[a])||extents[a]<0)return -1;
    if(fabsf(point[0])>extents[0]||fabsf(point[2])>extents[2])return 0;
    int hit=0;float best=1.0e38f;
    for(unsigned i=0;i<nodes;i++) {
        const unsigned char *node=asset+16+i*16;
        float center[3];for(unsigned a=0;a<3;a++){center[a]=befloat(node+a*4);if(!isfinite(center[a]))return -1;}
        unsigned relative=be16(node+14);
        if(relative<nodes*16u||relative+24u>mesh_bytes)return -1;
        const unsigned char *strip=asset+16+relative;
        unsigned count=be16(strip+6);if(count<3||relative+count*8u>mesh_bytes)return -1;
        float dx=center[0]-point[0],dz=center[2]-point[2],radius=be16(node+12)*(1.0f/16.0f);
        if(fmaf(dx,dx,dz*dz)>=radius*radius)continue;
        WorldCollisionCandidate candidate;
        int found=world_collision_strip_candidate(strip,count*8u,center,point,mask,&candidate);
        if(found<0)return -1;
        if(!found)continue;
        if(candidate.material_index>=material_count)return -1;
        float (*v)[3]=candidate.vertices,normal[3];
        if(world_collision_ground_query_normal(candidate.vertices,normal)<0)return -1;
        float height=v[0][1];
        if(normal[1]!=0){float numerator=fmaf(normal[0],point[0]-v[0][0],normal[2]*(point[2]-v[0][2]));height-=numerator/normal[1];}
        float gap=point[1]-height,low=fminf(v[0][1],fminf(v[1][1],v[2][1]));
        if(low-0.5f<point[1]&&gap>0&&gap<best){best=gap;hit=1;out->triangle=candidate;out->height_gap=gap;out->node_index=(uint16_t)i;}
    }
    return hit;
}

int world_collision_wall_contact_normal(const float start[3],const float point[3],
    const float a[3],const float b[3],float inverse,float normal[3]) {
    if(!start||!point||!a||!b||!normal||!isfinite(inverse)||inverse<=0)return -1;
    for(unsigned k=0;k<3;k++)if(!isfinite(start[k])||!isfinite(point[k])||!isfinite(a[k])||!isfinite(b[k]))return -1;
    float nx=(b[2]-a[2])*inverse,nz=(a[0]-b[0])*inverse;
    float dx=start[0]-point[0],dz=start[2]-point[2];
    if(fmaf(nx,dx,nz*dz)<0){nx=-nx;nz=-nz;}
    normal[0]=nx;normal[1]=0;normal[2]=nz;
    return 0;
}

int world_collision_ground_query_normal(const float v[3][3],float normal[3]) {
    if(!v||!normal)return -1;
    for(unsigned i=0;i<3;i++)for(unsigned a=0;a<3;a++)if(!isfinite(v[i][a]))return -1;
    float u[3],w[3];
    for(unsigned a=0;a<3;a++){u[a]=v[1][a]-v[0][a];w[a]=v[0][a]-v[2][a];}
    float values[3]={fmaf(u[1],w[2],-u[2]*w[1]),-fmaf(u[0],w[2],-u[2]*w[0]),-fmaf(u[1],w[0],-u[0]*w[1])};
    if(values[0]==0&&values[1]==0&&values[2]==0){values[0]=0;values[1]=1;values[2]=0;}
    else {
        float squared=fmaf(values[2],values[2],fmaf(values[0],values[0],values[1]*values[1]));
        float length=mw_gekko_sqrt_newton2(squared);
        if(length>0){float inverse=1.0f/length;for(unsigned a=0;a<3;a++)values[a]*=inverse;}
    }
    if(values[1]<0)for(unsigned a=0;a<3;a++)values[a]=-values[a];
    if(values[1]>=0.9999f)values[1]=0.9999f;
    for(unsigned a=0;a<3;a++)normal[a]=values[a];
    return 0;
}

int world_collision_ground_contact_plane(const float triangle[3][3],const float query[3],float plane[4]) {
    if(!query||!plane||!isfinite(query[0])||!isfinite(query[1])||!isfinite(query[2]))return -1;
    if(world_collision_ground_query_normal(triangle,plane)<0)return -1;
    float dx=triangle[0][0]-query[0],dy=triangle[0][1]-query[1],dz=triangle[0][2]-query[2];
    plane[3]=fmaf(dz,plane[2],fmaf(dx,plane[0],dy*plane[1]));
    return 0;
}
