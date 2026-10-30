#!/usr/bin/env python3
"""Build deterministic source-only GitHub release assets from a clean checkpoint."""
import argparse,gzip,hashlib,io,json,pathlib,re,subprocess,tarfile

def build(root,tag,commit):
 if not re.fullmatch(r'source-checkpoint-[0-9]{8}\.[0-9]+',tag) or not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('Invalid source identity')
 manifest=json.loads((root/'SOURCE-MANIFEST.json').read_text());files={}
 for name,sha in manifest.items():
  p=pathlib.PurePosixPath(name)
  if p.is_absolute() or '..' in p.parts or (root/name).is_symlink():raise ValueError('Unsafe source member')
  data=(root/name).read_bytes()
  if hashlib.sha256(data).hexdigest()!=sha or b'\0' in data:raise ValueError('Source manifest mismatch')
  data.decode('utf-8');files[name]=data
 files['SOURCE-MANIFEST.json']=(root/'SOURCE-MANIFEST.json').read_bytes()
 output=io.BytesIO()
 with gzip.GzipFile(fileobj=output,mode='wb',mtime=0,filename='') as compressed:
  with tarfile.open(fileobj=compressed,mode='w',format=tarfile.USTAR_FORMAT) as archive:
   for name,data in sorted(files.items()):
    member=tarfile.TarInfo(name);member.size=len(data);member.mode=0o644;member.mtime=0;member.uid=member.gid=0
    archive.addfile(member,io.BytesIO(data))
 bundle=output.getvalue()
 receipt={'schema':1,'repository':'perryraskin/ipad-mini2-linux','kind':'source-only','tag':tag,'commit':commit,'boot_qualified':False,'size':len(bundle),'sha256':hashlib.sha256(bundle).hexdigest()}
 return bundle,receipt

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--tag',required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
 root=pathlib.Path(__file__).resolve().parents[1]
 if subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip():raise SystemExit('Release requires a clean committed source checkout')
 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip();bundle,receipt=build(root,a.tag,commit)
 a.output.mkdir(parents=True,exist_ok=False)
 (a.output/'source-checkpoint.tar.gz').write_bytes(bundle);(a.output/'checkpoint.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print('Built source-only checkpoint assets; no device binaries/firmware or activation.')
if __name__=='__main__':main()
