#!/usr/bin/env python3
"""Read-only oldstyle NBD server, restricted to the iPad's USB link."""
import errno,os,pathlib,socket,struct,sys
path=pathlib.Path(sys.argv[1]).resolve(); bind=sys.argv[2]; peer=sys.argv[3]
fd=os.open(path,os.O_RDONLY); size=os.fstat(fd).st_size
assert size%4096==0

def recv_exact(c,n):
 out=bytearray()
 while len(out)<n:
  b=c.recv(n-len(out))
  if not b: raise EOFError
  out.extend(b)
 return bytes(out)

with socket.socket() as server:
 server.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
 server.bind((bind,10811));server.listen(1)
 print(f'Read-only NBD: {path.name}, {size} bytes; {bind}:10811; only {peer}',flush=True)
 while True:
  c,addr=server.accept()
  if addr[0]!=peer: c.close();continue
  print('USB client connected',flush=True)
  try:
   with c:
    c.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
    c.sendall(struct.pack('!8sQQI',b'NBDMAGIC',0x420281861253,size,3)+bytes(124))
    while True:
     magic,flags,kind,handle,offset,length=struct.unpack('!IHH8sQI',recv_exact(c,28))
     if magic!=0x25609513:raise ValueError('Bad request magic')
     if kind==2:break
     error=0;data=b''
     if kind==1:
      if length>32*1024*1024:raise ValueError('Oversized write rejected')
      recv_exact(c,length);error=errno.EROFS
     elif kind==0:
      if length>32*1024*1024 or offset+length>size:error=errno.EINVAL
      else:
       data=os.pread(fd,length,offset)
       if len(data)!=length: error=errno.EIO;data=b''
     else:error=errno.EROFS
     c.sendall(struct.pack('!II8s',0x67446698,error,handle)+data)
  except (EOFError,ConnectionError,OSError,ValueError) as e:print(type(e).__name__,str(e),flush=True)
  print('USB client disconnected',flush=True)
