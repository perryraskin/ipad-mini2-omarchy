#!/usr/bin/env python3
"""Recover the pinned public initramfs gzip stream from the verified Image."""
import hashlib,pathlib,zlib
r=pathlib.Path(__file__).resolve().parents[2]
b=(r/'assets/kernel-4k-Image.initramfs').read_bytes()
expected='a74c1699c9eace242774e27f72072a996665cb5596fde4b3fa9a976b4250dbc2'
o=0
while True:
 o=b.find(b'\x1f\x8b\x08',o)
 if o<0:raise SystemExit('Pinned initramfs not found')
 try:
  d=zlib.decompressobj(31);raw=d.decompress(b[o:]);raw+=d.flush()
  n=len(b)-o-len(d.unused_data);gz=b[o:o+n]
  if raw.startswith(b'070701') and hashlib.sha256(gz).hexdigest()==expected:
   (r/'wifi/build/original-initramfs.cpio.gz').write_bytes(gz)
   (r/'wifi/build/original-initramfs.cpio').write_bytes(raw)
   print('Pinned initramfs recovered',n,len(raw));break
 except zlib.error:pass
 o+=1
p=0
while p+110<=len(raw):
 h=raw[p:p+110]
 if h[:6]!=b'070701':break
 v=[int(h[6+i*8:14+i*8],16)for i in range(13)];size=v[6];namesize=v[11]
 name=raw[p+110:p+110+namesize-1].decode();start=(p+110+namesize+3)&~3
 print(name,size);p=(start+size+3)&~3
 if name=='TRAILER!!!':break
