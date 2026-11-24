"""Bounded data-only subset of MS-NRBF; never loads .NET classes or executes code."""
import base64
import struct


class Reader:
    def __init__(self,b):self.b,self.p,self.objects,self.meta=b,0,{},{}
    def take(self,n):
        if n<0 or self.p+n>len(self.b):raise ValueError('truncated NRBF')
        v=self.b[self.p:self.p+n];self.p+=n;return v
    def u8(self):return self.take(1)[0]
    def i32(self):return struct.unpack('<i',self.take(4))[0]
    def count(self):
        n=self.i32()
        if not 0<=n<=1000000:raise ValueError('NRBF count')
        return n
    def string(self):
        size,shift=0,0
        for _ in range(5):
            v=self.u8();size|=(v&127)<<shift
            if not v&128:return self.take(size).decode('utf-8')
            shift+=7
        raise ValueError('NRBF string length')
    def primitive(self,t):
        fmt={1:'?',2:'B',3:'H',6:'d',7:'h',8:'i',9:'q',10:'b',11:'f',12:'q',13:'Q',14:'H',15:'I',16:'Q'}
        if t in fmt:return struct.unpack('<'+fmt[t],self.take(struct.calcsize(fmt[t])))[0]
        if t in (5,18):return self.string()
        if t==17:return None
        raise ValueError(f'NRBF primitive {t}')
    def additional(self,t):
        if t in (0,7):return self.u8()
        if t==3:return self.string()
        if t==4:return (self.string(),self.i32())
        if t in (1,2,5,6):return None
        raise ValueError('NRBF member type')
    def value(self,t,info):return self.primitive(info) if t==0 else self.record()
    def class_values(self,oid,meta):
        name,fields,types,infos=meta;obj={'__class__':name};self.objects[oid]=obj
        for field,t,info in zip(fields,types,infos):obj[field]=self.value(t,info)
        return obj
    def record(self):
        typ=self.u8()
        if typ==0:
            root,header,major,minor=struct.unpack('<iiii',self.take(16))
            if (major,minor)!=(1,0):raise ValueError('NRBF version')
            self.root=root;return None
        if typ==12:
            self.i32();self.string();return self.record()
        if typ in (4,5):
            oid=self.i32();name=self.string();n=self.count();fields=[self.string() for _ in range(n)]
            types=list(self.take(n));infos=[self.additional(t) for t in types]
            if typ==5:self.i32()
            meta=(name,fields,types,infos);self.meta[oid]=meta
            return self.class_values(oid,meta)
        if typ==1:
            oid,mid=self.i32(),self.i32();return self.class_values(oid,self.meta[mid])
        if typ==6:
            oid=self.i32();v=self.string();self.objects[oid]=v;return v
        if typ==8:return self.primitive(self.u8())
        if typ==9:return {'__ref__':self.i32()}
        if typ==10:return None
        if typ in (13,14):return {'__nulls__':self.u8() if typ==13 else self.count()}
        if typ==11:return {'__end__':True}
        if typ in (15,16,17,7):
            oid=self.i32()
            if typ==7:
                arraytype=self.u8();rank=self.count();dims=[self.count() for _ in range(rank)]
                if arraytype>=3:[self.i32() for _ in range(rank)]
                total=1
                for n in dims:total*=n
                if total>1000000:raise ValueError('NRBF array size')
                t=self.u8();info=self.additional(t)
            else:
                total=self.count();t=0 if typ==15 else 2;info=self.u8() if typ==15 else None
            arr=[];self.objects[oid]=arr
            while len(arr)<total:
                v=self.value(t,info)
                if isinstance(v,dict) and '__nulls__' in v:arr.extend([None]*v['__nulls__'])
                else:arr.append(v)
            if len(arr)!=total:raise ValueError('NRBF array length')
            return arr
        raise ValueError(f'NRBF record {typ}')
    def resolve(self,v,seen=None):
        if isinstance(v,dict):
            if '__ref__' in v:
                oid=v['__ref__'];seen=set() if seen is None else seen
                if oid in seen:return {'__cycle__':oid}
                return self.resolve(self.objects[oid],seen|{oid})
            return {k:self.resolve(x,seen) for k,x in v.items()}
        if isinstance(v,list):return [self.resolve(x,seen) for x in v]
        return v


def decode(b):
    if not b.startswith(b'Binary'):raise ValueError('not AC Binary save')
    b=b[6:].split(b'||',1)[0].rstrip(b'\0\r\n ')
    r=Reader(base64.b64decode(b,validate=True));r.record()
    while True:
        v=r.record()
        if isinstance(v,dict) and '__end__' in v:break
    if any(r.b[r.p:]):raise ValueError('NRBF nonzero residual bytes')
    return r.resolve(r.objects[r.root])
