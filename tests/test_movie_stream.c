#define _POSIX_C_SOURCE 200809L
#include "mw_movie.h"
#include <assert.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static uint32_t word(const unsigned char *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static void put(unsigned char *p,uint32_t v)
{ for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(v>>(i*8)); }
static uint32_t crc(const unsigned char *p,size_t bytes)
{ uint32_t c=~0u;while(bytes--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c; }
static void fix_header(unsigned char *p)
{ put(p+12,crc(p+16,112)); }
static void fix_index(unsigned char *p)
{ put(p+76,crc(p+128,word(p+44)+word(p+48)*4-128));fix_header(p); }
static void save(const char *path,const void *data,size_t bytes)
{ FILE *f=fopen(path,"wb");assert(f&&fwrite(data,1,bytes,f)==bytes&&!fclose(f)); }
static void reject(const char *path,const void *data,size_t bytes)
{
    save(path,data,bytes);MwMovie out={.frames=123,.total_bytes=456},before=out;
    assert(!mw_movie_open(&out,path));assert(!memcmp(&out,&before,sizeof(out)));
}
static unsigned morton(unsigned x,unsigned y)
{
    unsigned index=0;for(unsigned bit=0;bit<3;bit++){index|=((x>>bit)&1u)<<(bit*2);index|=((y>>bit)&1u)<<(bit*2+1);}return index;
}
int main(int argc,char **argv)
{
    assert(argc==2);MwMovie movie={0};assert(mw_movie_open(&movie,argv[1]));
    assert(movie.frames==92&&movie.audio_frames==120484&&movie.sample_rate==32000);
    assert(mw_movie_video_duration_us(&movie)==3069674&&mw_movie_duration_us(&movie)==3765125);
    assert(mw_movie_frame_at_us(&movie,0)==0&&mw_movie_frame_at_us(&movie,33366)==0&&mw_movie_frame_at_us(&movie,33367)==1);
    assert(mw_movie_frame_at_us(&movie,UINT64_MAX)==91&&mw_movie_frame_at_audio_sample(&movie,UINT64_MAX)==91);
    for(uint32_t i=0;i<movie.frames;i++){
        uint64_t us=((uint64_t)i*32767*1000000+982047-1)/982047;
        assert(mw_movie_frame_at_us(&movie,us)==i);
        uint64_t samples=((uint64_t)i*32767*32000+982047-1)/982047;
        assert(mw_movie_frame_at_audio_sample(&movie,samples)==i);
    }
    unsigned char *jpeg=malloc(MW_MOVIE_JPEG_CAPACITY+16),*pixels=malloc(MW_MOVIE_PIXELS+32),*texture=malloc(MW_MOVIE_TEXTURE_BYTES+32);
    assert(jpeg&&pixels&&texture);memset(pixels,0x7d,MW_MOVIE_PIXELS+32);memset(texture,0x5a,MW_MOVIE_TEXTURE_BYTES+32);
    uint32_t largest=0;size_t bytes=0;
    for(uint32_t i=0;i<movie.frames;i++){
        MwMovieFrame frame;assert(mw_movie_frame_info(&movie,i,&frame));if(frame.bytes>largest)largest=frame.bytes;
        assert(mw_movie_frame_jpeg(&movie,i,jpeg,MW_MOVIE_JPEG_CAPACITY,&bytes)&&bytes==frame.bytes);
#ifndef MW_MOVIE_NO_JPEG
        assert(mw_movie_decode_jpeg(jpeg,bytes,pixels+16,MW_MOVIE_PIXELS));
#endif
    }
    assert(largest==movie.max_jpeg_bytes);
    uint64_t audio_frames=0;unsigned char pcm[MW_MOVIE_AUDIO_BLOCK_BYTES+32];memset(pcm,0xe7,sizeof(pcm));
    for(uint32_t i=0;i<movie.audio_blocks;i++){
        uint32_t frames;assert(mw_movie_audio_block(&movie,i,pcm+16,MW_MOVIE_AUDIO_BLOCK_BYTES,&frames));audio_frames+=frames;
    }
    assert(audio_frames==movie.audio_frames);
    for(unsigned i=0;i<16;i++)assert(pcm[i]==0xe7&&pcm[MW_MOVIE_AUDIO_BLOCK_BYTES+16+i]==0xe7);
    assert(!mw_movie_audio_block(&movie,movie.audio_blocks,pcm,sizeof(pcm),&largest));
    assert(!mw_movie_frame_jpeg(&movie,0,jpeg,1,&bytes));
    assert(!mw_movie_frame_info(&movie,movie.frames,(MwMovieFrame *)&(MwMovieFrame){0}));
    /* Distinct RGB565 values across every pixel exercise channel and tile axes. */
    for(unsigned i=0;i<MW_MOVIE_WIDTH*MW_MOVIE_HEIGHT;i++){unsigned color=(i*73u)^(i>>3);pixels[16+i*2]=(unsigned char)color;pixels[17+i*2]=(unsigned char)(color>>8);}
    assert(mw_movie_texture_pack(texture+16,MW_MOVIE_TEXTURE_BYTES,pixels+16,MW_MOVIE_PIXELS));
    for(unsigned y=0;y<256;y++)for(unsigned x=0;x<512;x++){
        unsigned at=16+(((y/8)*64+x/8)*64+morton(x,y))*4;
        if(x>=MW_MOVIE_WIDTH||y>=MW_MOVIE_HEIGHT){assert(!texture[at]&&!texture[at+1]&&!texture[at+2]&&!texture[at+3]);continue;}
        unsigned p=16+(y*MW_MOVIE_WIDTH+x)*2,c=pixels[p]|(unsigned)pixels[p+1]<<8;
        assert(texture[at]==255&&texture[at+1]==(c&31)*255/31&&texture[at+2]==((c>>5)&63)*255/63&&texture[at+3]==(c>>11)*255/31);
    }
    for(unsigned i=0;i<16;i++)assert(pixels[i]==0x7d&&pixels[MW_MOVIE_PIXELS+16+i]==0x7d&&texture[i]==0x5a&&texture[MW_MOVIE_TEXTURE_BYTES+16+i]==0x5a);
#ifndef MW_MOVIE_NO_JPEG
    assert(!mw_movie_decode_jpeg("bad",3,pixels+16,MW_MOVIE_PIXELS));
    assert(mw_movie_frame_jpeg(&movie,0,jpeg,MW_MOVIE_JPEG_CAPACITY,&bytes));
    assert(!mw_movie_decode_jpeg(jpeg,bytes-2,pixels+16,MW_MOVIE_PIXELS));
    assert(!mw_movie_decode_jpeg(jpeg,bytes,pixels+16,MW_MOVIE_PIXELS-1));
#endif
    mw_movie_close(&movie);mw_movie_close(&movie);
    FILE *source=fopen(argv[1],"rb");assert(source&&!fseek(source,0,SEEK_END));long total=ftell(source);rewind(source);
    unsigned char *data=malloc((size_t)total),*bad=malloc((size_t)total);assert(data&&bad&&fread(data,1,(size_t)total,source)==(size_t)total);fclose(source);
    char path[]="/tmp/nfsmw-movie-stream.XXXXXX";int fd=mkstemp(path);assert(fd>=0&&!close(fd));
    for(unsigned length=0;length<128;length++)reject(path,data,length);
    reject(path,data,(size_t)total-1);
    for(unsigned at=0;at<128;at++){memcpy(bad,data,(size_t)total);bad[at]^=1;reject(path,bad,(size_t)total);}
    const unsigned fields[]={16,20,24,28,32,36,40,44,48,52,56,60,64,68,72,112,116,120,124};
    for(unsigned i=0;i<sizeof(fields)/sizeof(*fields);i++){memcpy(bad,data,(size_t)total);bad[fields[i]]^=1;fix_header(bad);reject(path,bad,(size_t)total);}
    for(unsigned field=0;field<16;field+=4){memcpy(bad,data,(size_t)total);bad[128+field]^=1;fix_index(bad);
        if(field==4){put(bad+132,word(data+132)+4);fix_index(bad);}
        if(field==8)continue; /* Recomputed per-payload CRC is checked on read. */
        reject(path,bad,(size_t)total);
    }
    memcpy(bad,data,(size_t)total);bad[136]^=1;fix_index(bad);save(path,bad,(size_t)total);assert(mw_movie_open(&movie,path));
    assert(!mw_movie_frame_jpeg(&movie,0,jpeg,MW_MOVIE_JPEG_CAPACITY,&bytes));mw_movie_close(&movie);
    memcpy(bad,data,(size_t)total);bad[word(data+52)+100]^=1;save(path,bad,(size_t)total);assert(mw_movie_open(&movie,path));
    assert(!mw_movie_frame_jpeg(&movie,0,jpeg,MW_MOVIE_JPEG_CAPACITY,&bytes));mw_movie_close(&movie);
    memcpy(bad,data,(size_t)total);bad[word(data+56)+100]^=1;save(path,bad,(size_t)total);assert(mw_movie_open(&movie,path));
    assert(!mw_movie_audio_block(&movie,0,pcm,sizeof(pcm),&largest));mw_movie_close(&movie);assert(!unlink(path));
    free(data);free(bad);free(jpeg);free(pixels);free(texture);
    puts("Movie:92 JPEG frames,120484 PCM frames, exact clock,131072 tiled texels, bounded indexes and corruptions passed.");
    return 0;
}
