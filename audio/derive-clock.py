#!/usr/bin/env python3
"""Offline J86 clock-ID lookup model using an owner's live boot ADT.

Executes stock AppleARMIODevice and AppleS5L8960X frequency methods in RAM.
Only boot-declared rates are recovered; no clock is measured or programmed.
"""
import argparse,hashlib,importlib.util,pathlib,struct
from unicorn import Uc,UcError,UC_ARCH_ARM64,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm64_const import UC_ARM64_REG_X0,UC_ARM64_REG_X1,UC_ARM64_REG_X30,UC_ARM64_REG_SP,UC_ARM64_REG_PC
ROOT=pathlib.Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('kernelcache',type=pathlib.Path);p.add_argument('--adt',required=True,type=pathlib.Path);a=p.parse_args()
data=a.kernelcache.read_bytes()
if hashlib.sha256(data).hexdigest()!='d173a651d02329a02d2f23c2859e1e54308a5e94da86ba729777efeb3503da08':raise SystemExit('Exact stock cache required')
b=a.adt.read_bytes();nodes={}
def parse(o,parent,depth=0):
 if depth>32 or o+8>len(b):raise ValueError('Invalid ADT node')
 np,nc=struct.unpack_from('<II',b,o);o+=8
 if np>4096 or nc>4096:raise ValueError('Invalid ADT counts')
 props={}
 for _ in range(np):
  if o+36>len(b):raise ValueError('Truncated ADT property')
  name=b[o:o+32].split(b'\0')[0].decode();n=struct.unpack_from('<I',b,o+32)[0]&0x7fffffff;o+=36
  if o+n>len(b) or name in props:raise ValueError('Invalid ADT property')
  props[name]=b[o:o+n];o+=(n+3)&~3
 path=parent+'/'+props.get('name',b'').split(b'\0')[0].decode()
 if path in nodes:raise ValueError('Duplicate ADT node')
 nodes[path]=props
 for _ in range(nc):o=parse(o,path,depth+1)
 return o
parse(0,'')
if not set(nodes['/device-tree']['compatible'].split(b'\0'))&{b'J86',b'J86AP'}:raise SystemExit('J86 ADT required')
def words(blob):
 if len(blob)%4:raise ValueError('Unaligned clock property')
 return struct.unpack('<'+'I'*(len(blob)//4),blob)
rates=words(nodes['/device-tree/arm-io']['clock-frequencies'])
# Stock SoC initializer admits 61 words and stores each as the first u64
# in a 0x48-byte record. Later live ADT padding is not another clock bank.
if len(rates)<61:raise SystemExit('Live clock table missing; stock placeholders are insufficient')
spec=importlib.util.spec_from_file_location('prelink',ROOT/'research/read-prelink.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
_,segments,data=m.prelink(a.kernelcache);u=Uc(UC_ARCH_ARM64,UC_MODE_ARM)
for name,va,vs,fo,fs in segments:
 if not vs:continue
 base=va&0xffffffff;lo=base&~4095;end=(base+vs+4095)&~4095
 try:u.mem_map(lo,end-lo)
 except UcError:pass
 blob=bytearray(data[fo:fo+fs])
 if name!='__TEXT_EXEC':
  for n in range(0,len(blob)-7,8):
   value=struct.unpack_from('<Q',blob,n)[0];canonical=value|0xffff000000000000
   if any(v<=canonical<v+size for _,v,size,_,_ in segments if size):struct.pack_into('<Q',blob,n,value&0xffffffff)
 if blob:u.mem_write(base,bytes(blob))
HEAP=0x10000000;STACK=0x20000000;STOP=0x50000000
for base in (HEAP,STACK,STOP):u.mem_map(base,0x10000)
def w32(p,v):u.mem_write(p,struct.pack('<I',v))
def w64(p,v):u.mem_write(p,struct.pack('<Q',v))
wrapper=HEAP;expert=HEAP+0x1000;table=HEAP+0x2000;ids=HEAP+0x4000
w64(wrapper,0x74058f8);w64(wrapper+0x88,expert);w64(wrapper+0x98,ids)
w64(expert,0x7510698);w32(expert+0xf0,61);w64(expert+0xf8,table)
for index,rate in enumerate(rates[:61]):w64(table+index*0x48,rate)
def code(mu,address,size,user):
 if not (0x7d48498<=address<=0x7d484c4 or 0x82c1a58<=address<=0x82c1a8c or 0x7d47ed8<=address<=0x7d47f2c or address==STOP):
  raise RuntimeError('Unexpected clock-model execution '+hex(address))
u.hook_add(UC_HOOK_CODE,code)
def call(fn,obj,index):
 u.reg_write(UC_ARM64_REG_X0,obj);u.reg_write(UC_ARM64_REG_X1,index);u.reg_write(UC_ARM64_REG_X30,STOP);u.reg_write(UC_ARM64_REG_SP,STACK+0xf000)
 u.emu_start(fn,STOP,count=1000)
 if u.reg_read(UC_ARM64_REG_PC)!=STOP:raise RuntimeError('Clock model instruction bound')
 return u.reg_read(UC_ARM64_REG_X0)
for device in ('nco','uart4'):
 clocks=words(nodes['/device-tree/arm-io/'+device]['clock-ids']);w32(wrapper+0x90,len(clocks))
 for index,clock in enumerate(clocks):w32(ids+index*4,clock)
 for index,clock in enumerate(clocks):
  if not 256<=clock<317:continue # Do not invent the inherited crystal-frequency table.
  rate=call(0x7d48498,wrapper,index);assert rate==rates[clock-256]
  print(device,'index',index,'clock-id',hex(clock),'boot-declared-Hz',rate)
 assert call(0x7d48498,wrapper,len(clocks))==0
# Out-of-range SoC IDs fall back to the modeled empty inherited table.
for clock in (0,255,317,0xffffffff):assert call(0x82c1a58,expert,clock)==0
print('PASS: stock wrapper/index and SoC clock lookup, invalid-index and fallback checks; no hardware access')
