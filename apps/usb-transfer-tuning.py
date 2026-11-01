#!/usr/bin/python3
"""Bound USB NBD writes and disable TCP segmentation offload for testing."""
import ctypes,fcntl,json,pathlib,socket,struct
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);before={}
for name,get,set in [('tso',0x1e,0x1f),('gso',0x23,0x24),('gro',0x2b,0x2c)]:
 data=(ctypes.c_uint32*2)(get,0)
 arg=struct.pack('16sP16x',b'usb0',ctypes.addressof(data))
 try:
  fcntl.ioctl(s.fileno(),0x8946,arg);before[name]=data[1]
  if before[name]:
   data[0]=set;data[1]=0;fcntl.ioctl(s.fileno(),0x8946,arg)
  data[0]=get;fcntl.ioctl(s.fileno(),0x8946,arg)
  if data[1]:raise RuntimeError(name+' remained enabled')
  print(name,before[name],'->0 verified')
 except OSError as error:
  if name in ('tso','gso'):raise RuntimeError('USB write transport requires '+name+' off') from error
  print(name,error)
p=pathlib.Path('/run/j86-usb-offload-before.json')
if not p.exists():p.write_text(json.dumps(before)+'\n')
pathlib.Path('/sys/block/nbd3/queue/max_sectors_kb').write_text('4\n')
