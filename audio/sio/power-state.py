#!/usr/bin/env python3
"""Decode SIO PMGR evidence offline. Never grants MMIO or firmware ownership."""
import argparse,json
RESET=1<<31
AUTO_ENABLE=1<<28
MIN_STATE=0xf<<16
PARENT_OFF=1<<11
DEV_DISABLE=1<<10
# PS_AUTO, PS_ACTUAL and historical gating flags are observations, not control
# fields. This mask follows Linux's Apple PMGR provider; not a write recipe.
CONTROL_MASK=RESET|AUTO_ENABLE|MIN_STATE|DEV_DISABLE|0xf
STATUS_MASK=(0xf<<24)|PARENT_OFF|(3<<8)|0xf0

def decode(value):
 if not isinstance(value,int) or isinstance(value,bool) or not 0<=value<=0xffffffff:
  raise ValueError('Require an unsigned 32-bit PMGR value')
 target=value&15;actual=(value>>4)&15;auto=(value>>24)&15
 if value&(RESET|DEV_DISABLE|PARENT_OFF):state='blocked'
 elif target==actual==15:state='active'
 elif target==actual==0:state='off'
 elif value&AUTO_ENABLE and target==15 and actual==4 and auto==4:
  state='consistent-with-auto-clock-gating'
 else:state='unresolved'
 return dict(state=state,target=target,actual=actual,auto_state=auto,
             auto_enabled=bool(value&AUTO_ENABLE),
             clock_gated_history=bool(value&(1<<9)),
             power_gated_history=bool(value&(1<<8)))

def compare(before,after):
 a,b=decode(before),decode(after)
 return dict(before=a,after=b,control_fields_unchanged=not bool((before^after)&CONTROL_MASK),
             exact_word_unchanged=before==after,
             unclassified_bits_changed=bool((before^after)&~(CONTROL_MASK|STATUS_MASK)),
             restoration_qualified=False,
             note='Power decoding alone cannot establish CPU, queue, remap, DMA or IRQ restoration.')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('before',type=lambda s:int(s,0));p.add_argument('after',type=lambda s:int(s,0));a=p.parse_args()
 print(json.dumps(compare(a.before,a.after),indent=2))
