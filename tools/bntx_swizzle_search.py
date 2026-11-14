import sys, itertools, struct
sys.path.insert(0,'tools')
import numpy as np
from bntx_probe import load, textures
from bntx_decode import bc4_block
from PIL import Image

b = load(r'F:\switch2\Longshot\romfs\UI\Layout2Archive\Common.Product.100.Nin_Ounce_NVN2.bntx.zs')
def get(name):
    t=[t for t in textures(b) if t[0]==name][0]
    o=t[-1]; mip0=struct.unpack_from('<Q',b,o+0x70)[0]; off=struct.unpack_from('<Q',b,mip0)[0]
    return t, b[off:off+t[7]]
t,data = get('Circle64_00')
w,h = t[2],t[3]; wb,hb = w//4,h//4; pitch=wb*8; bh=4; gobs_x=(pitch+63)//64
def desw(perm):
    out=bytearray(pitch*hb)
    for y in range(hb):
        for x in range(pitch):
            gob=(y//(8*bh))*512*bh*gobs_x+(x//64)*512*bh+((y%(8*bh))//8)*512
            v={'x4':(x%32)//16,'x5':(x%64)//32,'y0':y%2,'y1':(y%8)//2%2,'y2':(y%8)//4}
            a=gob+(x%16)
            for i,k in enumerate(perm): a+=v[k]<<(4+i)
            out[y*pitch+x]=data[a] if a<len(data) else 0
    return bytes(out)
def tv(raw):
    img=np.zeros((h,w),dtype=np.int32)
    for by in range(hb):
        for bx in range(wb):
            blk=bc4_block(raw[(by*wb+bx)*8:(by*wb+bx)*8+8])
            for i in range(16): img[by*4+i//4,bx*4+i%4]=blk[i]
    return int(np.abs(np.diff(img,axis=0)).sum()+np.abs(np.diff(img,axis=1)).sum()), img
best=[]
for perm in itertools.permutations(['x4','x5','y0','y1','y2']):
    s,img=tv(desw(perm)); best.append((s,perm))
best.sort(); print(best[:5])
s,img=tv(desw(best[0][1])); Image.fromarray(img.astype('uint8')).save('build/circle_fixed.png')
