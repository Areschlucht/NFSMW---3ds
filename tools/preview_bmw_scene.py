#!/usr/bin/env python3
"""Host reference render for the converted BMW scene; not a 3DS screenshot."""
import argparse
import json
import math
import struct
import zlib
from pathlib import Path
import numpy as np
from PIL import Image


def render(folder,yaw=0.65,pitch=-0.25,width=768,height=480):
    data=(folder/'body.nfm').read_bytes()
    magic,version,nv,nb,nt,size,crc,reserved=struct.unpack_from('<4s7I',data)
    assert magic==b'NFM1' and version==1 and len(data)==size+32 and zlib.crc32(data[32:])==crc
    pos=32;texinfo=[struct.unpack_from('<4I',data,pos+i*16) for i in range(nt)];pos+=nt*16
    batches=[struct.unpack_from('<4I',data,pos+i*16) for i in range(nb)];pos+=nb*16
    v=np.frombuffer(data,dtype='<f4',count=nv*8,offset=pos).reshape(nv,8).astype(np.float64)
    assert pos+nv*32==len(data) and np.isfinite(v).all()
    textures=[np.asarray(Image.open(folder/'textures'/f'{t[0]:08x}.png').convert('RGBA'),dtype=np.float64) for t in texinfo]
    cy,sy,cp,sp=math.cos(yaw),math.sin(yaw),math.cos(pitch),math.sin(pitch)
    rotation=np.array([[cy,0,sy],[sp*sy,cp,-sp*cy],[-cp*sy,sp,cp*cy]])
    view=v[:,:3]@rotation.T;normals=v[:,3:6]@rotation.T
    depth=3.4+view[:,2];focal=height/(2*math.tan(math.radians(40)/2))
    screen=np.column_stack((width/2+view[:,0]*focal/depth,height/2-view[:,1]*focal/depth))
    output=np.full((height,width,3),20.0);zbuf=np.zeros((height,width));triangles=[]
    for first,count,texture,_ in batches:
        assert first+count<=nv and count%3==0 and texture<nt
        for start in range(first,first+count,3):triangles.append((start,texture))
    opaque=[t for t in triangles if not texinfo[t[1]][3]&1]
    transparent=[t for t in triangles if texinfo[t[1]][3]&1]
    transparent.sort(key=lambda t:float(depth[t[0]:t[0]+3].mean()),reverse=True)
    for start,texid in opaque+transparent:
        s=screen[start:start+3];d=depth[start:start+3]
        x0=max(0,int(np.floor(s[:,0].min())));x1=min(width-1,int(np.ceil(s[:,0].max())))
        y0=max(0,int(np.floor(s[:,1].min())));y1=min(height-1,int(np.ceil(s[:,1].max())))
        if x0>x1 or y0>y1:continue
        ax,ay=s[0];bx,by=s[1];cx,cy=s[2]
        area=(bx-ax)*(cy-ay)-(by-ay)*(cx-ax)
        if abs(area)<1e-8:continue
        yy,xx=np.mgrid[y0:y1+1,x0:x1+1];xx=xx+0.5;yy=yy+0.5
        w0=((bx-xx)*(cy-yy)-(by-yy)*(cx-xx))/area
        w1=((cx-xx)*(ay-yy)-(cy-yy)*(ax-xx))/area;w2=1-w0-w1
        inv=w0/d[0]+w1/d[1]+w2/d[2]
        mask=(w0>=0)&(w1>=0)&(w2>=0)&(inv>zbuf[y0:y1+1,x0:x1+1])
        if not mask.any():continue
        uv=v[start:start+3,6:8]
        u=(w0*uv[0,0]/d[0]+w1*uv[1,0]/d[1]+w2*uv[2,0]/d[2])/inv
        vv=(w0*uv[0,1]/d[0]+w1*uv[1,1]/d[1]+w2*uv[2,1]/d[2])/inv
        image=textures[texid];th,tw=image.shape[:2]
        samples=image[(np.mod(vv,1)*th).astype(int)%th,(np.mod(u,1)*tw).astype(int)%tw]
        alpha=samples[:,:,3]/255;mask&=alpha>0
        light=0.35+0.65*abs(float(normals[start]@np.array([0.3,0.5,-0.8124038])))
        color=samples[:,:,:3]*min(1,light)
        patch=output[y0:y1+1,x0:x1+1]
        patch[mask]=(color*alpha[:,:,None]+patch*(1-alpha[:,:,None]))[mask]
        if not texinfo[texid][3]&1:zbuf[y0:y1+1,x0:x1+1][mask]=inv[mask]
    return Image.fromarray(np.clip(output,0,255).astype(np.uint8))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('scene',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();render(args.scene).save(args.output)
