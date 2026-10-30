#!/usr/bin/env python3
"""Preserve the verified J86 loader/DT/bootargs and replace its kernel stream."""
import argparse,gzip,hashlib,json,pathlib,zlib
root=pathlib.Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--profile',choices=['candidate','audio-candidate'],default='candidate');args=parser.parse_args()
out=root/('audio/build/candidate' if args.profile=='audio-candidate' else 'wifi/build/candidate')
old=(root/'assets/j86-ramboot.bin').read_bytes()
expected=json.loads((root/'assets/session-assets.json').read_text())['j86-ramboot.bin']
assert hashlib.sha256(old).hexdigest()==expected, 'Original payload checksum mismatch'
original=(root/'assets/kernel-4k-Image.initramfs').read_bytes()
matches=[]
pos=0
while True:
 pos=old.find(b'\x1f\x8b\x08',pos)
 if pos<0:break
 try:
  stream=zlib.decompressobj(31)
  raw=stream.decompress(old[pos:])+stream.flush()
  if raw==original:matches.append((pos,len(old)-len(stream.unused_data)))
 except zlib.error:pass
 pos+=1
assert len(matches)==1, 'Expected exactly one verified kernel gzip stream'
start,end=matches[0]
image=(out/'Image.initramfs').read_bytes()
assert image[56:60]==b'ARM\x64', 'Not an ARM64 Image'
payload=old[:start]+gzip.compress(image,compresslevel=9,mtime=0)+old[end:]
assert gzip.decompress(payload[start:])==image, 'Candidate kernel round-trip failed'
(out/'j86-ramboot.bin').write_bytes(payload)
print('Candidate J86 RAM payload:',len(payload),'bytes;',hashlib.sha256(payload).hexdigest())
print('Original loader, DT and bootargs preserved; no boot or asset activation performed.')
