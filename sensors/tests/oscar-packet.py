#!/usr/bin/env python3
"""Synthetic command-frame bounds, parity, corruption and round-trip checks."""
import importlib.util,pathlib,random
p=pathlib.Path(__file__).resolve().parents[1]/'oscar/packet.py'
spec=importlib.util.spec_from_file_location('packet',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
rng=random.Random(86)
for size in [0,1,2,3,31,32,113,114]:
 payload=bytes(rng.randrange(256) for _ in range(size));frame=m.encode_command(3,0xabcd,payload)
 assert len(frame)==14+size and m.decode_command(frame)==(3,0xabcd,payload)
 for offset in [0,5,6,10,12,len(frame)-1]:
  bad=bytearray(frame);bad[offset]^=1
  try:m.decode_command(bytes(bad))
  except ValueError:pass
  else:raise AssertionError('Corrupted frame accepted')
for args in [(-1,0,b''),(256,0,b''),(0,-1,b''),(0,65536,b''),(0,1,bytes(115))]:
 try:m.encode_command(*args)
 except ValueError:pass
 else:raise AssertionError('Invalid command accepted')
# Each span has an independent odd trailing byte in the stock checksum routine.
assert m.checksum(b'\x01',b'\x02')==0xfffc
assert m.checksum(b'\x01\x02')==0xfdfe
print('PASS: Oscar command bounds/parity, independent span checksum, round trips and corruption rejection')
