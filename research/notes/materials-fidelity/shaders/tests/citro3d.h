#ifndef MOCK_CITRO3D_H
#define MOCK_CITRO3D_H
#include <stdint.h>
enum { C3D_RGB=1,C3D_Alpha=2,C3D_Both=3 };
enum { GPU_PRIMARY_COLOR=0,GPU_TEXTURE0=3,GPU_CONSTANT=14,GPU_PREVIOUS=15 };
enum { GPU_REPLACE=0,GPU_MODULATE=1,GPU_TEVOP_RGB_SRC_COLOR=0 };
typedef struct {
    int src[2][3],func[2],opRgb[3],scale[2];uint32_t color;
} C3D_TexEnv;
C3D_TexEnv *C3D_GetTexEnv(int stage);
static inline void C3D_TexEnvInit(C3D_TexEnv *e) {
    *e=(C3D_TexEnv){.src={{GPU_PREVIOUS,0,0},{GPU_PREVIOUS,0,0}},
        .func={GPU_REPLACE,GPU_REPLACE},.scale={1,1},.color=0xffffffff};
}
static inline void C3D_TexEnvSrc(C3D_TexEnv *e,int mode,int a,int b,int c) {
    for (int i=0;i<2;++i) if (mode&(1<<i)) { e->src[i][0]=a;e->src[i][1]=b;e->src[i][2]=c; }
}
static inline void C3D_TexEnvFunc(C3D_TexEnv *e,int mode,int func) {
    for (int i=0;i<2;++i) if (mode&(1<<i)) e->func[i]=func;
}
static inline void C3D_TexEnvColor(C3D_TexEnv *e,uint32_t color) { e->color=color; }
static inline void C3D_TexEnvOpRgb(C3D_TexEnv *e,int a,int b,int c) {
    e->opRgb[0]=a;e->opRgb[1]=b;e->opRgb[2]=c;
}
#endif
