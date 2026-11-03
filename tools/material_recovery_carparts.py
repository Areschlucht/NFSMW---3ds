#!/usr/bin/env python3
"""Read the observed MW GC car-parts database container80034602/version6.

Original loader802D94F0..802D9A68; name802D9DD8, attribute802D9B14.
Preserves rawpart category/flags and field offsets; names do not establish units.
"""
import hashlib
import struct
from nfs_rockport import chunks
from material_recovery_vehicle import texture_hash


class CarParts:
    def __init__(self,data):
        self.data=bytes(data);self.sha256=hashlib.sha256(self.data).hexdigest()
        containers=[(s,e) for k,s,e in chunks(self.data) if k==0x80034602]
        if len(containers)!=1:raise ValueError('Expected one original car-parts container')
        start,end=containers[0]
        self.tables={}
        for k,s,e in chunks(self.data[start:end]):
            if k in self.tables:raise ValueError('Duplicate car-parts child')
            self.tables[k]=(start+s,start+e)
        expected={0x34603,0x34606,0x3460c,0x34605,0x3460a,0x3460b,0x34604}
        if set(self.tables)!=expected:raise ValueError('Unknown car-parts child schema')
        a,b=self.tables[0x34603]
        if b-a!=60:raise ValueError('Original car-parts header size mismatch')
        h=struct.unpack_from('<15I',self.data,a)
        if h[2]!=6:raise ValueError('Unknown car-parts database version')
        self.count=h[14];self.attributes_count=h[8]
        for tag,count,size in ((0x34605,h[8],8),(0x3460a,h[12],24),(0x3460b,h[10],4),(0x34604,self.count,14)):
            a,b=self.tables[tag]
            if not count*size<=b-a<=count*size+3 or any(self.data[a+count*size:b]):
                raise ValueError('Car-parts table count/bounds mismatch')
        self.parts={}
        a,b=self.tables[0x34604]
        for i in range(self.count):
            off=a+i*14;key=struct.unpack_from('<I',self.data,off)[0]
            self.parts.setdefault(key,[]).append(off)

    def text(self,index):
        a,b=self.tables[0x34606];start=a+index*4
        if not a<=start<b:raise ValueError('Car-parts string exceeds table')
        end=self.data.find(b'\0',start,b)
        if end<0:raise ValueError('Unterminated car-parts string')
        return self.data[start:end].decode('ascii')

    def part(self,key):
        offsets=self.parts.get(key,[])
        if len(offsets)!=1:raise ValueError('Selected car part is missing or ambiguous')
        at=offsets[0];name_index,group_index=struct.unpack_from('<2H',self.data,at+8)
        fields={};g,h=self.tables[0x3460c]
        if group_index!=0xffff:
            group=g+group_index*2
            if not g<=group<=h-2:raise ValueError('Attribute group exceeds table')
            n=struct.unpack_from('<H',self.data,group)[0]
            if group+2+2*n>h:raise ValueError('Attribute group count exceeds table')
            a,b=self.tables[0x34605]
            for i in range(n):
                index=struct.unpack_from('<H',self.data,group+2+2*i)[0]
                if index>=self.attributes_count:raise ValueError('Attribute index exceeds table')
                off=a+index*8;k,v=struct.unpack_from('<2I',self.data,off)
                if k in fields:raise ValueError('Ambiguous duplicate selected attribute')
                fields[k]=dict(value=v,file_offset=off,original_bytes=self.data[off:off+8].hex())
        return dict(key=f'{key:08x}',name=self.text(name_index),file_offset=at,
                    raw_record=self.data[at:at+14].hex(),fields=fields)

    def value(self,part,name,*,text=False,default=None):
        field=part['fields'].get(texture_hash(name))
        if field is None:return default
        return self.text(field['value']) if text else field['value']
