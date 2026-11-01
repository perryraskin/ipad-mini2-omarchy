#!/usr/bin/env python3
"""Offline-only stock J86 MCA format/configuration tracing. No device access.

Requires Unicorn in a local Python environment and an owner-extracted 16H88
kernelcache. Fake platform functions and cleared busy bits are modeling inputs,
not evidence of functional playback. Never execute this trace as an MMIO script.
"""
import argparse,hashlib,importlib.util,pathlib,struct,subprocess,re
from unicorn import Uc,UcError,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
from unicorn.arm64_const import UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3,UC_ARM64_REG_X4,UC_ARM64_REG_X5,UC_ARM64_REG_X6,UC_ARM64_REG_X7,UC_ARM64_REG_X30,UC_ARM64_REG_SP,UC_ARM64_REG_PC
ROOT=pathlib.Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('kernelcache',type=pathlib.Path);parser.add_argument('--amp-clock-model',action='store_true',help='Model MCA separate amplifier MCLK enable with synthetic 24MHz reference');parser.add_argument('--lifecycle-model',action='store_true');parser.add_argument('--nco-model',action='store_true');parser.add_argument('--nco-parent-rate',type=int,default=342857142);parser.add_argument('--stuck-busy',choices=('flush',),help='Offline non-clearing configure poll; expect instruction-bound stop before TX');parser.add_argument('--route-call-model',action='store_true',help='Capture stock MCA route callback arguments with an opaque route object');parser.add_argument('--nco-backend',type=pathlib.Path,help='Compare NCO1 writes against a compiled offline C plan');args=parser.parse_args()
assert hashlib.sha256(args.kernelcache.read_bytes()).hexdigest()=='d173a651d02329a02d2f23c2859e1e54308a5e94da86ba729777efeb3503da08','Expected exact iPad4,5 16H88 stock kernelcache'
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
heap=HEAP;fakes=[];log=[];state={}
def alloc(size):
 global heap
 p=heap;heap=(heap+size+15)&~15;uc.mem_write(p,bytes(size));return p
def w32(a,v):uc.mem_write(a,struct.pack('<I',v&0xffffffff))
def w64(a,v):uc.mem_write(a,struct.pack('<Q',v))
def fake(name):
 index=len(fakes);fakes.append(name);vtable=alloc(0x1000)
 for n in range(0,0x1000,8):w64(vtable+n,FAKE+index*0x1000+n)
 obj=alloc(0x40);w64(obj,vtable);return obj

def ret(value=0):uc.reg_write(UC_ARM64_REG_X0,value);uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_X30))
def code(mu,addr,size,user):
 if FAKE<=addr<FAKE+0x100000:
  index=(addr-FAKE)//0x1000;slot=(addr-FAKE)%0x1000;a=[mu.reg_read(r) for r in R]
  extra=''
  if fakes[index]=='mclk' and slot==0x78:extra=' hz='+str(struct.unpack('<I',mu.mem_read(a[1],4))[0])
  log.append('platform '+fakes[index]+' vslot='+hex(slot)+extra)
  if args.amp_clock_model and fakes[index]=='provider' and slot==0x550:ret(24000000)
  elif fakes[index]=='clocks' and slot==0x548:ret(args.nco_parent_rate if a[1]<2 else 24000000)
  else:ret(1)
  return
 if addr in (0x7c282d0,0x7a57f04,0x7cbe724,0x775ca84):ret();return # modeled delay/debug/IOReport counter
 if addr==0x7c2f45c:log.append('modeled registry property publication');ret(1);return
 if addr==0x7d6347c:
  log.append('platform route/gate args='+','.join(hex(mu.reg_read(r)) for r in R[:3]));ret();return
 if not (0x8639a98<=addr<0x863e850 or 0x7d46818<=addr<0x7d46c00 or 0x82c1fc8<=addr<0x82c2334):
  raise RuntimeError('Unmodeled call '+hex(addr)+' from '+hex(mu.reg_read(UC_ARM64_REG_X30)))
def read(mu,access,addr,size,value,user):
 offset=addr-MMIO;v=state.get(offset,0)
 if offset in (0x44,0x48) and offset!={'flush':0x48}.get(args.stuck_busy):v=0 # modeled self-clearing unless fault injected
 w32(addr,v)
def write(mu,access,addr,size,value,user):
 offset=addr-MMIO;state[offset]=value&0xffffffff;log.append('write +%04x = %08x'%(offset,value&0xffffffff))
