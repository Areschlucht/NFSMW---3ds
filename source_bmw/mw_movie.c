#include "mw_movie.h"
#include <limits.h>
#include <stdlib.h>
#include <string.h>
#ifndef MW_MOVIE_NO_JPEG
#include <setjmp.h>
#include <jpeglib.h>
#endif

static uint32_t word(const unsigned char *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static uint32_t update_crc(uint32_t crc,const unsigned char *p,size_t bytes)
{ while(bytes--){crc^=*p++;for(unsigned i=0;i<8;i++)crc=(crc>>1)^(0xedb88320u&-(crc&1u));}return crc; }
static uint32_t crc32(const void *p,size_t bytes)
{ return ~update_crc(~0u,p,bytes); }
static bool read_at(FILE *f,uint32_t at,void *out,size_t bytes)
{ return f&&!fseek(f,(long)at,SEEK_SET)&&fread(out,1,bytes,f)==bytes; }
void mw_movie_close(MwMovie *m)
{ if(!m)return;if(m->video)fclose(m->video);if(m->audio)fclose(m->audio);memset(m,0,sizeof(*m)); }

bool mw_movie_open(MwMovie *out,const char *path)
{
    if(!out||!path)return false;
    MwMovie m={0};unsigned char h[128],record[16];
    m.video=fopen(path,"rb");if(!m.video)return false;
    if(fseek(m.video,0,SEEK_END))goto fail;
    long size=ftell(m.video);if(size<128||size>INT32_MAX||!read_at(m.video,0,h,sizeof(h)))goto fail;
    if(memcmp(h,"NVM1",4)||word(h+4)!=1||word(h+8)!=(uint32_t)size||word(h+12)!=crc32(h+16,112)||
       word(h+16)!=MW_MOVIE_WIDTH||word(h+20)!=MW_MOVIE_HEIGHT||word(h+24)!=982047||word(h+28)!=32767||
       word(h+36)!=128||word(h+40)!=16||word(h+64)!=32000||word(h+68)!=2||word(h+112)!=MW_MOVIE_AUDIO_BLOCK_FRAMES)goto fail;
    for(unsigned i=116;i<128;i++)if(h[i])goto fail;
    m.total_bytes=(uint32_t)size;m.frames=word(h+32);m.rate_numerator=word(h+24);m.rate_denominator=word(h+28);
    m.audio_crc_at=word(h+44);m.audio_blocks=word(h+48);m.data_at=word(h+52);m.audio_at=word(h+56);
    m.audio_frames=word(h+60);m.sample_rate=word(h+64);m.max_jpeg_bytes=word(h+72);memcpy(m.source_sha256,h+80,32);
    if(!m.frames||m.frames>65535||!m.audio_frames||!m.max_jpeg_bytes||m.max_jpeg_bytes>MW_MOVIE_JPEG_CAPACITY||
       m.audio_crc_at!=128+m.frames*16||m.audio_blocks!=((uint64_t)m.audio_frames+4095)/4096||
       m.data_at!=((m.audio_crc_at+(uint64_t)m.audio_blocks*4+15)&~15ull)||
       (m.audio_at&3)||m.audio_at<m.data_at||m.audio_at+(uint64_t)m.audio_frames*4!=m.total_bytes)goto fail;
    uint32_t expected=m.data_at,largest=0,index_crc=~0u;
    if(fseek(m.video,128,SEEK_SET))goto fail;
    for(uint32_t i=0;i<m.frames;i++){
        if(fread(record,1,16,m.video)!=16)goto fail;
        index_crc=update_crc(index_crc,record,16);uint32_t bytes=word(record+4);
        if(word(record)!=expected||!bytes||bytes>m.max_jpeg_bytes||word(record+12)||
           expected+(uint64_t)bytes>m.audio_at)goto fail;
        if(bytes>largest)largest=bytes;
        expected=(expected+bytes+3)&~3u;
    }
    if(expected!=m.audio_at||largest!=m.max_jpeg_bytes)goto fail;
    for(uint32_t i=0;i<m.audio_blocks;i++){
        if(fread(record,1,4,m.video)!=4)goto fail;
        index_crc=update_crc(index_crc,record,4);
    }
    if(~index_crc!=word(h+76))goto fail;
    m.audio=fopen(path,"rb");if(!m.audio)goto fail;
    *out=m;return true;
fail:
    mw_movie_close(&m);return false;
}

bool mw_movie_frame_info(MwMovie *m,uint32_t index,MwMovieFrame *out)
{
    if(!m||!m->video||!out||index>=m->frames)return false;
    unsigned char r[16];if(!read_at(m->video,128+index*16,r,16))return false;
    MwMovieFrame frame={word(r),word(r+4),word(r+8)};
    if(frame.offset<m->data_at||(frame.offset&3)||!frame.bytes||frame.bytes>m->max_jpeg_bytes||
       frame.offset+(uint64_t)frame.bytes>m->audio_at||word(r+12))return false;
    *out=frame;return true;
}
bool mw_movie_frame_jpeg(MwMovie *m,uint32_t index,void *scratch,size_t capacity,size_t *out_bytes)
{
    MwMovieFrame f;
    if(!scratch||!out_bytes||!mw_movie_frame_info(m,index,&f)||f.bytes>capacity||
       !read_at(m->video,f.offset,scratch,f.bytes)||crc32(scratch,f.bytes)!=f.crc32)return false;
    *out_bytes=f.bytes;return true;
}
bool mw_movie_audio_block(MwMovie *m,uint32_t block,void *pcm,size_t capacity,uint32_t *out_frames)
{
    if(!m||!m->audio||!pcm||!out_frames||block>=m->audio_blocks)return false;
    uint32_t frames=m->audio_frames-block*4096;if(frames>4096)frames=4096;
    size_t bytes=frames*4;unsigned char expected[4];
    if(bytes>capacity||!read_at(m->audio,m->audio_crc_at+block*4,expected,4)||
       !read_at(m->audio,m->audio_at+block*MW_MOVIE_AUDIO_BLOCK_BYTES,pcm,bytes)||crc32(pcm,bytes)!=word(expected))return false;
    *out_frames=frames;return true;
}
uint64_t mw_movie_video_duration_us(const MwMovie *m)
{ return m&&m->frames&&m->rate_numerator?((uint64_t)m->frames*m->rate_denominator*1000000+m->rate_numerator-1)/m->rate_numerator:0; }
uint64_t mw_movie_duration_us(const MwMovie *m)
{
    uint64_t video=mw_movie_video_duration_us(m),audio=m&&m->sample_rate?((uint64_t)m->audio_frames*1000000+m->sample_rate-1)/m->sample_rate:0;
    return video>audio?video:audio;
}
uint32_t mw_movie_frame_at_us(const MwMovie *m,uint64_t us)
{
    if(!m||!m->frames||!m->rate_numerator||!m->rate_denominator)return 0;
    if(us>=mw_movie_video_duration_us(m))return m->frames-1;
    return (uint32_t)(us*m->rate_numerator/((uint64_t)m->rate_denominator*1000000));
}
uint32_t mw_movie_frame_at_audio_sample(const MwMovie *m,uint64_t samples)
{
    if(!m||!m->frames||!m->sample_rate||!m->rate_numerator||!m->rate_denominator)return 0;
    uint64_t end=((uint64_t)m->frames*m->rate_denominator*m->sample_rate+m->rate_numerator-1)/m->rate_numerator;
    if(samples>=end)return m->frames-1;
    return (uint32_t)(samples*m->rate_numerator/((uint64_t)m->rate_denominator*m->sample_rate));
}

#ifndef MW_MOVIE_NO_JPEG
typedef struct { struct jpeg_error_mgr base;jmp_buf jump; } MovieJpegError;
static void jpeg_failed(j_common_ptr jpeg)
{ MovieJpegError *error=(MovieJpegError *)jpeg->err;longjmp(error->jump,1); }
static void jpeg_message(j_common_ptr jpeg,int level)
{ if(level<0)jpeg_failed(jpeg); }
bool mw_movie_decode_jpeg(const void *data,size_t bytes,unsigned char *pixels,size_t capacity)
{
    if(!data||!bytes||bytes>MW_MOVIE_JPEG_CAPACITY||!pixels||capacity!=MW_MOVIE_PIXELS)return false;
    struct jpeg_decompress_struct decoder;MovieJpegError error;volatile bool created=false;
    memset(&decoder,0,sizeof(decoder));decoder.err=jpeg_std_error(&error.base);error.base.error_exit=jpeg_failed;error.base.emit_message=jpeg_message;
    if(setjmp(error.jump)){if(created)jpeg_destroy_decompress(&decoder);return false;}
    jpeg_create_decompress(&decoder);created=true;
    jpeg_mem_src(&decoder,(const unsigned char *)data,(unsigned long)bytes);
    if(jpeg_read_header(&decoder,TRUE)!=JPEG_HEADER_OK||decoder.image_width!=MW_MOVIE_WIDTH||decoder.image_height!=MW_MOVIE_HEIGHT||decoder.progressive_mode||decoder.num_components!=3)goto invalid;
    decoder.out_color_space=JCS_RGB;decoder.do_fancy_upsampling=FALSE;decoder.dct_method=JDCT_IFAST;
    if(!jpeg_start_decompress(&decoder)||decoder.output_width!=MW_MOVIE_WIDTH||decoder.output_height!=MW_MOVIE_HEIGHT||decoder.output_components!=3)goto invalid;
    unsigned char row[MW_MOVIE_WIDTH*3];JSAMPROW rows[1]={row};
    while(decoder.output_scanline<decoder.output_height){
        unsigned y=decoder.output_scanline;if(jpeg_read_scanlines(&decoder,rows,1)!=1)goto invalid;
        for(unsigned x=0;x<MW_MOVIE_WIDTH;x++){
            unsigned value=((unsigned)(row[x*3]>>3)<<11)|((unsigned)(row[x*3+1]>>2)<<5)|(row[x*3+2]>>3);
            pixels[(y*MW_MOVIE_WIDTH+x)*2]=(unsigned char)value;pixels[(y*MW_MOVIE_WIDTH+x)*2+1]=(unsigned char)(value>>8);
        }
    }
    if(!jpeg_finish_decompress(&decoder))goto invalid;
    jpeg_destroy_decompress(&decoder);return true;
invalid:
    jpeg_destroy_decompress(&decoder);return false;
}
#else
bool mw_movie_decode_jpeg(const void *p,size_t n,unsigned char *out,size_t bytes)
{ (void)p;(void)n;(void)out;(void)bytes;return false; }
#endif

bool mw_movie_texture_pack(void *texture,size_t bytes,const unsigned char *pixels,size_t source_bytes)
{
    if(!texture||bytes!=MW_MOVIE_TEXTURE_BYTES||!pixels||source_bytes!=MW_MOVIE_PIXELS)return false;
    unsigned char *out=texture;memset(out,0,bytes);
    static const unsigned morton[8]={0,1,4,5,16,17,20,21};
    for(unsigned y=0;y<MW_MOVIE_HEIGHT;y++)for(unsigned x=0;x<MW_MOVIE_WIDTH;x++){
        unsigned offset=(y*MW_MOVIE_WIDTH+x)*2,color=pixels[offset]|(unsigned)pixels[offset+1]<<8;
        unsigned at=(((y>>3)*64+(x>>3))*64+morton[x&7]+2*morton[y&7])*4;
        out[at]=255;out[at+1]=(unsigned char)((color&31)*255/31);
        out[at+2]=(unsigned char)(((color>>5)&63)*255/63);out[at+3]=(unsigned char)((color>>11)*255/31);
    }
    return true;
}
