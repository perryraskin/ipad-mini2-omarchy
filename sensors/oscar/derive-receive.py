#!/usr/bin/env python3
"""Validate Oscar receive framing against exact stock code, in emulator RAM only.

Stops before the stock receive queue/consumer boundary. Does not implement sensor reporting,
UART initialization, Oscar firmware boot or automatic rotation.
"""
import argparse,hashlib,importlib.util,pathlib,random,struct
from unicorn import Uc,UcError,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3,UC_ARM64_REG_X4,UC_ARM64_REG_X5,UC_ARM64_REG_X6,UC_ARM64_REG_X7,UC_ARM64_REG_X22,UC_ARM64_REG_X30,UC_ARM64_REG_SP,UC_ARM64_REG_PC
ROOT=pathlib.Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('kernelcache',type=pathlib.Path);args=p.parse_args()
assert hashlib.sha256(args.kernelcache.read_bytes()).hexdigest()=='d173a651d02329a02d2f23c2859e1e54308a5e94da86ba729777efeb3503da08'
def helper(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
_,segments,data=helper('prelink',ROOT/'research/read-prelink.py').prelink(args.kernelcache)
packet=helper('packet',ROOT/'sensors/oscar/packet.py')
R=[UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3,UC_ARM64_REG_X4,UC_ARM64_REG_X5,UC_ARM64_REG_X6,UC_ARM64_REG_X7]
HEAP=0x10000000;STACK=0x20000000;FAKE=0x30000000;MMIO=0x40000000;STOP=0x50000000
uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
# Relocate the complete cache to low32 bits. Relative A64 code stays valid;
# canonicalize only real in-cache data pointers (including stripped PAC bits).
for name,va,vs,fo,fs in segments:
 if not vs:continue
 base=va&0xffffffff;lo=base&~4095;end=(base+vs+4095)&~4095
 try:uc.mem_map(lo,end-lo)
 except UcError:pass
 blob=bytearray(data[fo:fo+fs])
 if name not in ('__TEXT_EXEC',):
  for n in range(0,len(blob)-7,8):
   value=struct.unpack_from('<Q',blob,n)[0];canonical=value|0xffff000000000000
   if any(v<=canonical<v+size for _,v,size,_,_ in segments if size):struct.pack_into('<Q',blob,n,value&0xffffffff)
 if blob:uc.mem_write(base,bytes(blob))
for base,size in [(HEAP,0x100000),(STACK,0x100000),(FAKE,0x100000),(MMIO,0x10000),(STOP,0x1000)]:uc.mem_map(base,size)
# Enter stock receive state8 after magic synchronization, in emulator memory.
# Stop before queuing an incoming packet or invoking any consumer callback.
from unicorn.arm64_const import UC_ARM64_REG_X19,UC_ARM64_REG_X20,UC_ARM64_REG_X24
obj=HEAP;buf=HEAP+0x1000;observed=None
def code(mu,address,size,user):
 global observed
 if address==0x8401f08:
  observed=('queued',bytes(mu.mem_read(buf+0x20,current_length)));mu.emu_stop();return
 if address==0x8401ff8:
  observed=('bad-length',None);mu.emu_stop();return
 if address==0x83f28d4:
  mu.reg_write(UC_ARM64_REG_X0,0);mu.reg_write(UC_ARM64_REG_PC,mu.reg_read(UC_ARM64_REG_X30));return
 if not (0x8401c00<=address<0x8402070 or 0x8403130<=address<0x84031b8):raise RuntimeError('Unexpected receive call '+hex(address))
uc.hook_add(UC_HOOK_CODE,code)
rng=random.Random(86);count=0
for length in [6,13,14,15,31,127,128,129,255,256]:
 for corrupt in (False,True):
  frame=bytearray(rng.randrange(256) for _ in range(length))
  frame[:6]=b'ICPA'+bytes([3,length%256])
  if length>=14:
   struct.pack_into('<H',frame,10,0);struct.pack_into('<H',frame,10,packet.checksum(frame))
   if corrupt:frame[-1]^=1
  current_length=length;observed=None
  uc.mem_write(obj,bytes(0x300));uc.mem_write(buf,bytes(0x200))
  uc.mem_write(obj+0x178,struct.pack('<Q',buf));uc.mem_write(buf+0x120,struct.pack('<Q',length));uc.mem_write(buf+0x20,bytes(frame))
  uc.reg_write(UC_ARM64_REG_X19,obj+0x88);uc.reg_write(UC_ARM64_REG_X20,obj);uc.reg_write(UC_ARM64_REG_X24,256)
  uc.reg_write(UC_ARM64_REG_SP,STACK+0xff000);uc.reg_write(UC_ARM64_REG_X30,STOP)
  uc.emu_start(0x8401c00,STOP,count=50000)
  if length<14:assert observed==('bad-length',None)
  else:
   expected=bytearray(frame)
   if corrupt:expected[4]=0xba
   assert observed==('queued',bytes(expected)),(length,corrupt,observed)
  count+=1
print('PASS:',count,'stock receive length/checksum cases; stopped before queue/consumer callback')
