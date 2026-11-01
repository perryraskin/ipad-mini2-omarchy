#!/usr/bin/env python3
"""Offline exact-owner A7 SmartIO startup model, stopping at READY.

Zero-filled MMIO and synthetic timer reads are explicit assumptions. Unicorn
executes ARM/Thumb startup and its MMU setup; no device or firmware upload occurs.
This enumerates startup writes, not a safe live boot/restore recipe.
"""
import argparse,collections,hashlib,json,pathlib,struct
from unicorn import Uc,UcError,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE,UC_HOOK_MEM_UNMAPPED
from unicorn.arm_const import UC_ARM_REG_CPSR,UC_ARM_REG_PC,UC_ARM_REG_R0,UC_ARM_REG_R1
from capstone import Cs,CS_ARCH_ARM,CS_MODE_ARM,CS_MODE_THUMB
SHA='af3d61851d4a2dd53d7301d945d7ff3f0d94eef2e15947f1de2c9a8982708e33'

def model(blob):
 if len(blob)!=0x71550 or hashlib.sha256(blob).hexdigest()!=SHA:
  raise ValueError('Require the exact privately extracted owner J86 firmware')
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x80000);u.mem_write(0,blob)
 writes=[];reads=collections.Counter();pages=set();timer_reads=[];ready=False
 decoders={False:Cs(CS_ARCH_ARM,CS_MODE_ARM),True:Cs(CS_ARCH_ARM,CS_MODE_THUMB)}
 def unmapped(mu,access,address,size,value,user):
  if not (0x20a000000<=address<0x20f000000):
   raise RuntimeError('Unexpected model access: '+hex(address))
  page=address&~4095
  if page not in pages:mu.mem_map(page,4096);pages.add(page)
  return True
 def read(mu,access,address,size,value,user):
  if address>=0x20a000000:reads[address]+=1
 def write(mu,access,address,size,value,user):
  nonlocal ready
  if address>=0x20a000000:writes.append((mu.reg_read(UC_ARM_REG_PC),address,size,value))
  if address==0x20ae00bb4:
   if size!=4 or value!=0 or len(writes)<2 or writes[-2][1:]!=(0x20ae00bb0,4,0x036d0000):
    raise RuntimeError('Unexpected startup mailbox message')
   ready=True;mu.emu_stop()
 def code(mu,addr,size,user):
  thumb=bool(mu.reg_read(UC_ARM_REG_CPSR)&32)
  i=next(decoders[thumb].disasm(bytes(mu.mem_read(addr,size)),addr),None)
  if not i:raise RuntimeError('Undecoded instruction')
  if i.mnemonic=='mrrc' and 'c14' in i.op_str:
   if i.op_str!='p15, #0, r0, r1, c14':raise RuntimeError('Unknown timer read')
   timer_reads.append(addr);mu.reg_write(UC_ARM_REG_R0,len(timer_reads)*1000)
   mu.reg_write(UC_ARM_REG_R1,0);mu.reg_write(UC_ARM_REG_PC,(addr+size)|int(thumb))
  if i.mnemonic in ('wfi','wfe'):raise RuntimeError('Unexpected idle before READY')
 u.hook_add(UC_HOOK_MEM_UNMAPPED,unmapped);u.hook_add(UC_HOOK_MEM_READ,read)
 u.hook_add(UC_HOOK_MEM_WRITE,write);u.hook_add(UC_HOOK_CODE,code)
 u.emu_start(0,0x7ffff,count=500000)
 if not ready:raise RuntimeError('Instruction budget exhausted before READY')
 # Exact reset function touches both DMA directions on sixteen peripheral bases.
 bases=[0x20a080000,0x20a084000,0x20a088000,0x20a08c000,
        0x20a0a0000,0x20a0a4000,0x20a0a8000,0x20a0ac000,
        0x20a0b0000,0x20a0b4000,0x20a0b8000,0x20a0c0000,
        0x20a0c4000,0x20a0c8000,0x20a0cc000,0x20a0d0000]
 controls={base+offset for base in bases for offset in (0x1010,0x1810)}
 for address in controls:
  actual=[(pc,size,value) for pc,a,size,value in writes if a==address]
  assert actual==[(0x15f0,4,0),(0x15f8,4,0),(0x1622,4,1)], (hex(address),actual)
 pmgr=[x for x in writes if 0x20e000000<=x[1]<0x20f000000]
 assert not pmgr
 assert len(writes)==121
 return dict(offline_model_only=True,ready_observed_in_model=True,
  modeled_mmio='zero-filled; no hardware side effects',synthetic_timer_reads=len(timer_reads),
  startup_mmio_writes=len(writes),peripheral_dma_controls_reset=len(controls),
  peripheral_bases=[hex(x) for x in bases],pmgr_writes_before_ready=len(pmgr),
  live_cleanup_qualified=False,playback_qualified=False,
  limitation='Stops at READY; no post-READY behavior, interrupts, automatic gating or DMA effects modeled.')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('firmware',type=pathlib.Path);a=p.parse_args()
 print(json.dumps(model(a.firmware.read_bytes()),indent=2))
