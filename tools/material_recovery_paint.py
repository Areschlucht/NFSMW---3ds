#!/usr/bin/env python3
"""Evidence-backed original GC paint-word packing and vinyl recolor subset.

Original802E1B64 packs BASE_PAINT RED/GREEN/BLUE/GLOSS as low-to-high bytes.
Original802E0A84 derives three source-channel weights, then802E0890 mixes
native words. Numeric words here preserve the original ABI; they are not a PNG
RGBA interface. No canonical BMW paint palette or final skin is selected.
"""
import hashlib
import math
import struct
from material_recovery_vehicle import DOL_SHA256, uint32


def f32(value):
    return struct.unpack('>f',struct.pack('>f',value))[0]


def pack_paint_word(red, green, blue, gloss):
    values=(red,green,blue,gloss)
    if any(not isinstance(v,int) or not 0<=v<=255 for v in values):
        raise ValueError('Paint attribute components must be unsigned bytes')
    return sum(v<<(8*i) for i,v in enumerate(values))


def remap_word(source_word, palette_words):
    """Transcribe802E0A84→802E0890 for three palette words.

    The original multiplies/truncates each weighted component separately,
    saturates the sums, and takes the maximum for the last native-memory byte.
    Keep original numeric/native-byte ordering until the platform pixel adapter
    is recovered; this is deliberately not an ordinary RGBA blend function.
    """
    uint32(source_word)
    if len(palette_words)!=3:
        raise ValueError('Original remap consumes three palette words')
    for word in palette_words:uint32(word)
    scale=f32(1/255)
    weights=[f32(f32((source_word>>(8*i))&255)*scale) for i in range(3)]
    out=[0,0,0,0]
    for word,weight in zip(palette_words,weights):
        if weight<=0:continue
        components=word.to_bytes(4,'big')
        terms=[math.trunc(f32(weight*f32(v))) for v in components]
        for i in range(3):out[i]+=terms[i]
        out[3]=max(out[3],terms[3]&255)
    return int.from_bytes(bytes(min(255,v) for v in out),'big')


def original_remap_word(image, source_word, palette_words):
    """Bounded checksum-pinned scalar PPC reference, never native execution."""
    if hashlib.sha256(image.data).hexdigest()!=DOL_SHA256:
        raise ValueError('Original paint reference requires pinned USA DOL')
    remap_word(source_word,palette_words)
    from unicorn import Uc,UC_ARCH_PPC,UC_MODE_PPC32,UC_MODE_BIG_ENDIAN
    from unicorn.ppc_const import UC_PPC_REG_1,UC_PPC_REG_3,UC_PPC_REG_4,UC_PPC_REG_LR,UC_PPC_REG_PC,UC_PPC_REG_MSR
    uc=Uc(UC_ARCH_PPC,UC_MODE_PPC32|UC_MODE_BIG_ENDIAN)
    palette,stack,stop=0x90000000,0x91000000,0xa0000000
    for va,size in ((0x802e0000,0x1000),(0x8040c000,0x1000),(palette,0x1000),(stack,0x2000),(stop,0x1000)):
        uc.mem_map(va,size)
    image.file_offset(0x802e0890,0x2c4,executable=True)
    uc.mem_write(0x802e0890,image.read(0x802e0890,0x2c4))
    uc.mem_write(0x8040cc00,image.read(0x8040cc00,0x60))
    uc.mem_write(palette,struct.pack('>3I',*palette_words))
    uc.reg_write(UC_PPC_REG_1,stack+0x1000);uc.reg_write(UC_PPC_REG_3,source_word)
    uc.reg_write(UC_PPC_REG_4,palette);uc.reg_write(UC_PPC_REG_LR,stop)
    uc.reg_write(UC_PPC_REG_MSR,0x2000)
    uc.emu_start(0x802e0a84,stop,timeout=100000,count=8192)
    if uc.reg_read(UC_PPC_REG_PC)!=stop:
        raise ValueError('Original remap did not return within its bound')
    return uc.reg_read(UC_PPC_REG_3)&0xffffffff


