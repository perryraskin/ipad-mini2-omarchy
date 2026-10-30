#!/usr/bin/env python3
import hashlib,importlib.util,pathlib,struct,zlib
spec=importlib.util.spec_from_file_location('stage',pathlib.Path(__file__).resolve().parents[1]/'tools/stage-driver-firmware.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
# Synthetic payload contains no firmware or real device identifiers.
nv=b'boardtype=0x67e\0boardrev=0x1303\0\0';blob=bytearray(struct.pack('<7I',0x30524448,28+482024+len(nv),0,0x10020,482024,0,len(nv))+bytes(482024)+nv)
struct.pack_into('<I',blob,8,zlib.crc32(blob[12:])^0xffffffff)
r={'rf_qualified':False,'otp_vendor':'u','stock_nvram':'seyval-u-kk.txt','expected_boardtype':0x67e,'expected_boardrev':0x1303,'size':len(blob),'sha256':hashlib.sha256(blob).hexdigest()}
assert m.validate(blob,r)['enabled'] is False
for key,value in [('rf_qualified',True),('otp_vendor','m'),('expected_boardrev',0),('sha256','0'*64)]:
 bad=dict(r);bad[key]=value
 try:m.validate(blob,bad)
 except ValueError:pass
 else:raise AssertionError(key)
blob[-1]^=1;r['sha256']=hashlib.sha256(blob).hexdigest()
try:m.validate(blob,r)
except ValueError:pass
else:raise AssertionError('Bad CRC accepted')
print('Driver staging: exact board, receipt and TRX integrity guards passed')
