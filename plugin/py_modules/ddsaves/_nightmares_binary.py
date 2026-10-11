"""Bounded stdlib decoding of real Atlas/Helios custom save containers."""
import struct
from ddsaves import gvas


class Cursor:
    def __init__(self,b,p=0):self.b,self.p=b,p
    def take(self,n):
        if n<0 or self.p+n>len(self.b):raise ValueError('truncated save')
        out=self.b[self.p:self.p+n];self.p+=n;return out
    def i32(self):return struct.unpack('<i',self.take(4))[0]
    def count(self,maximum=100000):
        n=self.i32()
        if not 0<=n<=maximum:raise ValueError('invalid count')
        return n
    def fstr(self):
        n=self.i32()
        if not -1000000<n<1000000:raise ValueError('invalid FString size')
        if not n:return ''
        size=abs(n)*(2 if n<0 else 1);raw=self.take(size);term=2 if n<0 else 1
        if raw[-term:]!=b'\0'*term:raise ValueError('FString terminator')
        return raw[:-term].decode('utf-16-le' if n<0 else 'utf-8')


def header(b):
    r=Cursor(b)
    if r.take(4)!=b'GVAS' or r.i32()!=2:raise ValueError('unsupported GVAS')
    r.i32();r.take(10);r.fstr()
    if r.i32()!=3:raise ValueError('custom version format')
    r.take(r.count(1000)*20)
    cls=r.fstr()
    return cls,r


def atlas_meta(b):
    cls,r=header(b)
    if cls!='AtlasMetaState' or r.fstr()!='None' or r.i32()!=0:
        raise ValueError('not AtlasMetaState')
    out={}
    for _ in range(r.count(1000)):
        key=r.fstr()
        if key in out:raise ValueError('duplicate meta field')
        out[key]=[r.fstr() for _ in range(r.count(100000))]
    if r.p!=len(b):raise ValueError('Atlas meta residual bytes')
    return out


def chalk_value(kind,raw):
    if kind in (2,14) and len(raw)==4:return struct.unpack('<i',raw)[0]
    if kind==1 and len(raw)==1:return bool(raw[0])
    if kind==10 and len(raw)==4:return struct.unpack('<f',raw)[0]
    if kind==19:
        r=Cursor(raw);text=r.fstr()
        # Serialized strings may carry extra bytes inside the length-delimited value.
        return {'text':text,'residual_hex':raw[r.p:].hex()}
    if kind==64:
        r=Cursor(raw)
        try:
            cls=r.fstr()
            if cls.endswith('.DateTime') and r.i32()==8:
                ticks=struct.unpack('<q',r.take(8))[0]
                if r.p==len(raw):return ticks
                if len(raw)-r.p==4 and r.i32()==1:return ticks
        except (ValueError,UnicodeError,struct.error):pass
    return {'raw_type':kind,'raw_hex':raw.hex()}


def helios(b):
    cls,r=header(b)
    if cls!='/Script/Helios.HeliosSave':raise ValueError('not real HeliosSave')
    props=gvas.Reader(b);props.p=r.p;root=props.props();r.p=props.p
    if r.i32()!=0:raise ValueError('unexpected root GUID')
    out={}
    for _ in range(r.count(10000)):
        owner=r.fstr();proxies={}
        for _ in range(r.count(10000)):
            name=r.fstr()
            if r.i32()!=0:raise ValueError('unknown Chalkboard version')
            records={}
            for _ in range(r.count(100000)):
                key=r.fstr();kind=r.i32();size=r.count(16000000)
                if key in records:raise ValueError('duplicate Chalkboard key')
                records[key]=chalk_value(kind,r.take(size))
            proxies[name]=records
        out[owner]=proxies
    if r.p!=len(b):raise ValueError('Helios residual bytes')
    return {'root':root,'managers':out}
