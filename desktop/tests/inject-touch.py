#!/usr/bin/python3
"""Temporary synthetic J86 touchscreen for unattended compositor validation."""
import argparse,fcntl,os,pathlib,struct,time
p=argparse.ArgumentParser(description=__doc__);p.add_argument('x',type=int);p.add_argument('y',type=int);p.add_argument('--hold',type=float,default=.7);p.add_argument('--to-x',type=int);p.add_argument('--to-y',type=int);args=p.parse_args()
assert pathlib.Path('/proc/device-tree/model').read_bytes().rstrip(b'\0')==b'Apple iPad mini 2 (Cellular)'
assert os.geteuid()==0 and 0<=args.x<1536 and 0<=args.y<2048 and 0<=args.hold<=2
fd=os.open('/dev/uinput',os.O_WRONLY|os.O_NONBLOCK);created=False
try:
 for kind in (1,3):fcntl.ioctl(fd,0x40045564,kind)
 fcntl.ioctl(fd,0x40045565,330);fcntl.ioctl(fd,0x4004556e,1)
 for code,maximum in [(0,1535),(1,2047),(47,9),(53,1535),(54,2047),(57,65535)]:
  fcntl.ioctl(fd,0x40045567,code)
  fcntl.ioctl(fd,0x401c5504,struct.pack('H2xiiiiii',code,0,0,maximum,0,0,0))
 fcntl.ioctl(fd,0x405c5503,struct.pack('HHHH80sI',6,0x1234,0x86,1,b'J86 Synthetic Touch (temporary)',0))
 fcntl.ioctl(fd,0x5501);created=True;time.sleep(3)
 def send(items):
  data=b''.join(struct.pack('@llHHi',0,0,t,c,v) for t,c,v in items+[(0,0,0)])
  assert os.write(fd,data)==len(data)
 send([(3,47,0),(3,57,1),(3,53,args.x),(3,54,args.y),(3,0,args.x),(3,1,args.y),(1,330,1)])
 time.sleep(args.hold)
 if args.to_x is not None or args.to_y is not None:
  assert args.to_x is not None and args.to_y is not None and 0<=args.to_x<1536 and 0<=args.to_y<2048
  for step in range(1,13):
   x=round(args.x+(args.to_x-args.x)*step/12);y=round(args.y+(args.to_y-args.y)*step/12)
   send([(3,47,0),(3,53,x),(3,54,y),(3,0,x),(3,1,y)]);time.sleep(.025)
 send([(3,47,0),(3,57,-1),(1,330,0)])
 time.sleep(.3)
 print('Synthetic touch completed; temporary device removed on exit.')
finally:
 if created:fcntl.ioctl(fd,0x5502)
 os.close(fd)
