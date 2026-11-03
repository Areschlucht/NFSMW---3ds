#include "world_collision_query.h"
#include <assert.h>
#include <math.h>
#include <string.h>
static void put16(unsigned char *p,int n){unsigned v=(unsigned)n;p[0]=(unsigned char)(v>>8);p[1]=(unsigned char)v;}
static void vertex(unsigned char *p,int x,int y,int z,int meta){put16(p,x);put16(p+2,y);put16(p+4,z);put16(p+6,meta);}
static void putfloat(unsigned char *p,float value){uint32_t v;memcpy(&v,&value,4);p[0]=(unsigned char)(v>>24);p[1]=(unsigned char)(v>>16);p[2]=(unsigned char)(v>>8);p[3]=(unsigned char)v;}
static void wall(unsigned char *p,float z,unsigned flags){
    putfloat(p,-1);putfloat(p+4,-2);putfloat(p+8,z);p[12]=0;p[13]=(unsigned char)flags;
    putfloat(p+16,1);putfloat(p+20,2);putfloat(p+24,z);putfloat(p+28,.5f);
}
static void test_wall_bank(void){
    unsigned char asset[128]={0};WorldCollisionWallHit out;
    put16(asset+4,2);put16(asset+6,64);asset[9]=1;put16(asset+10,4);
    wall(asset+16,0,2);wall(asset+48,.5f,18);
    float a[3]={0,0,-1},b[3]={0,0,1};
    assert(world_collision_wall_bank_segment(asset,sizeof asset,a,b,0,&out)==1);
    assert(out.wall_index==0&&out.flags==2&&out.material_index==0);
    assert(out.point[0]==0&&out.point[1]==0&&out.point[2]==0);
    assert(world_collision_wall_bank_segment(asset,sizeof asset,b,a,0,&out)==1);
    assert(out.wall_index==1&&out.point[2]==.5f);
    assert(world_collision_wall_bank_segment(asset,sizeof asset,b,a,16,&out)==1);
    assert(out.wall_index==0);
    assert(world_collision_wall_bank_segment(asset,sizeof asset,a,b,2,&out)==0);
    a[1]=b[1]=2;assert(world_collision_wall_bank_segment(asset,sizeof asset,a,b,0,&out)==0);
    a[1]=b[1]=-2;assert(world_collision_wall_bank_segment(asset,sizeof asset,a,b,0,&out)==0);
    a[1]=b[1]=0;a[0]=b[0]=2;assert(world_collision_wall_bank_segment(asset,sizeof asset,a,b,0,&out)==0);
    assert(world_collision_wall_bank_segment(asset,32,a,b,0,&out)==-1);
    a[0]=NAN;assert(world_collision_wall_bank_segment(asset,sizeof asset,a,b,0,&out)==-1);
    float start[3]={0,0,-1},point[3]={0,0,0},wall_a[3]={-1,-2,0},wall_b[3]={1,2,0},normal[3];
    assert(world_collision_wall_contact_normal(start,point,wall_a,wall_b,.5f,normal)==0);
    assert(normal[0]==0&&normal[1]==0&&normal[2]==-1);
    start[2]=1;assert(world_collision_wall_contact_normal(start,point,wall_a,wall_b,.5f,normal)==0);
    assert(normal[2]==1);
    assert(world_collision_wall_contact_normal(start,point,wall_a,wall_b,0,normal)==-1);
}
static void test_mesh_point_below(void){
    unsigned char asset[128]={0};WorldCollisionMeshHit out;
    put16(asset,2);put16(asset+2,80);asset[9]=2;put16(asset+10,8);
    put16(asset+16+12,16);put16(asset+16+14,32);
    putfloat(asset+32+4,.5f);put16(asset+32+12,16);put16(asset+32+14,56);
    vertex(asset+48,0,0,0,3);vertex(asset+56,0,0,128,0);vertex(asset+64,128,0,0,0);
    vertex(asset+72,0,0,0,3);vertex(asset+80,0,0,128,0);vertex(asset+88,128,0,0,0x0110);
    float point[3]={.2f,1,.2f},extent[3]={1,1,1};
    assert(world_collision_mesh_point_below(asset,sizeof asset,point,extent,0,&out)==1);
    assert(out.node_index==1&&out.height_gap==.5f&&out.triangle.material_index==1);
    assert(world_collision_mesh_point_below(asset,sizeof asset,point,extent,16,&out)==1);
    assert(out.node_index==0&&out.height_gap==1);
    point[1]=.5f;assert(world_collision_mesh_point_below(asset,sizeof asset,point,extent,0,&out)==1);
    assert(out.node_index==0&&out.height_gap==.5f);
    point[1]=0;assert(world_collision_mesh_point_below(asset,sizeof asset,point,extent,0,&out)==0);
    point[1]=-1;assert(world_collision_mesh_point_below(asset,sizeof asset,point,extent,0,&out)==0);
    point[0]=2;assert(world_collision_mesh_point_below(asset,sizeof asset,point,extent,0,&out)==0);
    point[0]=.2f;point[1]=1;assert(world_collision_mesh_point_below(asset,32,point,extent,0,&out)==-1);
    put16(asset+30,0);assert(world_collision_mesh_point_below(asset,sizeof asset,point,extent,0,&out)==-1);
}
int main(void){
    test_wall_bank();
    test_mesh_point_below();
    float plane[4];const float flat[3][3]={{0,4,0},{0,4,1},{1,4,0}};
    assert(world_collision_ground_contact_plane(flat,(float[3]){.2f,5,.2f},plane)==0);
    assert(plane[0]==0&&plane[1]==.9999f&&plane[2]==0&&plane[3]==-.9999f);
    assert(world_collision_ground_contact_plane(flat,(float[3]){.2f,3,.2f},plane)==0&&plane[3]==.9999f);
    unsigned char strip[32];WorldCollisionCandidate out;
    float center[3]={10,2,-20},p[3]={10.2f,3,-19.8f};
    vertex(strip,0,0,0,3);vertex(strip+8,0,0,128,0);vertex(strip+16,128,0,0,0x0700);
    assert(world_collision_strip_candidate(strip,24,center,p,0,&out)==1);
    assert(out.material_index==7&&out.attributes==0&&out.triangle_index==0);
    assert(out.vertices[0][0]==10&&out.vertices[1][2]==-19&&out.vertices[2][0]==11);
    put16(strip+14,1);assert(world_collision_strip_candidate(strip,24,center,p,0,&out)==0);
    vertex(strip+8,128,0,0,1);vertex(strip+16,0,0,128,0x0700);
    assert(world_collision_strip_candidate(strip,24,center,p,0,&out)==1);
    assert(world_collision_strip_candidate(strip,24,center,p,1,&out)==0);
    strip[23]=8;assert(world_collision_strip_candidate(strip,24,center,p,0,&out)==0);
    strip[23]=16;assert(world_collision_strip_candidate(strip,24,center,p,16,&out)==0);
    assert(world_collision_strip_candidate(strip,24,center,p,0,&out)==1);
    put16(strip+14,2);p[1]=1;
    assert(world_collision_strip_candidate(strip,24,center,p,0,&out)==0); /* minY==pointY+1 rejected */
    p[1]=1.01f;assert(world_collision_strip_candidate(strip,24,center,p,0,&out)==1);
    vertex(strip,0,0,0,4);vertex(strip+8,0,0,128,0);vertex(strip+16,128,0,0,0x0700);vertex(strip+24,128,0,128,0x0904);
    p[0]=10.8f;p[1]=3;p[2]=-19.2f;
    assert(world_collision_strip_candidate(strip,32,center,p,0,&out)==1);
    assert(out.triangle_index==1&&out.material_index==9&&out.attributes==4);
    assert(world_collision_strip_candidate(strip,32,center,p,4,&out)==0);
    assert(world_collision_strip_candidate(strip,31,center,p,0,&out)==-1);
    assert(world_collision_strip_candidate(NULL,32,center,p,0,&out)==-1);
    put16(strip+14,4);assert(world_collision_strip_candidate(strip,32,center,p,0,&out)==-1);
    put16(strip+14,0);p[0]=NAN;assert(world_collision_strip_candidate(strip,32,center,p,0,&out)==-1);
    return 0;
}
