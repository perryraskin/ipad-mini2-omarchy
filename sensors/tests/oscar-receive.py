#!/usr/bin/env python3
import importlib.util,pathlib,random,struct
spec=importlib.util.spec_from_file_location('rx',pathlib.Path(__file__).resolve().parents[1]/'oscar/receive.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def frame(size):
 b=bytearray(b'ICPA'+bytes([17,size%256])+b'\x11\x22\x33\x44'+bytes(size-10))
 struct.pack_into('<H',b,12,0x1234);struct.pack_into('<H',b,10,m.packet.checksum(b));return bytes(b)
for size in (14,15,127,128,129,255,256):
 b=frame(size)
 for split in range(size+1):
  r=m.Receiver();out=r.feed(b[:split])+r.feed(b[split:]);assert len(out)==1 and out[0]['frame']==b
  assert out[0]['header']==b'\x11\x22\x33\x44' and not r.buffer
r=m.Receiver();b=frame(256);bad=bytearray(frame(14));bad[-1]^=1
out=r.feed(b'noiseIC'+b'PA\x03\x06'+bytes(bad)+b)
assert len(out)==1 and out[0]['frame']==b and r.bad_length and r.bad_checksum
rng=random.Random(86)
for _ in range(100):
 r.feed(bytes(rng.randrange(256) for _ in range(4096)));assert len(r.buffer)<=256
r.reset();assert not r.buffer
try:r.feed(bytes(4097))
except ValueError:pass
else:raise AssertionError('Unbounded chunk accepted')
print('Oscar RX: all split points, 256-byte frames, corruption recovery and bounded noise passed')
