#!/usr/bin/env python3
"""Read-only J86 suspend readiness report. Never writes /sys/power/state.

A USB/NBD-root session must not suspend: it can lose the root block transport.
Even a passing report is not proof of A7 resume or a physical wake source.
"""
import argparse,json,pathlib,re

def inspect(root):
 def read(path):
  try:return (root/path.lstrip('/')).read_text().strip()
  except OSError:return ''
 states=read('/sys/power/state').split();mem=read('/sys/power/mem_sleep')
 mounts=read('/proc/self/mountinfo');cmdline=read('/proc/cmdline')
 nbd=bool(re.search(r'\bnbd\d+(?:p\d+)?\b',mounts+' '+cmdline))
 return {'states':states,'mem_sleep':mem,'network_block_root_or_mount':nbd,
  'enabled':False,'ready':False,
  'blockers':(['Network block devices must be detached before any suspend experiment'] if nbd else [])+
   (['Suspend is absent from this kernel'] if 'mem' not in states else [])+
   ['A7 resume and wake IRQ are unqualified; physical recovery required']}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=pathlib.Path,default=pathlib.Path('/'));a=p.parse_args()
 print(json.dumps(inspect(a.root),indent=2))
if __name__=='__main__':main()
