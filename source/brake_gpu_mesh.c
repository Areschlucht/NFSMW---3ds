#include "brake_gpu_mesh.h"
#include <math.h>
#include <string.h>

size_t brake_gpu_mesh(const BrakeMesh *mesh, bool wireframe, BrakeGpuVertex *out, size_t capacity)
{
    if (!mesh || !out || !mesh->vertex_count || mesh->vertex_count>BRAKE_VERTICES ||
        !mesh->face_count || mesh->face_count>BRAKE_MAX_FACES) return 0;
    size_t count=mesh->face_count*(wireframe?18:3);
    if (capacity<count) return 0;
    float low[3]={INFINITY,INFINITY,INFINITY},high[3]={-INFINITY,-INFINITY,-INFINITY};
    for (size_t i=0;i<mesh->vertex_count;++i)
        for (size_t axis=0;axis<3;++axis) {
            float v=mesh->positions[i][axis];
            if (!isfinite(v)) return 0;
            if (v<low[axis]) low[axis]=v;
            if (v>high[axis]) high[axis]=v;
        }
    float extent=fmaxf(high[0]-low[0],fmaxf(high[1]-low[1],high[2]-low[2]));
    if (!isfinite(extent) || extent<=0) return 0;
    float normalized[BRAKE_VERTICES][3];
    for (size_t i=0;i<mesh->vertex_count;++i)
        for (size_t axis=0;axis<3;++axis)
            normalized[i][axis]=(mesh->positions[i][axis]-(low[axis]+high[axis])*0.5f)*2/extent;
    size_t written=0;
    for (size_t face=0;face<mesh->face_count;++face) {
        const uint8_t *indices=mesh->faces[face];
        for (size_t j=0;j<3;++j) if (indices[j]>=mesh->vertex_count) return 0;
        const float *a=normalized[indices[0]],*b=normalized[indices[1]],*c=normalized[indices[2]];
        float u[3],v[3],normal[3];
        for (size_t axis=0;axis<3;++axis) { u[axis]=b[axis]-a[axis];v[axis]=c[axis]-a[axis]; }
        normal[0]=u[1]*v[2]-u[2]*v[1];normal[1]=u[2]*v[0]-u[0]*v[2];normal[2]=u[0]*v[1]-u[1]*v[0];
        float length=sqrtf(normal[0]*normal[0]+normal[1]*normal[1]+normal[2]*normal[2]);
        if (!isfinite(length) || length<=0) return 0;
        for (size_t axis=0;axis<3;++axis) normal[axis]/=length;
        if (!wireframe) {
            for (size_t j=0;j<3;++j) {
                memcpy(out[written].position,normalized[indices[j]],sizeof(normal));
                memcpy(out[written].normal,normal,sizeof(normal));
                ++written;
            }
        } else {
            /* PICA200 has no line primitive: draw thin in-plane triangle ribbons. */
            for (size_t edge=0;edge<3;++edge) {
                const float *p=normalized[indices[edge]],*q=normalized[indices[(edge+1)%3]];
                float d[3],side[3];
                for (size_t axis=0;axis<3;++axis) d[axis]=q[axis]-p[axis];
                side[0]=normal[1]*d[2]-normal[2]*d[1];
                side[1]=normal[2]*d[0]-normal[0]*d[2];
                side[2]=normal[0]*d[1]-normal[1]*d[0];
                float scale=0.004f/sqrtf(side[0]*side[0]+side[1]*side[1]+side[2]*side[2]);
                float corners[4][3];
                for (size_t axis=0;axis<3;++axis) {
                    corners[0][axis]=p[axis]-side[axis]*scale;
                    corners[1][axis]=p[axis]+side[axis]*scale;
                    corners[2][axis]=q[axis]+side[axis]*scale;
                    corners[3][axis]=q[axis]-side[axis]*scale;
                }
                const uint8_t order[]={0,1,2,0,2,3};
                for (size_t j=0;j<6;++j) {
                    memcpy(out[written].position,corners[order[j]],sizeof(normal));
                    memcpy(out[written].normal,normal,sizeof(normal));
                    ++written;
                }
            }
        }
    }
    return written;
}
