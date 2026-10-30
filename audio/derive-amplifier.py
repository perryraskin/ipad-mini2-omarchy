#!/usr/bin/env python3
"""Offline-only exact J86 amplifier sequence model; never accesses a device.

I2C, GPIO, board-mode and status reads are explicit modeling assumptions.
Private speaker records and register values are never printed by default.
"""
import argparse,hashlib,importlib.util,json,os,pathlib,struct
from unicorn import Uc,UcError,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3,UC_ARM64_REG_X4,UC_ARM64_REG_X5,UC_ARM64_REG_X6,UC_ARM64_REG_X7,UC_ARM64_REG_X30,UC_ARM64_REG_SP,UC_ARM64_REG_PC
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('kernelcache',type=pathlib.Path);p.add_argument('live_adt',type=pathlib.Path);p.add_argument('--private-trace',type=pathlib.Path);p.add_argument('--amp-revision',type=lambda v:int(v,0),default=0xb0);args=p.parse_args()
assert 0<=args.amp_revision<=255
assert hashlib.sha256(args.kernelcache.read_bytes()).hexdigest()=='d173a651d02329a02d2f23c2859e1e54308a5e94da86ba729777efeb3503da08'
def helper(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
_,segments,data=helper('prelink',ROOT/'research/read-prelink.py').prelink(args.kernelcache)
nodes=helper('assets',ROOT/'touch/tools/prepare-assets.py').adt_nodes(args.live_adt.read_bytes())
assert b'J86AP' in nodes['/device-tree']['compatible'].split(b'\0')
records=[v for props in nodes.values() for key,v in props.items() if key=='speaker-config']
assert len(records)==1 and len(records[0])==40
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
heap=HEAP;log=[];registers={};callbacks=set()
def alloc(size):
 global heap
 p=heap;heap=(heap+size+15)&~15;uc.mem_write(p,bytes(size));return p
def w32(a,v):uc.mem_write(a,struct.pack('<I',v))
def w64(a,v):uc.mem_write(a,struct.pack('<Q',v))
def ret(value=0):uc.reg_write(UC_ARM64_REG_X0,value);uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_X30))
def write(amp,reg,value,mask=255):
 assert 0<=amp<2 and 0<=reg<=0x7f
 old=registers.get((amp,reg),0);registers[amp,reg]=(old&~mask)|(value&mask)
 log.append({'amp':amp,'register':reg,'value':value,'mask':mask})
def code(mu,address,size,user):
 a=[mu.reg_read(r) for r in R]
 if FAKE<=address<FAKE+0x1000:
  slot=address-FAKE
  if slot==0xa68:write(a[1],a[2],a[3]);ret()
  elif slot==0xa70:
   for amp in range(2):write(amp,a[1],a[2])
   ret()
  elif slot==0xac0:write(a[1],a[2],a[4],a[3]);ret()
  elif slot==0xac8:
   for amp in range(2):write(amp,a[1],a[3],a[2])
   ret()
  elif slot==0xa78:ret(args.amp_revision if a[2]==5 else registers.get((a[1],a[2]),0))
  elif slot==0xae0:callbacks.add('modeled amplifier state callback');ret()
  elif slot==0x6f8:callbacks.add('modeled board mode=0');ret()
  else:raise RuntimeError('Unknown virtual callback '+hex(slot))
  return
 if address in (0x7a57f04,0x7c28200,0x7c282d0):callbacks.add('modeled logging/delay');ret();return
 if address==0x7dedfb0:callbacks.add('modeled superclass state callback=0');ret();return
 if address==0x759d6c0:mu.mem_write(a[0],bytes(a[1]));ret();return
 if address==0x7df2fe0:callbacks.add('modeled board function predicate=0');ret();return
 if address==0x81f5328:callbacks.add('modeled zeroed sense-channel descriptor');mu.mem_write(a[1],bytes(48));ret();return
 if address in (0x81f4ed4,0x81f582c,0x81f6478):callbacks.add('modeled GPIO/keepalive operation '+hex(address));ret();return
 if address==0x81f579c:callbacks.add('modeled board route predicate=0');ret();return
 if not 0x81f3f28<=address<0x81f7d18:raise RuntimeError('Unmodeled call '+hex(address)+' from '+hex(mu.reg_read(UC_ARM64_REG_X30)))
uc.hook_add(UC_HOOK_CODE,code)
vtable=alloc(0x1000)
for n in range(0,0x1000,8):w64(vtable+n,FAKE+n)
obj=alloc(0x300);cfg=alloc(40);uc.mem_write(cfg,records[0]);w64(obj,vtable);w64(obj+0x250,cfg);w32(obj+0x20c,2);w64(obj+0x1e8,alloc(2))
w32(0x88e5490,0)
def call(address,*values):
 uc.reg_write(UC_ARM64_REG_SP,STACK+0xff000);uc.reg_write(UC_ARM64_REG_X30,STOP)
 for r,v in zip(R,values):uc.reg_write(r,v)
 uc.emu_start(address,STOP,count=100000)
 assert uc.reg_read(UC_ARM64_REG_PC)==STOP,'Instruction limit reached'
 return uc.reg_read(UC_ARM64_REG_X0)
for title,address,values in [('revision setup',0x81f65b4,(obj,0)),('boost setup',0x81f7130,(obj,2)),('power config',0x81f72a4,(obj,2)),('status setup',0x81f76a8,(obj,))]:
 before=len(log)
 result=call(address,*values)
 print(title+': '+str(len(log)-before)+' modeled register operations; returned '+hex(result))
print('Modeled amplifier revision:',hex(args.amp_revision),'(not measured)')
print('Modeling assumptions:',', '.join(sorted(callbacks)))
if args.private_trace:
 if args.private_trace.exists():raise ValueError('Refusing to overwrite private trace')
 fd=os.open(args.private_trace,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:f.write(json.dumps(log,indent=2)+'\n')
 print('Private trace written. Do not publish it.')
print('Offline model only: no amplifier, clock, DMA or GPIO hardware writes; no playback claim.')
