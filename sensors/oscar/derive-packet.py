#!/usr/bin/env python3
"""Validate Oscar command framing against exact stock code, in emulator RAM only.

Stops before the stock transport callback. Does not implement sensor reporting,
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
captured=None
payload_ptr=HEAP+0x1000;first=HEAP+0x2000;second=HEAP+0x3000

def code(mu,address,size,user):
 global captured
 a=[mu.reg_read(r) for r in R]
 if address==0x8403f88:
  sp=mu.reg_read(UC_ARM64_REG_SP);length=mu.reg_read(UC_ARM64_REG_X22)
  assert 14<=length<=128
  captured=bytes(mu.mem_read(sp+0x28,length));mu.emu_stop();return
 if address==0x7720540:
  assert a[2]<=a[3] and a[2]<=114
  if a[2]:mu.mem_write(a[0],bytes(mu.mem_read(a[1],a[2])))
  mu.reg_write(UC_ARM64_REG_PC,mu.reg_read(UC_ARM64_REG_X30));return
 if not (0x8403ef4<=address<0x8403f88 or 0x8403130<=address<0x84031b8):raise RuntimeError('Unexpected call before transport boundary '+hex(address))
uc.hook_add(UC_HOOK_CODE,code)
rng=random.Random(86);count=0
for length in [0,1,2,3,31,32,113,114]:
 for channel,command in [(0,0),(3,0xabcd),(255,65535)]:
  payload=bytes(rng.randrange(256) for _ in range(length));uc.mem_write(payload_ptr,payload or b'\0');captured=None
  for r,value in zip(R,[HEAP,channel,command,payload_ptr,length]):uc.reg_write(r,value)
  uc.reg_write(UC_ARM64_REG_SP,STACK+0xff000);uc.reg_write(UC_ARM64_REG_X30,STOP)
  uc.emu_start(0x8403ef4,STOP,count=50000)
  assert uc.reg_read(UC_ARM64_REG_PC)==0x8403f88
  assert captured==packet.encode_command(channel,command,payload)
  count+=1
for left,right in [(b'',b''),(b'\x01',b'\x02'),(b'\xff'*13,b'\x80'*17),(bytes(range(128)),bytes(range(114)))]:
 uc.mem_write(first,left or b'\0');uc.mem_write(second,right or b'\0')
 for r,value in zip(R,[first,len(left),second,len(right)]):uc.reg_write(r,value)
 uc.reg_write(UC_ARM64_REG_X30,STOP)
 uc.emu_start(0x8403130,STOP,count=50000)
 assert uc.reg_read(UC_ARM64_REG_PC)==STOP and uc.reg_read(UC_ARM64_REG_X0)==packet.checksum(left,right)
print('PASS:',count,'synthetic command frames and four checksum-span cases match executed stock code; stopped before UART/transport')
