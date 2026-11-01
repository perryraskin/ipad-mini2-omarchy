#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Exact private A7 firmware setup-dispatch model. No device access.

Allocation/mapping callbacks return synthetic success. Tests dispatch acceptance,
not backing-memory sizes, mapping side effects, DMA or hardware cleanup.
"""
import argparse,hashlib,json,pathlib,struct
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_LR,UC_ARM_REG_PC,UC_ARM_REG_SP
SHA='af3d61851d4a2dd53d7301d945d7ff3f0d94eef2e15947f1de2c9a8982708e33'
def model(blob):
 if hashlib.sha256(blob).hexdigest()!=SHA:raise ValueError('Require exact owner firmware')
 u=Uc(UC_ARCH_ARM,UC_MODE_THUMB);u.mem_map(0,0x80000);u.mem_write(0,blob)
 u.mem_map(0x100000,0x10000);u.mem_map(0x200000,0x10000)
 obj=0x100000;msg=0x101000;stop=0x200000;events=[];replies=[]
 def ret(value):u.reg_write(UC_ARM_REG_R0,value);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def code(mu,pc,size,data):
  if pc in (0x24f4,0x896e,0x2590,0x3c66,0x3cde):
   events.append(pc);ret(1)
  elif pc in (0x7b26,0x7b98):
   replies.append((pc,mu.reg_read(UC_ARM_REG_R2)));ret(0)
  elif not (0x2044<=pc<0x20ea or 0x7050<=pc<0x70aa):raise RuntimeError('Unexpected call '+hex(pc))
 u.hook_add(UC_HOOK_CODE,code)
 accepted={}
 for endpoint,entry in ((0,0x2045),(3,0x7051)):
  accepted[endpoint]={}
  for param in range(256):
   events.clear();replies.clear();u.mem_write(msg,struct.pack('<BBBBI',endpoint,1,3,param,0x1234))
   u.reg_write(UC_ARM_REG_SP,0x10f000);u.reg_write(UC_ARM_REG_LR,stop|1)
   u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,msg)
   u.emu_start(entry,stop,count=1000)
   if u.reg_read(UC_ARM_REG_PC)!=stop or len(replies)!=1:raise RuntimeError('Incomplete dispatch')
   if replies[0]==(0x7b26,0x65):accepted[endpoint][param]=events.copy()
   else:assert replies[0]==(0x7b98,3),(endpoint,param,replies)
 assert set(accepted[0])=={1,2,3,4,11,12,15,16}
 assert set(accepted[3])=={13,14}
 assert accepted[0][1]==accepted[0][2]==[0x24f4]
 assert accepted[0][11]==accepted[0][12]==[0x2590]
 return {str(ep):{hex(p):[hex(x) for x in calls] for p,calls in values.items()} for ep,values in accepted.items()}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('firmware',type=pathlib.Path);a=p.parse_args()
 print(json.dumps(model(a.firmware.read_bytes()),indent=2))
 print('512 offline dispatch cases passed; A7 rejects EP0 0x1a/0x1b; helper effects are mocked.')
