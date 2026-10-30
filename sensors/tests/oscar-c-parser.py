#!/usr/bin/env python3
"""Compare the exact kernel receive parser with the independent Python parser."""
import importlib.util,pathlib,random,struct,subprocess,tempfile
root=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('rx',root/'sensors/oscar/receive.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
rng=random.Random(86);stream=bytearray()
for i in range(500):
 size=rng.choice([14,15,127,128,129,255,256]);b=bytearray(rng.randbytes(size));b[:6]=b'ICPA'+bytes([i%256,size%256]);b[10:12]=b'\0\0';struct.pack_into('<H',b,10,m.packet.checksum(b))
 if i%3==0:b[-1]^=1
 stream.extend(rng.randbytes(rng.randrange(33)));stream.extend(b)
r=m.Receiver();frames=[]
for pos in range(0,len(stream),97):frames.extend(v['frame'].hex() for v in r.feed(bytes(stream[pos:pos+97])))
with tempfile.TemporaryDirectory() as tmp:
 binary=pathlib.Path(tmp)/'oscar-rx'
 subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(root/'sensors/tests/oscar-rx.c'),'-o',str(binary)],check=True)
 result=subprocess.run([str(binary)],input=stream,capture_output=True,check=True)
 assert result.stdout.decode().splitlines()==frames
 assert list(map(int,result.stderr.split()))==[len(frames),r.bad_length,r.bad_checksum,r.discarded,len(r.buffer)]
print('Oscar kernel parser: 500 mixed frames/noise cases match Python frames and recovery counters')
