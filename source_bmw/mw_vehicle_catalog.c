#include "mw_vehicle_catalog.h"
#include <math.h>
#include <string.h>
static uint32_t word(const unsigned char *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static float real(const unsigned char *p){uint32_t b=word(p);float f;memcpy(&f,&b,4);return f;}
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned j=0;j<8;j++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
static bool text(const unsigned char *p,size_t n,bool id){
    size_t i=0;for(;i<n&&p[i];i++)if(id?!(p[i]>='A'&&p[i]<='Z')&&!(p[i]>='0'&&p[i]<='9')&&p[i]!='_':p[i]<32||p[i]>126)return false;
    if(!i||i==n)return false;
    for(;i<n;i++)if(p[i])return false;
    return true;
}
bool mw_vehicle_catalog_get(const MwVehicleCatalog *c,uint32_t index,MwVehicleSpec *out){
    if(!c||!c->data||!out||index>=c->count)return false;
    const unsigned char *p=c->data+96+(size_t)index*160;
    *out=(MwVehicleSpec){.frontend_key=word(p),.ecar_key=word(p+4),.body_crc=word(p+8),.wheel_crc=word(p+12),.half_extent=real(p+16),.id=(const char *)p+24,.display_name=(const char *)p+56};return true;
}
bool mw_vehicle_catalog_open(MwVehicleCatalog *out,const void *data,size_t bytes){
    if(!out||!data||bytes<256||bytes>96+128*160)return false;
    const unsigned char *p=data;uint32_t count=word(p+16);
    if(memcmp(p,"NVC1",4)||word(p+4)!=1||word(p+8)!=bytes||word(p+12)!=crc(p+16,bytes-16)||!count||count>128||word(p+20)!=96||word(p+24)!=160||word(p+28)||bytes!=96+(uint64_t)count*160)return false;
    static const unsigned char attr[32]={91,105,196,79,252,252,112,19,163,242,73,0,179,54,23,0,43,31,104,242,72,74,145,8,218,165,191,229,215,42,210,12};
    static const unsigned char parts[32]={218,2,53,61,231,13,234,58,138,81,214,35,30,78,253,225,90,184,197,199,46,237,97,25,164,155,201,218,210,11,119,11};
    if(memcmp(p+32,attr,32)||memcmp(p+64,parts,32))return false;
    MwVehicleCatalog view={p,bytes,count};MwVehicleSpec previous={0};
    for(uint32_t i=0;i<count;i++){
        MwVehicleSpec s;mw_vehicle_catalog_get(&view,i,&s);const unsigned char *r=p+96+(size_t)i*160;
        if(!s.ecar_key||!isfinite(s.half_extent)||s.half_extent<=1||s.half_extent>=4||word(r+20)||!text(r+24,32,true)||!text(r+56,64,false)||(i&&strcmp(previous.id,s.id)>=0))return false;
        for(unsigned j=152;j<160;j++)if(r[j])return false;
        unsigned nonzero=0;for(unsigned j=120;j<152;j++)nonzero|=r[j];if(!nonzero)return false;
        for(uint32_t j=0;j<i;j++){MwVehicleSpec other;mw_vehicle_catalog_get(&view,j,&other);if(other.ecar_key==s.ecar_key||(s.frontend_key&&other.frontend_key==s.frontend_key))return false;}
        previous=s;
    }
    *out=view;return true;
}
bool mw_vehicle_catalog_find_id(const MwVehicleCatalog *c,const char *id,MwVehicleSpec *out){
    if(!c||!c->data||!id||!out)return false;
    for(uint32_t i=0;i<c->count;i++){MwVehicleSpec s;if(!mw_vehicle_catalog_get(c,i,&s))return false;if(!strcmp(s.id,id)){*out=s;return true;}}return false;
}
bool mw_vehicle_catalog_find_frontend(const MwVehicleCatalog *c,uint32_t key,MwVehicleSpec *out){
    if(!c||!c->data||!key||!out)return false;
    for(uint32_t i=0;i<c->count;i++){MwVehicleSpec s;if(!mw_vehicle_catalog_get(c,i,&s))return false;if(s.frontend_key==key){*out=s;return true;}}return false;
}
