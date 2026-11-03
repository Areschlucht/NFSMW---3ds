#include "brake_mesh.h"
#include "brake_render.h"
#include "brake_gpu_mesh.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static BrakePackage package;
static uint8_t framebuffer[VIEW_BYTES];
static float depth[VIEW_PIXELS];
static struct {
    uint64_t before;
    BrakeGpuVertex vertices[BRAKE_GPU_MAX_VERTICES];
    uint64_t after;
} gpu_buffer;

static void test_gpu_mesh(const BrakeMesh *mesh)
{
    for (unsigned mode=0;mode<2;++mode) {
        gpu_buffer.before=0x12345678;
        gpu_buffer.after=0xabcdef12;
        size_t expected=mesh->face_count*(mode?18:3);
        assert(!brake_gpu_mesh(mesh,mode,gpu_buffer.vertices,expected-1));
        assert(brake_gpu_mesh(mesh,mode,gpu_buffer.vertices,BRAKE_GPU_MAX_VERTICES)==expected);
        assert(gpu_buffer.before==0x12345678 && gpu_buffer.after==0xabcdef12);
        for (size_t v=0;v<expected;++v) {
            float length=0;
            for (size_t a=0;a<3;++a) {
                assert(isfinite(gpu_buffer.vertices[v].position[a]));
                assert(fabsf(gpu_buffer.vertices[v].position[a])<=1.01f);
                float n=gpu_buffer.vertices[v].normal[a];
                assert(isfinite(n));length+=n*n;
            }
            assert(fabsf(length-1)<1e-5f);
        }
    }
}

int main(int argc,char **argv)
{
    assert(argc==2 || argc==3);
    FILE *file=fopen(argv[1],"rb");assert(file);
    uint8_t original[BRAKE_SAMPLE_BYTES],changed[BRAKE_SAMPLE_BYTES];
    assert(fread(original,1,sizeof(original),file)==sizeof(original));
    assert(fgetc(file)==EOF);fclose(file);
    assert(brake_package_decode(original,sizeof(original),&package));
    assert(package.model_count==4);
    const size_t vertices[]={22,26,28,43},triangles[]={27,29,32,41};
    for (size_t model=0;model<4;++model) {
        const BrakeMesh *mesh=&package.models[model];
        test_gpu_mesh(mesh);
        assert(mesh->vertex_count==vertices[model] && mesh->face_count==triangles[model]);
        for (size_t i=0;i<mesh->face_count;++i)
            for (size_t j=0;j<3;++j) assert(mesh->faces[i][j]<mesh->vertex_count);
        for (unsigned mode=0;mode<2;++mode)
            for (unsigned frame=0;frame<6;++frame) {
                brake_render(mesh,framebuffer,depth,frame*0.7f,-0.8f,frame&1?1.7f:0.5f,mode);
                size_t lit=0;
                for (size_t i=0;i<VIEW_BYTES;++i) lit+=framebuffer[i]!=12;
                assert(lit>100);
            }
        if (argc==3) {
            brake_render(mesh,framebuffer,depth,0,-0.8f,1,false);
            char path[1024];
            int count=snprintf(path,sizeof(path),"%s/model-%zu.ppm",argv[2],model);
            assert(count>0 && (size_t)count<sizeof(path));
            FILE *out=fopen(path,"wb");assert(out);
            fprintf(out,"P6\n400 240\n255\n");
            for (int y=0;y<VIEW_HEIGHT;++y)
                for (int x=0;x<VIEW_WIDTH;++x) {
                    size_t p=((size_t)x*VIEW_HEIGHT+VIEW_HEIGHT-1-y)*3;
                    fputc(framebuffer[p+2],out);fputc(framebuffer[p+1],out);fputc(framebuffer[p],out);
                }
            assert(!fclose(out));
        }
    }
    assert(!brake_package_decode(NULL,sizeof(original),&package));
    assert(!brake_package_decode(original,sizeof(original),NULL));
    for (size_t n=0;n<sizeof(original);++n) assert(!brake_package_decode(original,n,&package));
    assert(!brake_package_decode(original,sizeof(original)+1,&package));
    const size_t corrupt_offsets[]={0,4,0x18c,0x284,0x28c,0x2c0,0x2cd,0x340,0x343};
    for (size_t i=0;i<sizeof(corrupt_offsets)/sizeof(corrupt_offsets[0]);++i) {
        memcpy(changed,original,sizeof(changed));changed[corrupt_offsets[i]]=255;
        assert(!brake_package_decode(changed,sizeof(changed),&package));
    }
    /* Mutate every byte in turn to exercise variable chunk/table bounds. */
    for (size_t i=0;i<sizeof(original);++i) {
        memcpy(changed,original,sizeof(changed));changed[i]^=255;
        (void)brake_package_decode(changed,sizeof(changed),&package);
    }
    assert(brake_package_decode(original,sizeof(original),&package));
    BrakeMesh simple={.vertex_count=3,.face_count=1,
        .positions={{-1,-1,0},{1,-1,0},{-1,1,0}},.faces={{0,1,2}}};
    assert(brake_gpu_mesh(&simple,false,gpu_buffer.vertices,BRAKE_GPU_MAX_VERTICES)==3);
    for (size_t i=0;i<3;++i) {
        for (size_t a=0;a<3;++a) assert(gpu_buffer.vertices[i].position[a]==simple.positions[i][a]);
        assert(gpu_buffer.vertices[i].normal[0]==0 && gpu_buffer.vertices[i].normal[1]==0 && gpu_buffer.vertices[i].normal[2]==1);
    }
    assert(!brake_gpu_mesh(NULL,false,gpu_buffer.vertices,BRAKE_GPU_MAX_VERTICES));
    assert(!brake_gpu_mesh(&simple,false,NULL,BRAKE_GPU_MAX_VERTICES));
    simple.faces[0][2]=255;
    assert(!brake_gpu_mesh(&simple,false,gpu_buffer.vertices,BRAKE_GPU_MAX_VERTICES));
    simple.faces[0][2]=0;
    assert(!brake_gpu_mesh(&simple,false,gpu_buffer.vertices,BRAKE_GPU_MAX_VERTICES));
    simple.faces[0][2]=2;
    simple.positions[0][0]=NAN;
    assert(!brake_gpu_mesh(&simple,false,gpu_buffer.vertices,BRAKE_GPU_MAX_VERTICES));
    printf("[");
    for (size_t m=0;m<4;++m) {
        const BrakeMesh *mesh=&package.models[m];
        printf("%s{\"positions\":[",m?",":"");
        for (size_t i=0;i<mesh->vertex_count;++i)
            printf("%s[%.9g,%.9g,%.9g]",i?",":"",mesh->positions[i][0],mesh->positions[i][1],mesh->positions[i][2]);
        printf("],\"faces\":[");
        for (size_t i=0;i<mesh->face_count;++i)
            printf("%s[%u,%u,%u]",i?",":"",mesh->faces[i][0],mesh->faces[i][1],mesh->faces[i][2]);
        printf("]}");
    }
    puts("]");
    return 0;
}
