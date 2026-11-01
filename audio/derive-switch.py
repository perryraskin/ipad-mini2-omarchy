#!/usr/bin/env python3
"""Offline exact J86 Switch3 edge/default/writer model. Never accesses a device.

Requires owner-extracted exact stock cache and Unicorn. This does not model the
AppleARMIISSwitch graph router, clock ownership or board playback sequencing.
"""
import argparse,hashlib,importlib.util,pathlib,struct,subprocess
from unicorn import Uc, UcError, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm64_const import UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3,UC_ARM64_REG_X4,UC_ARM64_REG_X5,UC_ARM64_REG_X6,UC_ARM64_REG_X30,UC_ARM64_REG_SP,UC_ARM64_REG_PC
p=argparse.ArgumentParser(description=__doc__);p.add_argument('kernelcache',type=pathlib.Path);p.add_argument('--backend',type=pathlib.Path,required=True);args=p.parse_args()
assert hashlib.sha256(args.kernelcache.read_bytes()).hexdigest()=='d173a651d02329a02d2f23c2859e1e54308a5e94da86ba729777efeb3503da08'
root=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('prelink',root/'research/read-prelink.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
_,segments,data=helper.prelink(args.kernelcache)
uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
HEAP=0x10000000;STACK=0x20000000;MMIO=0x40000000;STOP=0x50000000
for name,va,vs,fo,fs in segments:
 if not vs:continue
 base=va&0xffffffff;lo=base&~4095;end=(base+vs+4095)&~4095
 try:uc.mem_map(lo,end-lo)
 except UcError:pass
 if fs:uc.mem_write(base,data[fo:fo+fs])
for base,size in [(HEAP,0x100000),(STACK,0x100000),(MMIO,0x10000),(STOP,0x1000)]:uc.mem_map(base,size)
R=[UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3,UC_ARM64_REG_X4,UC_ARM64_REG_X5,UC_ARM64_REG_X6]
writes=[]
def code(mu,address,size,user):
 if not (0x863e39c<=address<0x863e420 or 0x863e54c<=address<0x863e7b4):
  raise RuntimeError('Unexpected code '+hex(address))
def write(mu,access,address,size,value,user):writes.append((address-MMIO,size,value))
uc.hook_add(UC_HOOK_CODE,code)
uc.hook_add(UC_HOOK_MEM_WRITE,write,begin=MMIO,end=MMIO+0xffff)
def call(fn,*values):
 uc.reg_write(UC_ARM64_REG_SP,STACK+0xff000);uc.reg_write(UC_ARM64_REG_X30,STOP)
 for reg,value in zip(R,values):uc.reg_write(reg,value)
 uc.emu_start(fn,STOP,count=10000)
 assert uc.reg_read(UC_ARM64_REG_PC)==STOP,'instruction bound'
 return uc.reg_read(UC_ARM64_REG_X0)&0xffffffff
def words(address,count=20):return list(struct.unpack('<'+'I'*count,uc.mem_read(address,4*count)))
obj=HEAP;default=HEAP+0x1000;mask=HEAP+0x2000;value=HEAP+0x3000
# Class constructor 0x863e7c8 names Switch3; distinct from Switch5/AOP1.
assert bytes(uc.mem_read(0x73653b0,19)).split(b'\0')[0]==b'AppleAE2I2SSwitch3'
assert call(0x863e400,obj)==20
assert call(0x863e408,obj)==15
call(0x863e39c,obj,default)
expected={'defaults':words(default)}
for reverse in range(2):
 for mode in range(2):
  for lane in range(2):
   uc.mem_write(mask,bytes(80));uc.mem_write(value,bytes(80))
   a,b=(0x70696e31,0x61756431) if reverse else (0x61756431,0x70696e31)
   assert call(0x863e54c,obj,mode,a,b,lane,mask,value)==0
   expected[f'{reverse}{mode}{lane}']=words(mask)+words(value)
# Illegal lane must fail before changing either scratch array.
uc.mem_write(mask,bytes(80));uc.mem_write(value,bytes(80))
assert call(0x863e54c,obj,0,0x61756431,0x70696e31,2,mask,value)==0xe00002be
assert words(mask)+words(value)==[0]*40
# Writer has exactly20 contiguous 32-bit stores, including offsets0x2c..0x38.
uc.mem_write(obj+0xb8,struct.pack('<Q',MMIO));writes.clear()
assert call(0x863e3dc,obj,default)==0
assert writes==[(4*i,4,n) for i,n in enumerate(expected['defaults'])]
actual={}
for line in subprocess.check_output([str(args.backend.resolve())],text=True).splitlines():
 key,*numbers=line.split();actual[key]=[int(n,16) for n in numbers]
assert actual==expected,(actual,expected)
print('PASS: exact Switch3 defaults, 8 aud1/pin1 edge cases, rejected lane, 20-word synthetic writer; C agreement')
print('Offline only: full graph routing, NCO clocks, DMA and playback remain unqualified.')
