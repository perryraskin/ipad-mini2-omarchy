#!/usr/bin/env python3
"""Bounded Oscar IPC receive framing. No UART, power/reset or sensor commands.

Stock receive state8 at0x8401c00 interprets length0 as256 and rejects length<14;
checksum validation calls0x8403130. Payload/report meaning is deliberately opaque.
Unlike stock's diagnostic channel0xba substitution, corrupt frames are discarded.
"""
import importlib.util,pathlib,struct
spec=importlib.util.spec_from_file_location('oscar_packet',pathlib.Path(__file__).with_name('packet.py'))
packet=importlib.util.module_from_spec(spec);spec.loader.exec_module(packet)
class Receiver:
 def __init__(self):self.buffer=bytearray();self.bad_length=0;self.bad_checksum=0;self.discarded=0
 def feed(self,data):
  if not isinstance(data,bytes) or len(data)>4096:raise ValueError('Supply bytes in bounded chunks up to4096')
  result=[]
  # Process bytewise: even arbitrarily fragmented/noisy input retains <=256 bytes.
  for value in data:
   self.buffer.append(value)
   while self.buffer:
    start=self.buffer.find(b'ICPA')
    if start<0:
     keep=max((n for n in range(1,min(3,len(self.buffer))+1) if self.buffer[-n:]==b'ICPA'[:n]),default=0)
     self.discarded+=len(self.buffer)-keep
     if keep:self.buffer[:]=self.buffer[-keep:]
     else:self.buffer.clear()
     break
    if start:self.discarded+=start;del self.buffer[:start]
    if len(self.buffer)<6:break
    size=self.buffer[5] or 256
    if size<14:
     self.bad_length+=1;self.discarded+=1;del self.buffer[0];continue
    if len(self.buffer)<size:break
    frame=bytes(self.buffer[:size])
    if packet.checksum(frame):
     self.bad_checksum+=1;self.discarded+=1;del self.buffer[0];continue
    # Header bytes6..9 are preserved; outgoing encoder's zeros are not an RX rule.
    result.append({'channel':frame[4],'header':frame[6:10],'command':struct.unpack_from('<H',frame,12)[0],'payload':frame[14:],'frame':frame})
    del self.buffer[:size]
  return result
 def reset(self):
  self.discarded+=len(self.buffer);self.buffer.clear()
