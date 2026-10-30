#!/usr/bin/env python3
"""Stage an inactive private brcmfmac candidate directory on the host only.

This does not copy into a rootfs, initramfs or device. Firmware acceptance and RF
behavior under brcmfmac remain unqualified even when probe firmware boot passed.
"""
import argparse,hashlib,json,os,pathlib,struct,zlib
NAME='brcm/brcmfmac43241b5-j86.bin'
def validate(blob,receipt):
 blob=bytes(blob)
 if receipt.get('rf_qualified') is not False or receipt.get('otp_vendor')!='u' or receipt.get('stock_nvram')!='seyval-u-kk.txt':raise ValueError('Require exact J86 vendor-u unqualified receipt')
 if (receipt.get('expected_boardtype'),receipt.get('expected_boardrev'))!=(0x67e,0x1303):raise ValueError('Unexpected board')
 if receipt.get('size')!=len(blob) or receipt.get('sha256')!=hashlib.sha256(blob).hexdigest():raise ValueError('Receipt integrity failure')
 if len(blob)<28:raise ValueError('Short TRX')
 magic,size,crc,flags,fwsize,jump,nvsize=struct.unpack_from('<7I',blob)
 if magic!=0x30524448 or size!=len(blob) or flags!=0x10020 or fwsize!=482024 or not 0<nvsize<=8192 or 28+fwsize+nvsize!=size:raise ValueError('Unexpected TRX layout')
 if zlib.crc32(blob[12:])^0xffffffff!=crc:raise ValueError('TRX CRC mismatch')
 fields={}
 for item in blob[28+fwsize:].rstrip(b'\0').split(b'\0'):
  if b'=' not in item:raise ValueError('Malformed NVRAM')
  k,v=item.split(b'=',1)
  if k in fields:raise ValueError('Duplicate NVRAM')
  fields[k]=v
 if int(fields.get(b'boardtype',b'0'),0)!=0x67e or int(fields.get(b'boardrev',b'0'),0)!=0x1303:raise ValueError('NVRAM board mismatch')
 return {'name':NAME,'sha256':hashlib.sha256(blob).hexdigest(),'size':len(blob),'enabled':False,'rf_qualified':False,'autostart':False,'driver_boot_tested':False}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepared-dir',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
 receipt=json.loads((a.prepared_dir/'manifest.json').read_text())
 blob=(a.prepared_dir/'j86-wifi-seyval-configured-probe.trx').read_bytes();result=validate(blob,receipt)
 # No absolute source paths or identifying NVRAM values in the derived receipt.
 a.output.mkdir(mode=0o700,parents=False,exist_ok=False)
 target=a.output/NAME;target.parent.mkdir(mode=0o700)
 fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'wb') as f:f.write(blob)
 fd=os.open(a.output/'stage.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:json.dump(result,f,indent=2);f.write('\n')
 print('Private inactive firmware stage verified; no activation or RF qualification.')
if __name__=='__main__':main()
