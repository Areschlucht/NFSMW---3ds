"""Choose a supported free-drive spawn on the original navigation centerline."""
import math


class RoadSampler:
    def __init__(self, triangles):
        self.rows=[]
        for p in triangles:
            a,b,c=p;ax,az=b[0]-a[0],b[2]-a[2];bx,bz=c[0]-a[0],c[2]-a[2]
            denominator=ax*bz-az*bx
            if abs(denominator)<1e-6:continue
            self.rows.append((min(v[0] for v in p),max(v[0] for v in p),min(v[2] for v in p),max(v[2] for v in p),a,ax,az,b[1]-a[1],bx,bz,c[1]-a[1],denominator))

    def height(self,x,z,reference):
        result=None;best=2
        for lowx,highx,lowz,highz,p,ax,az,ay,bx,bz,by,den in self.rows:
            if x<lowx-.001 or x>highx+.001 or z<lowz-.001 or z>highz+.001:continue
            dx,dz=x-p[0],z-p[2];a=(dx*bz-dz*bx)/den;b=(ax*dz-az*dx)/den
            if a<-.00001 or b<-.00001 or a+b>1.00001:continue
            y=p[1]+a*ay+b*by;distance=abs(y-reference)
            if distance<best:result=y;best=distance
        return result

    def run(self,point,heading):
        y=point[1]
        for distance in range(1,161):
            y=self.height(point[0]+math.sin(heading)*distance,point[2]+math.cos(heading)*distance,y)
            if y is None:return distance-1
        return 160


def choose_spawn(reference,network,triangles):
    sampler=RoadSampler(triangles);nodes=[(n[2],n[1],n[0]) for n in network['nodes']];candidates=[]
    for index,(a,b) in enumerate(network['segments']):
        a,b=nodes[a],nodes[b];u=[b[i]-a[i] for i in range(3)];length=sum(v*v for v in u)
        if length<1e-6:continue
        t=max(0,min(1,sum((reference[i]-a[i])*u[i] for i in range(3))/length))
        point=[a[i]+t*u[i] for i in range(3)];distance=sum((point[i]-reference[i])**2 for i in range(3))
        if distance<=25*25:candidates.append((distance,index,point,math.atan2(u[0],u[2])))
    for distance,index,point,heading in sorted(candidates):
        y=sampler.height(point[0],point[2],point[1])
        if y is None or abs(y-point[1])>.5:continue
        point=[point[0],y,point[2]];supported=True
        for x,z in ((1.35,.8),(1.35,-.8),(-1.35,.8),(-1.35,-.8)):
            if sampler.height(point[0]+math.sin(heading)*x-math.cos(heading)*z,
                              point[2]+math.cos(heading)*x+math.sin(heading)*z,y) is None:supported=False;break
        if not supported:continue
        forward=sampler.run(point,heading);reverse=sampler.run(point,heading+math.pi)
        if reverse>forward+5:heading=(heading+math.pi)%(2*math.pi)
        return point,heading,dict(method='Projected onto original navigation segment, checked against original road triangles',
                                 segment=index,offset_from_old_spawn_m=math.sqrt(distance),
                                 forward_run_m=forward,reverse_run_m=reverse)
    raise ValueError('No supported original navigation centerline near the starting area')
