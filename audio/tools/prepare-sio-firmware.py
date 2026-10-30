#!/usr/bin/env python3
"""Extract exact owner J86 SIO firmware privately; never stages, loads or boots it."""
import argparse,hashlib,importlib.util,json,os,pathlib,struct
ROOT=pathlib.Path(__file__).resolve().parents[2]
CACHE_SHA='d173a651d02329a02d2f23c2859e1e54308a5e94da86ba729777efeb3503da08'
def extract(path):
 blob=path.read_bytes()
 if hashlib.sha256(blob).hexdigest()!=CACHE_SHA:raise ValueError('Require exact iPad4,5 16H88 owner kernelcache')
 spec=importlib.util.spec_from_file_location('prelink',ROOT/'research/read-prelink.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 info,segments,_=m.prelink(path)
 drivers=[k for k in info['_PrelinkInfoDictionary'] if k.get('CFBundleIdentifier')=='com.apple.driver.AppleS5L8960XSmartIO']
 if len(drivers)!=1 or drivers[0].get('ModuleIndex')!=99:raise ValueError('Unexpected exact-stock SIO module identity')
 def offset(address,size):
  matches=[o+address-v for _,v,_,o,fs in segments if v<=address and address+size<=v+fs]
  if len(matches)!=1:raise ValueError('No unique file-backed mapping')
  return matches[0]
 sections=[];pos=32
 for _ in range(struct.unpack_from('<I',blob,16)[0]):
  cmd,size=struct.unpack_from('<II',blob,pos)
  if cmd==25:
   segment=blob[pos+8:pos+24].rstrip(b'\0')
   for index in range(struct.unpack_from('<I',blob,pos+64)[0]):
    s=pos+72+80*index;name=blob[s:s+16].rstrip(b'\0')
    if (segment,name)==(b'__DATA',b'__firmware'):sections.append(struct.unpack_from('<QQI',blob,s+32))
  pos+=size
 if len(sections)!=1:raise ValueError('No unique firmware section')
 address,size,fileoff=sections[0]
 # Exact SmartIO constructor loads this global and passes length0x71550 to
 # its firmware memory descriptor. Resolve/canonicalize the tagged data pointer.
 pointer=struct.unpack_from('<Q',blob,offset(0xfffffff0087fdb28,8))[0]|0xffff000000000000
 if size!=0x71550 or pointer!=address or fileoff!=offset(address,size):raise ValueError('Firmware section does not match exact driver reference/length')
 return blob[fileoff:fileoff+size]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('kernelcache',type=pathlib.Path);p.add_argument('--output-dir',type=pathlib.Path,default=ROOT/'private-data/sio');args=p.parse_args()
 firmware=extract(args.kernelcache);args.output_dir.mkdir(parents=True,exist_ok=True,mode=0o700);args.output_dir.chmod(0o700)
 target=args.output_dir/'s5l8960x-smartio.bin';receipt={'board':'J86','stock_cache_sha256':CACHE_SHA,'bytes':len(firmware),'sha256':hashlib.sha256(firmware).hexdigest(),'boot_qualified':False,'staged':False}
 for path,data in [(target,firmware),(args.output_dir/'manifest.json',(json.dumps(receipt,indent=2)+'\n').encode())]:
  fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,'wb') as f:f.write(data)
 print('Prepared private exact J86 SIO firmware:',len(firmware),'bytes; no device access or firmware boot.')
if __name__=='__main__':main()
