#include "mw_color_grade.h"
#include <citro3d.h>

void mw_color_grade_apply(bool enabled)
{
    /* Explicitly restore every stage after other renderers/toggle changes. */
    for (int stage=0;stage<6;++stage) {
        C3D_TexEnv *env=C3D_GetTexEnv(stage);
        C3D_TexEnvInit(env);
        if (stage==0) {
            C3D_TexEnvSrc(env,C3D_Both,GPU_TEXTURE0,GPU_PRIMARY_COLOR,0);
            C3D_TexEnvFunc(env,C3D_Both,GPU_MODULATE);
        } else if (stage==1 && enabled) {
            /* PICA constant register uses 0xAABBGGRR. Only RGB is multiplied;
             * alpha remains the previous stage's original source alpha. */
            const uint32_t gain=(uint32_t)MW_COLOR_GRADE_RED |
                ((uint32_t)MW_COLOR_GRADE_GREEN<<8) |
                ((uint32_t)MW_COLOR_GRADE_BLUE<<16) | UINT32_C(0xff000000);
            C3D_TexEnvSrc(env,C3D_RGB,GPU_PREVIOUS,GPU_CONSTANT,0);
            C3D_TexEnvOpRgb(env,GPU_TEVOP_RGB_SRC_COLOR,GPU_TEVOP_RGB_SRC_COLOR,GPU_TEVOP_RGB_SRC_COLOR);
            C3D_TexEnvFunc(env,C3D_RGB,GPU_MODULATE);
            C3D_TexEnvColor(env,gain);
        }
    }
}

uint32_t mw_color_grade_clear(uint32_t rgba,bool enabled)
{
    if (!enabled) return rgba;
    uint32_t red=((rgba>>24)*MW_COLOR_GRADE_RED+127)/255;
    uint32_t green=(((rgba>>16)&255)*MW_COLOR_GRADE_GREEN+127)/255;
    uint32_t blue=(((rgba>>8)&255)*MW_COLOR_GRADE_BLUE+127)/255;
    return (red<<24)|(green<<16)|(blue<<8)|(rgba&255);
}
