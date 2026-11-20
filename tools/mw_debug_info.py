#!/usr/bin/env python3
"""Read-only targeted ELF32 big-endian DWARF 1 queries. References are .debug offsets.
Original ELF/debug payload remains private; only selected query results are returned.
"""
import argparse
from dataclasses import dataclass
import json
import mmap
import struct

@dataclass(frozen=True)
class DIE:
    offset: int
    length: int
    tag: int
    attrs: dict
    @property
    def name(self): return self.attrs.get(3)
    @property
    def sibling(self): return self.attrs.get(1)
    @property
    def size(self): return self.attrs.get(11)

class DebugInfo:
    def __init__(self,path):
        self.file=open(path,'rb'); self.data=mmap.mmap(self.file.fileno(),0,access=mmap.ACCESS_READ)
        if self.data[:6]!=b'\x7fELF\x01\x02': raise ValueError('requires ELF32 big-endian')
        shoff=struct.unpack_from('>I',self.data,32)[0]
        entsize,count,index=struct.unpack_from('>HHH',self.data,46)
        hs=[struct.unpack_from('>10I',self.data,shoff+i*entsize) for i in range(count)]
        h=hs[index]; names=self.data[h[4]:h[4]+h[5]]; self.sections={}
        for h in hs:
            name=names[h[0]:].split(b'\0',1)[0].decode('ascii')
            self.sections[name]=dict(address=h[3],offset=h[4],size=h[5],link=h[6],entsize=h[9])
        self.debug=self.sections['.debug']; self._cache={}; self._names={}
    def close(self): self.data.close(); self.file.close()
    def __enter__(self): return self
    def __exit__(self,*args): self.close()
    def die(self,offset):
        if offset in self._cache: return self._cache[offset]
        if offset<0 or offset+6>self.debug['size']: raise ValueError('DIE out of range')
        base=self.debug['offset']; p=base+offset
        length,tag=struct.unpack_from('>IH',self.data,p); end=p+length
        if length<6 or end>base+self.debug['size']: raise ValueError('invalid DIE length')
        p+=6; attrs={}
        while p<end:
            if p+2>end: raise ValueError('truncated attribute')
            attr=struct.unpack_from('>H',self.data,p)[0]; p+=2; form=attr&15
            if form in (1,2,5,6,7):
                size={1:4,2:4,5:2,6:4,7:8}[form]
                if p+size>end: raise ValueError('truncated scalar')
                value=int.from_bytes(self.data[p:p+size],'big'); p+=size
            elif form in (3,4):
                size=2 if form==3 else 4
                if p+size>end: raise ValueError('truncated block size')
                n=int.from_bytes(self.data[p:p+size],'big'); p+=size
                if p+n>end: raise ValueError('truncated block')
                value=self.data[p:p+n]; p+=n
            elif form==8:
                stop=self.data.find(b'\0',p,end)
                if stop<0: raise ValueError('unterminated string')
                value=self.data[p:stop].decode('utf-8','replace'); p=stop+1
            else: raise ValueError('unsupported form %x at %x'%(form,offset))
            attrs[attr>>4]=value
        d=DIE(offset,length,tag,attrs); self._cache[offset]=d; return d
    def find(self,name,tags=None):
        if name not in self._names:
            pattern=b'\x00\x38'+name.encode()+b'\0'; start=self.debug['offset']; end=start+self.debug['size']; cursor=start; matches={}
            while True:
                found=self.data.find(pattern,cursor,end)
                if found<0: break
                rel=found-start
                for back in (12,6,*range(8,257,2)):
                    candidate=rel-back
                    if candidate<0: continue
                    try: d=self.die(candidate)
                    except (ValueError,struct.error): continue
                    if d.name==name and candidate+d.length>=rel+len(pattern): matches[d.offset]=d; break
                cursor=found+len(pattern)
            self._names[name]=list(matches.values())
        return [d for d in self._names[name] if tags is None or d.tag in tags]
    def children(self,entry):
        end=entry.sibling
        if end is None or end<=entry.offset+entry.length: return
        cursor=entry.offset+entry.length
        while cursor<end:
            if struct.unpack_from('>I',self.data,self.debug['offset']+cursor)[0]==4:
                cursor+=4; continue
            child=self.die(cursor); yield child
            nxt=child.sibling or cursor+child.length
            if nxt<=cursor or nxt>end: raise ValueError('invalid child sibling')
            cursor=nxt
    @staticmethod
    def member_offset(entry):
        raw=entry.attrs.get(2)
        if isinstance(raw,bytes) and len(raw) in (5,6) and raw[0]==4 and (len(raw)==5 or raw[5]==7): return int.from_bytes(raw[1:5],'big')
        return None
    def members(self,entry):
        return [dict(name=d.name,offset=self.member_offset(d),type=d.attrs.get(7),die_offset=d.offset,attrs=d.attrs) for d in self.children(entry) if d.tag==13]
    @staticmethod
    def enum_values(entry):
        raw=entry.attrs.get(15,b''); p=0; out=[]
        while p<len(raw):
            if p+4>len(raw): raise ValueError('truncated enum value')
            value=int.from_bytes(raw[p:p+4],'big'); p+=4; end=raw.find(b'\0',p)
            if end<0: raise ValueError('unterminated enum label')
            out.append((raw[p:end].decode('utf-8','replace'),value)); p=end+1
        return out
    def symbols(self,name=None):
        h=self.sections['.symtab']; s=self.sections['.strtab']; out=[]
        for p in range(h['offset'],h['offset']+h['size'],h['entsize']):
            sn,value,size,info,other,index=struct.unpack_from('>IIIBBH',self.data,p); at=s['offset']+sn; end=self.data.find(b'\0',at,s['offset']+s['size']); label=self.data[at:end].decode('utf-8','replace')
            if name is None or name in label: out.append(dict(name=label,address=value,size=size,type=info&15,section=index))
        return out

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('elf'); p.add_argument('name'); p.add_argument('--symbols',action='store_true'); a=p.parse_args()
    with DebugInfo(a.elf) as d:
        out=d.symbols(a.name) if a.symbols else [dict(offset=e.offset,tag=e.tag,name=e.name,size=e.size,members=d.members(e),enum=d.enum_values(e)) for e in d.find(a.name)]
        print(json.dumps(out,indent=2,default=lambda x:x.hex() if isinstance(x,bytes) else str(x)))
if __name__=='__main__': main()
