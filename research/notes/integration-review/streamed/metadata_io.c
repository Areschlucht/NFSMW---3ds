#include "streamed_world.h"
#include <assert.h>
#include <stdio.h>
size_t __wrap_fread(void *p,size_t size,size_t count,FILE *file){(void)p;(void)size;(void)count;(void)file;return 0;}
int main(int argc,char **argv){assert(argc==3);StreamedWorldConfig c={.asset_root=argv[1],.metadata_path=argv[2],.normal_bytes=1024*1024,.linear_bytes=1024*1024,.scratch_bytes=256,.cache_entries=1,.object_capacity=1,.run_capacity=1,.render_scale=.001f,.lod_mode=STREAMED_WORLD_REFERENCE_SLOT0};StreamedWorld*w=(StreamedWorld*)1;assert(streamed_world_create(&c,&w)==STREAMED_WORLD_IO);assert(!w&&mock_linear_used==0);puts("Injected metadata short read classified IO, output NULL, no GPU allocations.");return 0;}
