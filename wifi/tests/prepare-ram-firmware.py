#!/usr/bin/env python3
"""Private-input preparation invariants, using synthetic non-device fixtures."""
import hashlib,importlib.util,pathlib,struct,zlib
p=pathlib.Path(__file__).resolve().parents[1]/'tools/prepare-ram-firmware.py'
spec=importlib.util.spec_from_file_location('prepare',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def otp(vendor):
 body=b'\x01\x00M=TEST m=1.0 V='+vendor+b'\0'
 return bytes([0x15,len(body)])+body+b'\xff'
assert m.otp_vendor(otp(b'u'))=='u' and m.otp_vendor(otp(b'm'))=='m'
for raw in (otp(b'x'),otp(b'u')[:-1]+otp(b'm'),bytes([0x15,255,1])):
 try:m.otp_vendor(raw)
 except ValueError:pass
 else:raise AssertionError('Invalid/ambiguous OTP accepted')
fw=bytearray(483328);struct.pack_into('<7I',fw,0,0x30524448,len(fw),0,0x10020,482024,129,0);struct.pack_into('<I',fw,8,zlib.crc32(fw[12:])^0xffffffff)
m.FIRMWARE_SHA=hashlib.sha256(fw).hexdigest()
image,fields=m.prepare(bytes(fw),b'# fixture\nboardtype=0x67e\nboardrev=0x1303\n',bytes([2,0,0,0,0,1]))
assert image[28:482052]==fw[28:482052]
assert len(image)%4==0 and struct.unpack_from('<I',image,4)[0]==len(image)
assert struct.unpack_from('<I',image,24)[0]==len(image)-482052
assert (zlib.crc32(image[12:])^0xffffffff)==struct.unpack_from('<I',image,8)[0]
assert image[482052:].count(b'macaddr=02:00:00:00:00:01\0')==1
for nvram,mac in ((b'boardtype=1\nboardtype=2',bytes([2,0,0,0,0,1])),(b'boardtype=1',bytes(6))):
 try:m.prepare(bytes(fw),nvram,mac)
 except ValueError:pass
 else:raise AssertionError('Invalid NVRAM/MAC accepted')
fw[-1]^=1;m.FIRMWARE_SHA=hashlib.sha256(fw).hexdigest()
try:m.prepare(bytes(fw),b'boardtype=1',bytes([2,0,0,0,0,1]))
except ValueError as error:assert 'CRC' in str(error)
else:raise AssertionError('Corrupt TRX CRC accepted')
print('PASS: exact OTP vendor selection, immutable firmware body, TRX length/CRC, MAC replacement, ambiguity/corruption rejection')
