#!/usr/bin/env python3
"""Prepare private exact-J86 TRX+NVRAM for a RAM-only, RF-disabled qualification probe.

Does not flash or connect. Optional exact-board calibration remains RF-unqualified;
this artifact must not be used to qualify scanning, association or transmission.
"""
import argparse,hashlib,importlib.util,json,os,pathlib,re,struct,zlib
ROOT=pathlib.Path(__file__).resolve().parents[2]
FIRMWARE_SHA='75e6818842d0bd239029b9b954698c95c76e7aed4717a3376e980469dd89b64a'
VARIANTS={'m':('seyval-m-mt.txt','a812a108b35c90f723dee449a7de4077016fe3c5bb57da6d62f57d2e5d5158f2',0x694),'u':('seyval-u-kk.txt','d5d11800a0ecbf361aa1beeb59b03728e7f75ceb431ad12104b4a89c7a3fad0c',0x67e)}
def otp_vendor(raw):
 pos=0;vendors=[]
 while pos<len(raw):
  tag=raw[pos];pos+=1
  if tag==255:break
  if not tag:continue
  if pos>=len(raw):raise ValueError('Truncated OTP tuple')
  size=raw[pos];pos+=1
  if pos+size>len(raw):raise ValueError('OTP tuple outside buffer')
  if tag==0x15:
   vendors.extend(m.decode() for m in re.findall(rb'(?:^|[ \0])V=([mu])(?=[ \0\xff]|$)',raw[pos:pos+size]))
  pos+=size
 if len(vendors)!=1:raise ValueError('Require one exact OTP vendor tag; never guess an NVRAM variant')
 return vendors[0]
def prepare(firmware,nvram,mac,calibration_props=None):
 magic,length,crc,flags,fwlength,jump,nvlength=struct.unpack_from('<7I',firmware)
 if hashlib.sha256(firmware).hexdigest()!=FIRMWARE_SHA or (magic,length,flags,fwlength,nvlength)!=(0x30524448,483328,0x10020,482024,0):raise ValueError('Unexpected stock firmware')
 if (zlib.crc32(firmware[12:])^0xffffffff)!=crc:raise ValueError('Stock TRX CRC mismatch')
 if len(mac)!=6 or not any(mac) or mac==bytes([255])*6 or mac[0]&1:raise ValueError('Require exact live unicast Wi-Fi MAC')
 fields={}
 for line in nvram.decode('ascii').splitlines():
  line=line.split('#',1)[0].strip()
  if not line:continue
  if '=' not in line:raise ValueError('Invalid NVRAM field')
  key,value=line.split('=',1);key=key.strip();value=value.strip()
  if key in fields or not re.fullmatch('[A-Za-z0-9_]+',key) or '\0' in value:raise ValueError('Invalid/duplicate NVRAM field')
  fields[key]=value
 if calibration_props is not None:
  spec=importlib.util.spec_from_file_location('j86_calibration',ROOT/'wifi/tools/calibration.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  fields.update(module.derive(calibration_props))
 fields['macaddr']=':'.join('%02x'%x for x in mac)
 variables=b'\0'.join((k+'='+v).encode('ascii') for k,v in fields.items())+b'\0\0'
 variables+=bytes((-len(variables))%4)
 if not 0<len(variables)<=8192:raise ValueError('NVRAM exceeds reviewed bounds')
 image=bytearray(firmware[:28+fwlength])+variables
 struct.pack_into('<I',image,4,len(image));struct.pack_into('<I',image,24,len(variables))
 struct.pack_into('<I',image,8,zlib.crc32(image[12:])^0xffffffff)
 return bytes(image),fields

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--firmware-dir',type=pathlib.Path,required=True);p.add_argument('--live-adt',type=pathlib.Path,required=True);p.add_argument('--otp',type=pathlib.Path,required=True);p.add_argument('--include-calibration',action='store_true',help='Apply offline stock-model-validated DT mapping; RF remains unqualified');p.add_argument('--output-dir',type=pathlib.Path,default=ROOT/'private-data/wifi-ram-probe');a=p.parse_args()
 spec=importlib.util.spec_from_file_location('adt',ROOT/'touch/tools/prepare-assets.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 nodes=m.adt_nodes(a.live_adt.read_bytes());assert b'J86AP' in nodes['/device-tree']['compatible'].split(b'\0')
 props=nodes['/device-tree/arm-io/usb-complex/usb-ehci1/wlan']
 if props['module-instance'].rstrip(b'\0')!=b'seyval':raise ValueError('Unexpected exact-board module instance')
 vendor=otp_vendor(a.otp.read_bytes());name,expected,boardtype=VARIANTS[vendor]
 nvram=(a.firmware_dir/name).read_bytes()
 if hashlib.sha256(nvram).hexdigest()!=expected:raise ValueError('Unexpected stock NVRAM variant')
 image,fields=prepare((a.firmware_dir/'seyval.trx').read_bytes(),nvram,props['local-mac-address'],props if a.include_calibration else None)
 if int(fields['boardtype'],0)!=boardtype:raise ValueError('Stock variant boardtype mismatch')
 a.output_dir.mkdir(parents=True,exist_ok=True,mode=0o700);a.output_dir.chmod(0o700)
 target=a.output_dir/'j86-wifi-seyval-configured-probe.trx'
 fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'wb') as f:f.write(image)
 receipt={'purpose':'RAM-only RF-disabled probe','rf_qualified':False,'calibration_overrides_applied':a.include_calibration,'otp_vendor':vendor,'stock_nvram':name,'expected_boardtype':boardtype,'expected_boardrev':int(fields['boardrev'],0),'source':str(target.resolve()),'sha256':hashlib.sha256(image).hexdigest(),'size':len(image)}
 fd=os.open(a.output_dir/'manifest.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:json.dump(receipt,f,indent=2);f.write('\n')
 print('Prepared private',len(image),'byte RAM-only image using OTP vendor',vendor,'and',name)
 print('RF remains unqualified. Calibration overrides applied:',a.include_calibration,'. Private values and integrity receipt stay local.')
if __name__=='__main__':main()
