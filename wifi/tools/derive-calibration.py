#!/usr/bin/env python3
"""Offline exact-stock J86 Wi-Fi calibration-structure model. No device access.

This models property lookup and memory operations only. It does not identify a
firmware iovar or qualify RF. Private calibration values are never printed.
"""
import argparse,hashlib,importlib.util,json,os,pathlib,random,re,struct
from unicorn import Uc,UcError,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X2,UC_ARM64_REG_X3,UC_ARM64_REG_X4,UC_ARM64_REG_X5,UC_ARM64_REG_X6,UC_ARM64_REG_X7,UC_ARM64_REG_X30,UC_ARM64_REG_SP,UC_ARM64_REG_PC
ROOT=pathlib.Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('kernelcache',type=pathlib.Path);p.add_argument('live_adt',type=pathlib.Path);p.add_argument('--private-output',type=pathlib.Path);p.add_argument('--synthetic-seed',type=int,default=1);p.add_argument('--synthetic',action='store_true',help='Replace calibration and MAC with synthetic patterns in model RAM only');args=p.parse_args()
assert hashlib.sha256(args.kernelcache.read_bytes()).hexdigest()=='d173a651d02329a02d2f23c2859e1e54308a5e94da86ba729777efeb3503da08'
def helper(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
_,segments,data=helper('prelink',ROOT/'research/read-prelink.py').prelink(args.kernelcache)
nodes=helper('assets',ROOT/'touch/tools/prepare-assets.py').adt_nodes(args.live_adt.read_bytes())
assert b'J86AP' in nodes['/device-tree']['compatible'].split(b'\0')
props=nodes['/device-tree/arm-io/usb-complex/usb-ehci1/wlan']
assert props['module-instance'].rstrip(b'\0')==b'seyval'
if args.synthetic:
 props=dict(props);rng=random.Random(args.synthetic_seed)
 for key,count in [('tx-calibration-2.4',6),('tx-calibration-5.0',18)]:props[key]=struct.pack('<'+'h'*count,*[rng.randint(-32768,32767) for i in range(count)])
 for key,count in [('rx-calibration-2.4',54),('rx-calibration-5.0',32)]:props[key]=struct.pack('<'+'b'*count,*[rng.randint(-128,127) for i in range(count)])
 props['local-mac-address']=bytes.fromhex('020000000001')
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
heap=HEAP;objects={};lookups=[];modeled=set();overrides={};nvram_phase=False
def alloc(size):
 global heap
 ptr=heap;heap=(heap+size+15)&~15
 if heap>HEAP+0x100000:raise RuntimeError('Model heap exhausted')
 uc.mem_write(ptr,bytes(size));return ptr
def w64(a,v):uc.mem_write(a,struct.pack('<Q',v))
def ret(value=0):uc.reg_write(UC_ARM64_REG_X0,value);uc.reg_write(UC_ARM64_REG_PC,uc.reg_read(UC_ARM64_REG_X30))
def string(a):
 raw=bytes(uc.mem_read(a,256));return raw.split(b'\0',1)[0].decode('ascii')
vt=alloc(0x1000)
for offset in range(0,0x1000,8):w64(vt+offset,FAKE+offset)
provider=alloc(0x40);w64(provider,vt)
data_vt=alloc(0x1000)
for offset in range(0,0x1000,8):w64(data_vt+offset,FAKE+0x1000+offset)
def datum(key):
 if key not in props:return 0
 raw=props[key];obj=alloc(0x40);buf=alloc(max(16,len(raw)));uc.mem_write(buf,raw);w64(obj,data_vt);objects[obj]=(raw,buf);return obj
def code(mu,address,size,user):
 a=[mu.reg_read(r) for r in R]
 if nvram_phase:
  if address==0x80481bc:mu.emu_stop();return
  if address in (0x8047bcc,0x8047da8):
   key=string(a[1])
   if key in overrides:raise RuntimeError('Duplicate calibration override')
   value=str(a[2]-(1<<32) if a[2]&(1<<31) else a[2]) if address==0x8047bcc else string(a[2])
   overrides[key]=value;ret();return
  if address==0x7af3ec4:
   fmt=string(a[2]);index=0;sp=mu.reg_read(UC_ARM64_REG_SP)
   def substitute(match):
    nonlocal index
    raw=struct.unpack('<Q',mu.mem_read(sp+8*index,8))[0];index+=1
    flags,width,kind=match.groups()
    if kind in 'di':value=raw-(1<<64) if raw&(1<<63) else raw;return str(value)
    if kind=='u':return str(raw)
    if kind in 'xX':return format(raw,('0'+width if '0' in flags else width)+kind)
    raise RuntimeError('Unmodeled format conversion')
   rendered=re.sub(r'%([-+ #0]*)([0-9]*)(?:ll|l|h)?([diuxX])',substitute,fmt)
   if '%' in rendered:raise RuntimeError('Unmodeled printf format')
   raw=rendered.encode('ascii');mu.mem_write(a[0],raw[:max(0,a[1]-1)]+b'\0');ret(len(raw));return
  if not 0x80480c8<=address<0x8049374:raise RuntimeError('Unmodeled NVRAM call '+hex(address))
  return
 if address==FAKE+0x118:
  modeled.add('symbol property lookup omitted (clock metadata)');ret();return
 if address==FAKE+0x128:
  key=string(a[1]);lookups.append({'property':key,'bytes':len(props[key]) if key in props else None});ret(datum(key));return
 if FAKE+0x1000<=address<FAKE+0x2000:
  raw,buf=objects[a[0]];slot=address-FAKE-0x1000
  if slot==0x98:ret(len(raw))
  elif slot==0xd0:ret(buf)
  elif slot==0xd8:
   if a[1]+a[2]>len(raw):raise RuntimeError('OSData range exceeds property')
   ret(buf+a[1])
  else:raise RuntimeError('Unmodeled OSData slot '+hex(slot))
  return
 if address==0x7bdcc40:modeled.add('OSData type cast');ret(a[0]);return
 if address==0x7755b58:
  left=bytes(mu.mem_read(a[0],a[2]));right=bytes(mu.mem_read(a[1],a[2]));ret(0 if left==right else 1);return
 if address in (0x802ce54,0x7f65838,0x7f659a4):modeled.add('suppressed stock logging');ret();return
 if not (0x8044918<=address<0x8046a0c or 0x8046a0c<=address<0x8046c38):raise RuntimeError('Unmodeled call '+hex(address))
uc.hook_add(UC_HOOK_CODE,code)
obj=alloc(0x100);logger=alloc(0x200);level=alloc(0x100);output=alloc(0x140)
w64(obj+0x28,provider);w64(obj+0x18,logger);w64(logger+0x138,level)
uc.reg_write(UC_ARM64_REG_SP,STACK+0xff000);uc.reg_write(UC_ARM64_REG_X30,STOP)
uc.reg_write(UC_ARM64_REG_X0,obj);uc.reg_write(UC_ARM64_REG_X1,output)
uc.emu_start(0x8044918,STOP,count=200000)
if uc.reg_read(UC_ARM64_REG_PC)!=STOP:raise RuntimeError('Instruction budget exhausted')
result=bytes(uc.mem_read(output,0x140));flags=struct.unpack_from('<I',result)[0]
# Execute only the stock override-selection body. Append and snprintf callbacks
# are explicit models; final MAC insertion/buffer compaction are not executed.
nvram_phase=True
nvobj=alloc(0x300);uc.mem_write(nvobj+0x30,result);w64(nvobj+0x18,logger)
uc.reg_write(UC_ARM64_REG_X0,nvobj)
from unicorn.arm64_const import UC_ARM64_REG_X20
uc.reg_write(UC_ARM64_REG_X20,nvobj);uc.reg_write(UC_ARM64_REG_SP,STACK+0xfe000)
uc.emu_start(0x80480c8,STOP,count=200000)
if uc.reg_read(UC_ARM64_REG_PC)!=0x80481bc:raise RuntimeError('Override body did not reach finalization boundary')
modeled.add('NVRAM append and snprintf callbacks; board mode=0; finalization omitted')
portable=helper('calibration',ROOT/'wifi/tools/calibration.py').derive(props)
if overrides!=portable:raise RuntimeError('Portable calibration disagrees with exact-stock model')
receipt={'offline_model_only' :True,'rf_qualified':False,'structure_bytes':len(result),'presence_flags':hex(flags),'property_lookups':lookups,'modeled_callbacks':sorted(modeled),'override_keys':sorted(overrides),'portable_mapping_matches_stock_model':True}
print(json.dumps(receipt,indent=2))

if args.private_output:
 args.private_output.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
 fd=os.open(args.private_output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'wb') as f:f.write(result)
 target=args.private_output.with_suffix('.overrides.json')
 fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:json.dump(overrides,f,indent=2);f.write('\n')
 print('Private structure and modeled overrides written; no firmware command generated.')