uc.hook_add(UC_HOOK_CODE,code)
uc.hook_add(UC_HOOK_MEM_READ,read,begin=MMIO,end=MMIO+0xffff)
uc.hook_add(UC_HOOK_MEM_WRITE,write,begin=MMIO,end=MMIO+0xffff)
def call(fn,*arguments):
 uc.reg_write(UC_ARM64_REG_SP,STACK+0xff000);uc.reg_write(UC_ARM64_REG_X30,STOP)
 for r,a in zip(R,arguments):uc.reg_write(r,a)
 uc.emu_start(fn,STOP,count=500000)
 if uc.reg_read(UC_ARM64_REG_PC)!=STOP:raise RuntimeError('Instruction limit reached at '+hex(uc.reg_read(UC_ARM64_REG_PC)))
 return uc.reg_read(UC_ARM64_REG_X0)
def run(title,descriptor):
 state.clear();log.clear();obj=alloc(0x228);w64(obj,0x7575cd0);w64(obj+0x110,fake('provider'));w64(obj+0x120,MMIO);w32(obj+0x128,1)
 for offset,name in [(0x150,'irq'),(0x158,'txdma'),(0x160,'rxdma'),(0x168,'mclk')]:w64(obj+offset,fake(name))
 if args.route_call_model:w64(obj+0x1a8,fake('route'))
 if args.amp_clock_model:
  w64(obj+0x148,MMIO+0x8000);uc.mem_write(obj+0x179,b'\1')
 # Exact bounded live MCA1 inventory measured TX/RX FIFO depths128.
 w32(obj+0x130,128);w32(obj+0x134,128)
 d=alloc(36);uc.mem_write(d,descriptor)
 print(title)
 try:
  rc=call(0x863b7fc,obj,0,d);print('configure rc',hex(rc))
  if args.amp_clock_model:
   print('amp MCLK enable rc',hex(call(0x863cf80,obj,d,1)))
  rc=call(0x863c61c,obj,2);print('start TX rc',hex(rc))
  if args.lifecycle_model:
   rc=call(0x863c8f8,obj,2);print('stop TX rc',hex(rc))
  if args.amp_clock_model:
   assert state[0x8000]==0x58,'expected nclk/2 plus MCLK enable'
   print('amp MCLK disable rc',hex(call(0x863cf80,obj,d,0)))
   assert state[0x8000]==0x18,'expected MCLK enable cleared'
   print('PASS: separate MCLK control 58 enabled / 18 disabled (modeled 24MHz nclk)')
 except (RuntimeError,UcError) as error:
  if not args.stuck_busy:raise
  assert isinstance(error,RuntimeError) and str(error).startswith('Instruction limit reached'),error
  expected=['write +0044 = 00000003','write +0048 = 00000001']
  assert [line for line in log if line.startswith('write ')]==expected,log
  print('EXPECTED NON-CLEARING POLL: instruction bound reached before any TX enable')
 else:
  assert not args.stuck_busy,'Injected busy bit unexpectedly cleared'

 for line in log:print(' ',line)
 print('Model only; no playback claim.\n')
# Exact common speaker template, not device calibration or firmware bytes.
descriptor=bytes.fromhex('1012000008000100001bb700000010003000010003000000ff0000000208101000000000')
run('J86 stock speaker template (slave)',descriptor)
run('J86 stock speaker template with master bit',bytes([descriptor[0]|1])+descriptor[1:])

if args.nco_model:
 state.clear();log.clear();obj=alloc(0xb8)
 w64(obj+0x88,fake('clocks'));w64(obj+0x98,MMIO);w32(obj+0xa0,5);w64(obj+0xa8,alloc(20));w32(obj+0xb0,0x1000)
 print('NCO1 MODEL: parent rate',args.nco_parent_rate,'Hz; crystal limit24MHz; requested12.288MHz')
 try:print('set rate rc',hex(call(0x82c1fc8,obj,1,12288000,0,0)))
 except (RuntimeError,UcError) as error:print('INCOMPLETE NCO MODEL',error)
 for line in log:print(' ',line)
 if args.nco_backend:
  actual=[(int(a,16),int(b,16)) for a,b in re.findall(r'write \+([0-9a-f]+) = ([0-9a-f]+)', '\n'.join(log))]
  expected=[tuple(int(n,16) for n in line.split()) for line in subprocess.check_output([str(args.nco_backend.resolve()),str(args.nco_parent_rate)],text=True).splitlines()]
  assert actual==expected,(actual,expected)
  print('PASS: fixed-format C NCO plan matches exact stock writes for this synthetic parent')
 print('Modeled reference rates are not measured clock evidence. No hardware writes.')
