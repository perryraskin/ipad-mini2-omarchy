#!/usr/bin/env python3
"""Read-only oldstyle NBD server, restricted to the iPad's USB link."""
import errno,os,pathlib,socket,struct,subprocess,sys
path=pathlib.Path(sys.argv[1]).resolve(); bind=sys.argv[2]; peer=sys.argv[3]
port=int(sys.argv[4]) if len(sys.argv)>4 else 10811
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
 server.bind((bind,port));server.listen(1)
 port=server.getsockname()[1]
 print(f'Read-only NBD: {path.name}, {size} bytes; {bind}:{port}; only {peer}',flush=True)
 while True:
  c,addr=server.accept()
  if addr[0]!=peer: c.close();continue
  print('USB client connected',flush=True)
  awake=None
  try:
   with c:
    # Only an active root client needs the assertion. The display may sleep.
    if sys.platform=='darwin':
     try:awake=subprocess.Popen(['/usr/bin/caffeinate','-i','-w',str(os.getpid())],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
     except OSError as error:print('Host idle-sleep assertion failed:',error,flush=True)
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
  finally:
   if awake is not None:
    awake.terminate()
    try:awake.wait(timeout=2)
    except subprocess.TimeoutExpired:awake.kill();awake.wait()
  print('USB client disconnected',flush=True)
