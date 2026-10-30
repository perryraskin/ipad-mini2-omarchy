#!/usr/bin/env python3
"""Opt-in IIO rotation policy. No UART, firmware, MMIO or device-tree writes.

Input is SI acceleration in panel axes: +X right, +Y down, +Z out of glass.
An exact per-board axis mapping must be qualified before attaching an IIO source.
"""
import argparse,json,math,pathlib,subprocess,time
ORIENTATIONS={'down':'portrait','right':'landscape','up':'inverted','left':'landscape-inverted'}
class Policy:
 def __init__(self):self.candidate=None;self.since=None;self.last_time=None;self.applied=None
 def sample(self,x,y,z,now):
  if not all(math.isfinite(v) for v in (x,y,z,now)):raise ValueError('Non-finite acceleration/time')
  if self.last_time is not None and now<=self.last_time:raise ValueError('Non-monotonic sample')
  gap=self.last_time is not None and now-self.last_time>.5
  self.last_time=now
  norm=math.sqrt(x*x+y*y+z*z);dominant=max(abs(x),abs(y))
  # Reject shaking, a nearly flat panel, and diagonal/ambiguous poses.
  if gap or not 7.0<=norm<=12.5 or dominant<6 or abs(abs(x)-abs(y))<2:
   self.candidate=None;self.since=None;return None
  pose=('right' if x>0 else 'left') if abs(x)>abs(y) else ('down' if y>0 else 'up')
  target=ORIENTATIONS[pose]
  if target!=self.candidate:self.candidate=target;self.since=now
  if now-self.since>=.8 and target!=self.applied:return target
  return None
 def acknowledge(self,target):
  if target!=self.candidate:raise ValueError('Unexpected rotation acknowledgment')
  self.applied=target

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--replay',type=pathlib.Path,required=True,help='JSON lines with time,x,y,z in panel SI axes')
 p.add_argument('--apply',action='store_true',help='Explicitly apply qualified input via manual rotation helper')
 a=p.parse_args();policy=Policy()
 if a.apply:
  import os
  if os.geteuid()!=1000 or pathlib.Path('/proc/device-tree/model').read_bytes().rstrip(b'\0')!=b'Apple iPad mini 2 (Cellular)':raise SystemExit('Apply requires tablet user on exact J86')
 with a.replay.open() as stream:
  for line in stream:
   value=json.loads(line);target=policy.sample(*(float(value[k]) for k in ('x','y','z','time')))
   if target:
    if a.apply:subprocess.run(['/home/tablet/.local/bin/j86-rotate',target],check=True,timeout=10)
    policy.acknowledge(target);print(json.dumps({'orientation':target,'applied':a.apply}),flush=True)
if __name__=='__main__':main()
