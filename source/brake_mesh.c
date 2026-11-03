#include "brake_mesh.h"
#include <string.h>

typedef struct { size_t start, end; uint32_t id; } Chunk;
static uint16_t be16(const uint8_t *p) { return (uint16_t)((unsigned)p[0]*256+p[1]); }
static uint32_t be32(const uint8_t *p) { return (uint32_t)be16(p)<<16 | be16(p+2); }
static uint16_t le16(const uint8_t *p) { return (uint16_t)((unsigned)p[1]*256+p[0]); }
static uint32_t le32(const uint8_t *p) { return (uint32_t)le16(p+2)<<16 | le16(p); }
static int signed16(const uint8_t *p) { int v=be16(p); return v>=32768 ? v-65536 : v; }

static bool next(const uint8_t *data, size_t *position, size_t end, Chunk *chunk)
{
    if (*position>end || end-*position<8) return false;
    uint32_t bytes=le32(data+*position+4);
    if (bytes>end-*position-8) return false;
    chunk->start=*position; chunk->end=*position+8+bytes;
    chunk->id=le32(data+*position); *position=chunk->end;
    return true;
}

static bool find(const uint8_t *data, size_t start, size_t end, uint32_t id, Chunk *out)
{
    bool found=false;
    while (start<end) {
        Chunk chunk;
        if (!next(data,&start,end,&chunk)) return false;
        if (chunk.id==id) {
            if (found) return false;
            *out=chunk; found=true;
        }
    }
    return found;
}

static bool append_face(BrakeMesh *mesh, int raw[BRAKE_VERTICES][3], uint8_t a, uint8_t b, uint8_t c)
{
    int64_t u[3],v[3];
    for (size_t axis=0;axis<3;++axis) {
        u[axis]=raw[b][axis]-raw[a][axis]; v[axis]=raw[c][axis]-raw[a][axis];
    }
    if (u[1]*v[2]==u[2]*v[1] && u[2]*v[0]==u[0]*v[2] && u[0]*v[1]==u[1]*v[0]) return true;
    if (mesh->face_count>=BRAKE_MAX_FACES) return false;
    uint8_t *face=mesh->faces[mesh->face_count++];
    face[0]=a;face[1]=b;face[2]=c;
    return true;
}

static bool decode_model(const uint8_t *data, Chunk object, BrakeMesh *mesh)
{
    Chunk header,geom,metadata,descriptors,blob_chunk;
    if (!find(data,object.start+8,object.end,0x134011,&header) ||
        !find(data,object.start+8,object.end,0x80134100,&geom) ||
        !find(data,geom.start+8,geom.end,0x134800,&metadata) ||
        !find(data,geom.start+8,geom.end,0x134801,&descriptors) ||
        !find(data,geom.start+8,geom.end,0x134802,&blob_chunk)) return false;
    if (header.end-header.start<184) return false;
    size_t h=header.start+8;
    const uint8_t *name=data+h+160;
    const uint8_t *terminator=memchr(name,0,header.end-h-160);
    if (!terminator || (size_t)(terminator-name)>=sizeof(mesh->name)) return false;
    memcpy(mesh->name,name,(size_t)(terminator-name));

    /* Executable loader aligns payloads to 16, 16, and 32 bytes respectively. */
    size_t meta=(metadata.start+0x17)&~(size_t)15;
    size_t table=(descriptors.start+0x17)&~(size_t)15;
    size_t blob=(blob_chunk.start+0x27)&~(size_t)31;
    if (meta>metadata.end || metadata.end-meta<36 || table>descriptors.end || blob>blob_chunk.end) return false;
    unsigned records=be16(data+meta+4);
    if (be16(data+meta)!=0x16 || !records || records>64 || records*16>descriptors.end-table) return false;
    uint32_t total=be32(data+meta+8), positions=be32(data+meta+12), next_array=be32(data+meta+20);
    if (total>blob_chunk.end-blob || positions>=next_array || next_array>total) return false;
    unsigned maximum=0;
    for (unsigned record=0;record<records;++record) {
        size_t p=table+record*16;
        uint32_t offset=be32(data+p);
        unsigned length=be16(data+p+14), count=data[p+8], flags=data[p+12];
        if (data[p+13]!=0x16 || (flags!=0 && flags!=0x80) || count<3 || offset>total || length>total-offset) return false;
        unsigned prefix=flags ? 3 : 0, stride=flags ? 5 : 4;
        if (prefix+count*stride>length) return false;
        size_t first=blob+offset;
        if (flags && (data[first]!=0x9a || be16(data+first+1)!=count)) return false;
        for (unsigned i=0;i<count;++i) {
            unsigned index=data[first+prefix+i*stride];
            if (index>=BRAKE_VERTICES) return false;
            if (index>maximum) maximum=index;
        }
    }
    mesh->vertex_count=maximum+1;
    if (mesh->vertex_count*6>next_array-positions) return false;
    int raw[BRAKE_VERTICES][3];
    for (size_t i=0;i<mesh->vertex_count;++i)
        for (size_t axis=0;axis<3;++axis) {
            raw[i][axis]=signed16(data+blob+positions+i*6+axis*2);
            /* GX format 2: XYZ signed-16 with 11 fractional bits. */
            mesh->positions[i][axis]=raw[i][axis]/2048.0f;
        }
    for (unsigned record=0;record<records;++record) {
        size_t p=table+record*16;
        unsigned count=data[p+8], prefix=data[p+12] ? 3 : 0, stride=prefix ? 5 : 4;
        size_t first=blob+be32(data+p)+prefix;
        uint8_t strip[255];
        for (unsigned i=0;i<count;++i) strip[i]=data[first+i*stride];
        for (unsigned i=0;i+2<count;++i) {
            if (!append_face(mesh,raw,strip[i+(i&1)],strip[i+1-(i&1)],strip[i+2])) return false;
        }
    }
    return mesh->face_count && mesh->face_count==le16(data+h+20);
}

bool brake_package_decode(const uint8_t *data, size_t size, BrakePackage *package)
{
    if (!package) return false;
    memset(package,0,sizeof(*package));
    if (!data || size!=BRAKE_SAMPLE_BYTES) return false;
    Chunk root;
    if (!find(data,0,size,0x80134000,&root)) return false;
    size_t position=root.start+8;
    while (position<root.end) {
        Chunk object;
        if (!next(data,&position,root.end,&object)) goto invalid;
        if (object.id!=0x80134010) continue;
        if (package->model_count>=BRAKE_MODELS || !decode_model(data,object,&package->models[package->model_count])) goto invalid;
        ++package->model_count;
    }
    if (package->model_count==BRAKE_MODELS) return true;
invalid:
    memset(package,0,sizeof(*package));
    return false;
}
