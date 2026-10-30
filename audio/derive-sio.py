#!/usr/bin/env python3
"""Offline exact-stock A7 SIO DMA configuration-message model. No device access.

Synthetic DMA configuration, command pool and successful firmware reply are
explicit assumptions. This neither boots SIO nor submits real DMA/audio.
"""
import argparse,hashlib,importlib.util,json,pathlib,struct
from unicorn import Uc,UcError,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3,UC_ARM64_REG_X4,UC_ARM64_REG_X5,UC_ARM64_REG_X6,UC_ARM64_REG_X7,UC_ARM64_REG_X30,UC_ARM64_REG_SP,UC_ARM64_REG_PC
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('kernelcache',type=pathlib.Path);p.add_argument('--scenario',choices=['success','no-slot','submit-error'],default='success');args=p.parse_args()
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
heap=HEAP;events=[];phase="configure"
def alloc(size):
 global heap
 ptr=heap;heap=(heap+size+15)&~15;uc.mem_write(ptr,bytes(size));return ptr
def w32(a,v):uc.mem_write(a,struct.pack('<I',v))
def w64(a,v):uc.mem_write(a,struct.pack('<Q',v))
def ret(v=0):uc.reg_write(UC_ARM64_REG_X0,v);uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_X30))
obj=alloc(0x5000);vtable=alloc(0x1000);pool=alloc(0x100);poolvt=alloc(0x1000);controller=alloc(0x500);table=alloc(0x10000);command=alloc(0x100);provider=alloc(0x100)
for offset in range(0,0x1000,8):w64(vtable+offset,FAKE+offset);w64(poolvt+offset,FAKE+offset)
w64(obj,vtable);w64(pool,poolvt);w64(obj+0x70,pool);w64(obj+0x22b8,pool);w64(obj+0x22c8,controller);w64(controller+0x4b8,table);w64(obj+0x78,provider)
config=alloc(32);synthetic=[0x11000000+n for n in range(8)];uc.mem_write(config,struct.pack('<8I',*synthetic));w64(obj+0x2310,config);w32(obj+0x2318,synthetic[3]);w32(obj+0x231c,128)
def code(mu,address,size,user):
 a=[mu.reg_read(r) for r in R]
 if address==FAKE+0x80:events.append('modeled command allocation');ret(command);return
 if address in (FAKE+0x88,FAKE+0xa0):events.append('modeled command release');ret();return
 if address==FAKE+0x108:
  opcode,slot=struct.unpack('<HI',mu.mem_read(command+0x72,6))
  if phase=='configure':assert (opcode,slot)==(5,2);events.append('configure opcode=5 slot=2')
  else:assert (opcode,slot)==(0x0a03,128);events.append('parameter opcode=3 parameter=10 value=128 (synthetic frame size)')
  if args.scenario=='submit-error':events.append('modeled transport submission failure');ret(0xe00002bc);return
  mu.mem_write(command+0x72,struct.pack('<H',0x65));ret();return
 if address==0x83ee8f4:
  if args.scenario=='no-slot':events.append('modeled slot allocation failure');ret();return
  w32(a[2],2);events.append('modeled shared slot allocation=2');ret(1);return
 if address==0x83ee9c4:assert a[1]==2;events.append('modeled shared slot release=2');ret();return
 if not (0x83efd64<=address<0x83f0018 or 0x83f01a8<=address<0x83f02ac):raise RuntimeError('Unmodeled call '+hex(address))
uc.hook_add(UC_HOOK_CODE,code);uc.reg_write(UC_ARM64_REG_X0,obj);uc.reg_write(UC_ARM64_REG_SP,STACK+0xff000);uc.reg_write(UC_ARM64_REG_X30,STOP)
uc.emu_start(0x83efd64,STOP,count=50000)
if uc.reg_read(UC_ARM64_REG_PC)!=STOP:raise RuntimeError('Instruction budget exhausted')
assert uc.reg_read(UC_ARM64_REG_X0)=={'success':0,'no-slot':0xe00002bd,'submit-error':0xe00002bc}[args.scenario]
words=struct.unpack('<16I',uc.mem_read(table+2*12,64))
expected={0:synthetic[1],1:synthetic[2],2:synthetic[3],3:synthetic[4],4:synthetic[3],5:synthetic[5],6:128,7:synthetic[6],14:0}
if args.scenario!='no-slot':assert all(words[index]==value for index,value in expected.items())
else:assert not any(words)
configured=args.scenario=='success'
assert bytes(uc.mem_read(obj+0x230c,1))==bytes([int(configured)])
assert events[-1]=='modeled command release'
assert ('modeled shared slot release=2' in events)==(args.scenario!='no-slot')
phase='parameter';uc.mem_write(command,bytes(0x100))
uc.reg_write(UC_ARM64_REG_X0,obj);uc.reg_write(UC_ARM64_REG_X1,10);uc.reg_write(UC_ARM64_REG_X2,128)
uc.reg_write(UC_ARM64_REG_SP,STACK+0xff000);uc.reg_write(UC_ARM64_REG_X30,STOP)
uc.emu_start(0x83f01a8,STOP,count=50000)
assert uc.reg_read(UC_ARM64_REG_PC)==STOP
assert uc.reg_read(UC_ARM64_REG_X0)==(0xe00002bc if args.scenario=='submit-error' else 0)
assert events[-1]=='modeled command release'
print(json.dumps({'offline_model_only':True,'playback_qualified':False,'events':events,'synthetic_shared_words':[hex(w) for w in words],'configured_flag':configured,'scenario':args.scenario},indent=2))
