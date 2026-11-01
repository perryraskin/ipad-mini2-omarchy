#!/usr/bin/env python3
"""Offline exact J86 Switch3 graph-router model with explicit fake OS services. Never accesses a device.

Requires owner-extracted exact stock cache and Unicorn. This does not model the
AppleARMIISSwitch graph router, clock ownership or board playback sequencing.
"""
import argparse,hashlib,importlib.util,pathlib,struct,subprocess
from unicorn import Uc, UcError, UC_ARCH_ARM64, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm64_const import UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3,UC_ARM64_REG_X4,UC_ARM64_REG_X5,UC_ARM64_REG_X6,UC_ARM64_REG_X7,UC_ARM64_REG_X30,UC_ARM64_REG_SP,UC_ARM64_REG_PC
p=argparse.ArgumentParser(description=__doc__);p.add_argument('kernelcache',type=pathlib.Path);p.add_argument('--backend',type=pathlib.Path,required=True);args=p.parse_args()
assert hashlib.sha256(args.kernelcache.read_bytes()).hexdigest()=='d173a651d02329a02d2f23c2859e1e54308a5e94da86ba729777efeb3503da08'
root=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('prelink',root/'research/read-prelink.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
_,segments,data=helper.prelink(args.kernelcache)
uc=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
FAKE=0x30000000;HEAP=0x10000000;STACK=0x20000000;MMIO=0x40000000;STOP=0x50000000
for name,va,vs,fo,fs in segments:
 if not vs:continue
 base=va&0xffffffff;lo=base&~4095;end=(base+vs+4095)&~4095
 try:uc.mem_map(lo,end-lo)
 except UcError:pass
 if fs:uc.mem_write(base,data[fo:fo+fs])
for base,size in [(HEAP,0x100000),(STACK,0x100000),(MMIO,0x10000),(FAKE,0x10000),(STOP,0x1000)]:uc.mem_map(base,size)
R=[UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3,UC_ARM64_REG_X4,UC_ARM64_REG_X5,UC_ARM64_REG_X6,UC_ARM64_REG_X7]
heap=HEAP;writes=[];services=[]
def alloc(n):
 global heap
 a=heap;heap=(heap+n+15)&~15
 assert heap<HEAP+0x100000
 uc.mem_write(a,bytes(n));return a
def w32(a,v):uc.mem_write(a,struct.pack('<I',v))
def w64(a,v):uc.mem_write(a,struct.pack('<Q',v))
def ret(v=0):uc.reg_write(UC_ARM64_REG_X0,v);uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_X30))
fakevt=alloc(0x600)
for n in range(0,0x600,8):w64(fakevt+n,FAKE+n)
def opaque():
 a=alloc(0x40);w64(a,fakevt);return a
def code(mu,address,size,user):
 a=[mu.reg_read(r) for r in R]
 if FAKE<=address<FAKE+0x600:
  assert address-FAKE in (0x28,0xa0,0xb0,0xe0,0x428),(hex(address-FAKE),hex(mu.reg_read(UC_ARM64_REG_X30)))
  services.append(('opaque method',address-FAKE));ret(1);return
 if address in (0x7758abc,0x77598d0):services.append(('lock',address));ret();return
 if address==0x7d64298:services.append(('diagnostic route string',0));ret(opaque());return
 if address==0x7be2280:services.append(('OSArray allocation',a[0]));ret(opaque());return
 if address==0x759d6c0:
  assert 0<=a[1]<=0x10000
  mu.mem_write(a[0],bytes(a[1]));ret();return
 if not (0x7d6347c<=address<0x7d638dc or 0x7d644ac<=address<0x7d65000 or 0x863e39c<=address<0x863e420 or 0x863e4dc<=address<0x863e7c8):
  raise RuntimeError('Unmodeled call '+hex(address)+' from '+hex(mu.reg_read(UC_ARM64_REG_X30)))
def write(mu,access,address,size,value,user):writes.append((address-MMIO,size,value))
uc.hook_add(UC_HOOK_CODE,code);uc.hook_add(UC_HOOK_MEM_WRITE,write,begin=MMIO,end=MMIO+0xffff)
def call(fn,*values):
 sp=STACK+0xff000;uc.reg_write(UC_ARM64_REG_SP,sp);uc.reg_write(UC_ARM64_REG_X30,STOP)
 for reg,value in zip(R,values):uc.reg_write(reg,value)
 uc.emu_start(fn,STOP,count=2000000)
 assert uc.reg_read(UC_ARM64_REG_PC)==STOP,'instruction bound'
 return uc.reg_read(UC_ARM64_REG_X0)&0xffffffff
def fresh():
 obj=alloc(0xc8);vt=alloc(0x600);table=alloc(15*24);matrix=alloc(15*15*2)
 uc.mem_write(vt,bytes(uc.mem_read(fakevt,0x600)));w64(obj,vt)
 for slot,fn in {0x540:0x863e504,0x548:0x863e7b8,0x550:0x7d64ee4,0x558:0x863e408,0x560:0x863e410,0x568:0x863e4dc,0x570:0x863e400,0x578:0x863e39c,0x580:0x863e54c,0x588:0x863e3dc}.items():w64(vt+slot,fn)
 w32(obj+0x88,15);w32(obj+0x8c,20);w64(obj+0x90,opaque());w64(obj+0x98,table);w64(obj+0xa0,matrix);w64(obj+0xb8,MMIO)
 for i in range(15):
  name=call(0x863e410,obj,i);w32(table+i*24,name);w64(table+i*24+8,opaque());w32(table+i*24+16,call(0x863e4dc,obj,name))
 route=alloc(0x40);desc=alloc(12);w64(route+0x28,obj);w64(route+0x30,desc)
 # Public exact J86 function-i2s_route record; no default-routes property exists.
 uc.mem_write(desc,struct.pack('<III',0x61756431,0x70696e31,0x00330303))
 return obj,route
actual={}
for value in (1,2):
 obj,route=fresh();writes.clear()
 assert call(0x7d6347c,route,0,0)==0
 default=[v for _,_,v in writes[-20:]]
 writes.clear();assert call(0x7d6347c,route,2,value)==0
 active=[v for _,_,v in writes[-20:]]
 actual['tx'+str(value-1)]=active
 assert len(writes)==20 and any(a!=b for a,b in zip(default,active))
 writes.clear();assert call(0x7d6347c,route,0,0)==0
 stopped=[v for _,_,v in writes[-20:]]
 assert stopped==default
 print('TX route model',value,'active differences',[(4*i,hex(a),hex(b)) for i,(a,b) in enumerate(zip(default,active)) if a!=b])
 print('Stop restored default table; OS allocation/lock/property callbacks are modeled.')
print('Offline only; no live switch, clock, DMA, amplifier or playback qualification.')

backend={}
for line in subprocess.check_output([str(args.backend.resolve())],text=True).splitlines():
 key,*numbers=line.split()
 if key.startswith('tx'):backend[key]=[int(n,16) for n in numbers]
assert backend==actual
print('PASS: both complete C TX tables match stock graph routing and wrapper; stop restores modeled defaults.')
