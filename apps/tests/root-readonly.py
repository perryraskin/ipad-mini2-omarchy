#!/usr/bin/env python3
"""Verify actual NBD reads and write rejection against an isolated host fixture."""
import errno,pathlib,re,select,socket,struct,subprocess,sys,tempfile
server=pathlib.Path(__file__).resolve().parents[2]/'serve-root-readonly.py'
with tempfile.TemporaryDirectory() as directory:
 disk=pathlib.Path(directory)/'fixture.ext4';original=bytes(range(256))*16;disk.write_bytes(original)
 process=subprocess.Popen([sys.executable,str(server),str(disk),'127.0.0.1','127.0.0.1','0'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 try:
  assert select.select([process.stdout],[],[],5)[0],'Fixture server did not start'
  line=process.stdout.readline();match=re.search(r'127\.0\.0\.1:(\d+);',line);assert match,line
  with socket.create_connection(('127.0.0.1',int(match[1])),timeout=5) as client:
   def read(n):
    data=b''
    while len(data)<n:
     part=client.recv(n-len(data));assert part;data+=part
    return data
   hello=read(152);magic,_,size,flags=struct.unpack('!8sQQI',hello[:28]);assert magic==b'NBDMAGIC' and size==4096 and flags&2
   def request(kind,handle,body=b''):
    client.sendall(struct.pack('!IHH8sQI',0x25609513,0,kind,handle,128,512)+body)
    magic,error,returned=struct.unpack('!II8s',read(16));assert magic==0x67446698 and returned==handle;return error
   assert request(0,b'READ0001')==0 and read(512)==original[128:640]
   assert request(1,b'WRITE001',b'X'*512)==errno.EROFS
   assert request(0,b'READ0002')==0 and read(512)==original[128:640]
   client.sendall(struct.pack('!IHH8sQI',0x25609513,0,2,b'BYE00001',0,0))
  assert disk.read_bytes()==original,'Read-only server changed its backing file'
 finally:
  process.terminate()
  try:process.wait(timeout=5)
  except subprocess.TimeoutExpired:process.kill();process.wait()
print('PASS: real NBD reads, EROFS on write, unchanged backing file, isolated ephemeral TCP port')
