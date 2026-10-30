#!/usr/bin/env python3
"""Prepare private, owner-extracted exact-J86 touch assets. Never flashes a device."""
import argparse,hashlib,json,pathlib,plistlib,struct
ROOT=pathlib.Path(__file__).resolve().parents[2]
def adt_nodes(data):
 nodes={}
 def parse(offset,parent):
  if offset+8>len(data):raise ValueError('Truncated ADT')
  np,nc=struct.unpack_from('<II',data,offset);offset+=8
  if np>4096 or nc>4096:raise ValueError('Implausible ADT node')
  props={}
  for _ in range(np):
   if offset+36>len(data):raise ValueError('Truncated ADT property')
   key=data[offset:offset+32].split(b'\0',1)[0].decode()
   size=struct.unpack_from('<I',data,offset+32)[0]&0x7fffffff;offset+=36
   if offset+size>len(data):raise ValueError('Truncated ADT value')
   props[key]=data[offset:offset+size];offset+=(size+3)&~3
  path=parent+'/'+props.get('name',b'').split(b'\0',1)[0].decode();nodes[path]=props
  for _ in range(nc):offset=parse(offset,path)
  return offset
 parse(0,'');return nodes

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--mtprops',type=pathlib.Path,required=True)
 parser.add_argument('--adt',type=pathlib.Path,required=True)
 parser.add_argument('--module',type=pathlib.Path,default=ROOT/'touch/native/j86_touch.ko')
 parser.add_argument('--loader',type=pathlib.Path,default=ROOT/'touch/tools/load-once')
 parser.add_argument('--output-dir',type=pathlib.Path,default=ROOT/'private-data/touch')
 parser.add_argument('--manifest',type=pathlib.Path,default=ROOT/'touch/native/assets.json')
 args=parser.parse_args()
 if args.manifest.exists():raise ValueError('Manifest already exists; inspect it before replacing')
 nodes=adt_nodes(args.adt.read_bytes())
 if not {b'J86AP',b'J86'}.intersection(nodes['/device-tree']['compatible'].split(b'\0')):raise ValueError('Not an exact J86 ADT')
 calibration=nodes['/device-tree/arm-io/spi1/multi-touch']['multi-touch-calibration']
 if len(calibration)!=1024 or not any(calibration) or calibration.startswith(b'syscfg/'):raise ValueError('Live, non-placeholder panel calibration is required')
 fw=plistlib.loads(args.mtprops.read_bytes())['C1F14,3']['Constructed Firmware']
 if len(fw)!=57192 or fw[:4]!=bytes.fromhex('18e13001'):raise ValueError('Unexpected J86 firmware packet')
 entries=[]
 for source in (args.module,args.loader):
  if not source.is_file() or source.is_symlink():raise ValueError('Missing locally built module/loader')
 args.output_dir.mkdir(parents=True,exist_ok=True,mode=0o700);args.output_dir.chmod(0o700)
 for name,data,target in [('j86-touch-C1F14-3.bin',fw,'/lib/firmware/j86-touch-C1F14-3.bin'),('j86-touch-panel-cal.bin',calibration,'/lib/firmware/j86-touch-panel-cal.bin')]:
  source=args.output_dir/name
  if source.exists() and source.read_bytes()!=data:raise ValueError('Refusing to replace a different private asset: '+str(source))
  source.write_bytes(data);source.chmod(0o600)
  entries.append({'source':str(source.resolve()),'target':target,'sha256':hashlib.sha256(data).hexdigest()})
 for source,target in [(args.module,'/tmp/j86_touch.ko'),(args.loader,'/tmp/load-once')]:
  entries.append({'source':str(source.resolve()),'target':target,'sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
 args.manifest.parent.mkdir(parents=True,exist_ok=True)
 args.manifest.write_text(json.dumps(entries,indent=2)+'\n');args.manifest.chmod(0o600)
 print('Prepared private firmware/calibration and local integrity manifest. Do not publish these files.')
if __name__=='__main__':main()
