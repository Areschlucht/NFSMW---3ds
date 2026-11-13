#include "nfs_scene.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
int main(int argc,char **argv)
{
    assert(argc==6);const unsigned triangles[]={2097,9047,6757,1094,4819};
    const unsigned textures[]={33,53,55,13,33};
    for(unsigned i=0;i<5;i++){
        FILE *f=fopen(argv[i+1],"rb");assert(f);assert(!fseek(f,0,SEEK_END));long n=ftell(f);assert(n>32);rewind(f);
        unsigned char *raw=malloc((size_t)n);assert(raw&&fread(raw,1,(size_t)n,f)==(size_t)n);assert(!fclose(f));
        NfsScene s;assert(nfs_scene_decode(raw,(size_t)n,&s));assert(s.vertex_count==triangles[i]*3&&s.texture_count==textures[i]);
        printf("frontend platform %u: %u triangles, %u textures, %u ordered batches\n",i,s.vertex_count/3,s.texture_count,s.batch_count);
        nfs_scene_free(&s);free(raw);
    }
    return 0;
}
