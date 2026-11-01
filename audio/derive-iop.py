#!/usr/bin/env python3
"""Offline exact A7 IOP-v1 register-layout model. Never accesses real MMIO.

Synthetic memory descriptor, DMA address, clock and interrupt callbacks only.
This is evidence for a driver port, not an executable hardware register recipe.
"""
import argparse,hashlib,importlib.util,json,pathlib,struct
from unicorn import Uc,UcError,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm64_const import UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3,UC_ARM64_REG_X4,UC_ARM64_REG_X5,UC_ARM64_REG_X6,UC_ARM64_REG_X7,UC_ARM64_REG_X30,UC_ARM64_REG_SP,UC_ARM64_REG_PC
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('kernelcache',type=pathlib.Path);args=p.parse_args()
assert hashlib.sha256(args.kernelcache.read_bytes()).hexdigest()=='d173a651d02329a02d2f23c2859e1e54308a5e94da86ba729777efeb3503da08'
spec=importlib.util.spec_from_file_location('prelink',ROOT/'research/read-prelink.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
_,segments,data=helper.prelink(args.kernelcache)
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
obj=HEAP;vt=HEAP+0x1000;descriptor=HEAP+0x2000;message=HEAP+0x3000;writes=[];stop_events=[]
def w64(a,v):uc.mem_write(a,struct.pack('<Q',v))
def w32(a,v):uc.mem_write(a,struct.pack('<I',v))
def ret(v=0):uc.reg_write(UC_ARM64_REG_X0,v);uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_X30))
w64(obj,vt);w64(obj+0x98,MMIO);w64(descriptor,vt)
for offset in range(0,0x1000,8):w64(vt+offset,FAKE+offset)
def code(mu,address,size,user):
 a=[mu.reg_read(r) for r in R]
 if address==FAKE+0x5e8:ret(struct.unpack('<I',mu.mem_read(MMIO+a[1],4))[0]);return
 if address==FAKE+0xa8:ret(0x71550);return
 if address==0x7613540:ret(0);return # Synthetic non-locking context.
 if address==FAKE+0xb0:stop_events.append('interrupt-source-disable');ret();return
 if address in (FAKE+0x568,FAKE+0x560):
  assert a[1]==0 and a[2]==0
  stop_events.append('provider-callback-'+hex(address-FAKE));ret();return
 if address==0x7c90894:ret(0x123456789);return
 if address==0x775ca84:ret(0);return
 if address==0x7762cf8:ret(0x1020304050607080);return
 if not (0x80c2bd4<=address<0x80c2db0 or 0x80c2ebc<=address<0x80c3010 or 0x80c1160<=address<0x80c1210 or 0x80c1350<=address<0x80c13b8 or 0x80c0ec8<=address<0x80c0f24):raise RuntimeError('Unmodeled call '+hex(address))
def write(mu,access,address,size,value,user):writes.append((address-MMIO,size,value))
uc.hook_add(UC_HOOK_CODE,code);uc.hook_add(UC_HOOK_MEM_WRITE,write,begin=MMIO,end=MMIO+0xffff)
def call(fn,*values):
 writes.clear();uc.reg_write(UC_ARM64_REG_SP,STACK+0xff000);uc.reg_write(UC_ARM64_REG_X30,STOP)
 for reg,value in zip(R,values):uc.reg_write(reg,value)
 uc.emu_start(fn,STOP,count=50000)
 assert uc.reg_read(UC_ARM64_REG_PC)==STOP
 return list(writes)
# Execute actual A7 queue methods; callbacks emulate reads, not queue writes.
queue_init=call(0x80c2cac,obj)
assert queue_init==[(0x1000,4,0x1111)]
for enable,offset in [(0,0x1000),(1,0x1004)]:
 assert call(0x80c2cbc,obj,enable)==[(offset,4,1)]
 assert call(0x80c2d4c,obj,enable)==[(offset,4,0x1000)]
for initial in [0,1,0x20000,0x20001]:
 for enable in [0,1]:
  w32(MMIO+0x1020,initial)
  assert call(0x80c2d68,obj,enable)==[(0x1020,4,(initial & ~1)|enable)]
for offset,fn in [(0x1008,0x80c2c18),(0x1020,0x80c2cdc)]:
 for value in [0,0x10000,0x20000,0x30000]:
  w32(MMIO+offset,value)
  assert call(fn,obj)==[]
  assert uc.reg_read(UC_ARM64_REG_X0)==((value>>17)&1)
remap=call(0x80c2ebc,obj,0,descriptor)
assert remap==[(0x10,4,0),(0x14,4,0),(0x18,4,0x71000),(0x1c,4,0),(8,4,0x23456789),(12,4,1),(0x20,4,1)]
w32(MMIO+0x28,0x55aa0001)
assert call(0x80c2f3c,obj,1)==[(0x28,4,0x55aa0011)]
assert call(0x80c2f3c,obj,0)==[(0x28,4,0x55aa0001)]
w32(MMIO+0x80c,0x33)
sync=call(0x80c2f9c,obj)
assert sync==[(0x80c,4,0x31),(0x810,4,0x50607080),(0x818,4,0x10203040),(0x80c,4,0x33)]
w64(message,0x12345678abcdef01)
assert call(0x80c2be4,obj,message)==[(0x1010,8,0x12345678abcdef01)]
w64(MMIO+0x1038,0x9876543212345678);call(0x80c2bd4,obj,message)
assert struct.unpack('<Q',uc.mem_read(message,8))[0]==0x9876543212345678
# Execute the inherited stock stop method with exact A7 virtual overrides.
# IRQ objects and provider callbacks are fakes; no DMA quiescence is implied.
provider=HEAP+0x4000;irq0=HEAP+0x5000;irq1=HEAP+0x6000
for target in (provider,irq0,irq1):w64(target,vt)
w64(obj+0x88,provider);w64(obj+0x158,irq0);w64(obj+0x160,irq1)
for slot,fn in {0x618:0x80c2d68,0x5a0:0x80c1350,0x650:0x80c2f3c,
                0x648:0x80c2f38,0x670:0x80c0ec8}.items():w64(vt+slot,fn)
uc.mem_write(obj+0xa8,b'\x01');uc.mem_write(obj+0xaa,b'\x00')
uc.mem_write(obj+0x130,b'\x00')
w32(MMIO+0x1020,0x20001);w32(MMIO+0x28,0x55aa0011);w32(MMIO+0x20,1)
stop_writes=call(0x80c1160,obj)
assert stop_writes==[(0x1020,4,0x20000),(0x28,4,0x55aa0001)]
assert stop_events==['interrupt-source-disable','interrupt-source-disable',
                     'provider-callback-0x568','provider-callback-0x560']
assert bytes(uc.mem_read(obj+0xa8,1))==b'\x00'
assert struct.unpack('<I',uc.mem_read(MMIO+0x20,4))[0]==1
stop_events.clear();assert call(0x80c1160,obj)==[];assert not stop_events
print(json.dumps({'offline_model_only':True,'stock_stop_model_pass':True,'stock_stop_retains_remap':True,'a7_single_mailbox_model_pass':True,'synthetic_queue_reset':queue_init,'synthetic_remap_writes':remap,'synthetic_time_writes':sync,'cpu_control_offset':'0x28','tx_message_offset':'0x1010','rx_message_offset':'0x1038','firmware_boot_qualified':False},indent=2))