def masked_word(base_word, source_word, mask):
    """Original802E128C..1310 mask blend, retaining all four native bytes.

    The mask is a separate grayscale value, not the source texture alpha.
    Values>=128 select source. Lower values use mask/128 and truncate each
    weighted component before adding. Original GLOSS stays in its own byte.
    """
    uint32(base_word);uint32(source_word)
    if not isinstance(mask,int) or not 0<=mask<=255:
        raise ValueError('Expected original unsigned mask byte')
    if mask>=128:return source_word
    if mask==0:return base_word
    result=0
    for shift in range(0,32,8):
        a=(base_word>>shift)&255;b=(source_word>>shift)&255
        result|=((a*(128-mask))//128+(b*mask)//128)<<shift
    return result


def original_masked_word(image,base_word,source_word,mask):
    """Execute the original partial-mask preparation and blend on scalar PPC.

    Covers masks0..127 in original802E12B4..1314→802E0890. The full-source
    branch for128..255 is a direct assignment proven at802E128C..1298.
    """
    if hashlib.sha256(image.data).hexdigest()!=DOL_SHA256:
        raise ValueError('Original paint reference requires pinned USA DOL')
    masked_word(base_word,source_word,mask)
    if mask>=128:raise ValueError('Reference region is the partial-mask branch')
    from unicorn import Uc,UC_ARCH_PPC,UC_MODE_PPC32,UC_MODE_BIG_ENDIAN
    from unicorn.ppc_const import UC_PPC_REG_0,UC_PPC_REG_1,UC_PPC_REG_22,UC_PPC_REG_23,UC_PPC_REG_24,UC_PPC_REG_31,UC_PPC_REG_3,UC_PPC_REG_PC,UC_PPC_REG_MSR,UC_PPC_REG_FPR30,UC_PPC_REG_FPR31
    uc=Uc(UC_ARCH_PPC,UC_MODE_PPC32|UC_MODE_BIG_ENDIAN);stack=0x91000000
    for va,size in ((0x802e0000,0x2000),(0x8040c000,0x1000),(stack,0x2000)):
        uc.mem_map(va,size)
    for va,size in ((0x802e0890,0x1f4),(0x802e12b4,0x60)):
        image.file_offset(va,size,executable=True);uc.mem_write(va,image.read(va,size))
    uc.mem_write(0x8040cc00,image.read(0x8040cc00,0xe0))
    sp=stack+0x1000
    for reg,value in ((UC_PPC_REG_1,sp),(UC_PPC_REG_0,source_word),(UC_PPC_REG_22,base_word),
                      (UC_PPC_REG_23,sp+0x38),(UC_PPC_REG_24,sp+0x40),(UC_PPC_REG_31,mask)):
        uc.reg_write(reg,value)
    uc.reg_write(UC_PPC_REG_FPR31,struct.unpack('>Q',image.read(0x8040ccc8,8))[0])
    uc.reg_write(UC_PPC_REG_FPR30,struct.unpack('>Q',struct.pack('>d',image.f32(0x8040ccd0)))[0])
    uc.reg_write(UC_PPC_REG_MSR,0x2000)
    uc.emu_start(0x802e12b4,0x802e1314,timeout=100000,count=8192)
    if uc.reg_read(UC_PPC_REG_PC)!=0x802e1314:raise ValueError('Original mask blend exceeded bounds')
    return uc.reg_read(UC_PPC_REG_3)&0xffffffff


def rgb5a3_cpu_word(value):
    """Original8026C080 expansion into a CPU numeric ABGR word.

    Unlike display expansion, it shifts bitfields without bit replication.
    """
    if not isinstance(value,int) or not 0<=value<=65535:raise ValueError('Expected native RGB5A3 halfword')
    if value&0x8000:
        return pack_paint_word(((value>>10)&31)<<3,((value>>5)&31)<<3,(value&31)<<3,255)
    return pack_paint_word(((value>>8)&15)<<4,((value>>4)&15)<<4,(value&15)<<4,((value>>12)&7)<<5)


def cpu_word_rgb5a3(word):
    """Original8026C130 conversion back into a native GX palette halfword."""
    uint32(word);r=word&255;g=(word>>8)&255;b=(word>>16)&255;a=word>>24
    if a>239:return 0x8000|((r>>3)<<10)|((g>>3)<<5)|(b>>3)
    return ((a>>5)<<12)|((r>>4)<<8)|((g>>4)<<4)|(b>>4)


def original_palette_words(image,values,*,encode=False):
    """Execute unmodified original256-entry native palette conversion loop.

    Entry is after allocation/prologue and exit before cleanup. No allocator,
    external calls or unsupported Gekko instructions are executed or replaced.
    """
    if hashlib.sha256(image.data).hexdigest()!=DOL_SHA256:raise ValueError('Palette reference needs pinned USA DOL')
    if len(values)!=256:raise ValueError('Original palette loop processes256 entries')
    for v in values:
        cpu_word_rgb5a3(v) if encode else rgb5a3_cpu_word(v)
    from unicorn import Uc,UC_ARCH_PPC,UC_MODE_PPC32,UC_MODE_BIG_ENDIAN
    from unicorn.ppc_const import UC_PPC_REG_3,UC_PPC_REG_4,UC_PPC_REG_6,UC_PPC_REG_31,UC_PPC_REG_PC
    uc=Uc(UC_ARCH_PPC,UC_MODE_PPC32|UC_MODE_BIG_ENDIAN)
    for va,size in ((0x8026c000,0x1000),(0x90000000,0x4000)):uc.mem_map(va,size)
    uc.mem_write(0x8026c080,image.read(0x8026c080,0x144))
    if encode:
        uc.mem_write(0x90001000,struct.pack('>256I',*values));uc.mem_write(0x90002074,struct.pack('>I',0x90000000))
        uc.reg_write(UC_PPC_REG_3,0x90002000);uc.reg_write(UC_PPC_REG_4,0x90001000)
        start,stop=0x8026c144,0x8026c1c0;output_fmt='>256H'
    else:
        uc.mem_write(0x90000000,struct.pack('>256H',*values));uc.reg_write(UC_PPC_REG_31,0x90000000)
        uc.reg_write(UC_PPC_REG_6,0x90001000)
        start,stop=0x8026c0b4,0x8026c11c;output_fmt='>256I'
    uc.emu_start(start,stop,timeout=100000,count=20000)
    if uc.reg_read(UC_PPC_REG_PC)!=stop:raise ValueError('Original palette loop exceeded bounds')
    return list(struct.unpack(output_fmt,uc.mem_read(0x90000000 if encode else 0x90001000,struct.calcsize(output_fmt))))
