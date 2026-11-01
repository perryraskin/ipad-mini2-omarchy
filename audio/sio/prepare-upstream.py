#!/usr/bin/env python3
"""Assemble pinned public SIO sources and the experimental patch; never builds/loads."""
import argparse,base64,hashlib,json,pathlib,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=pathlib.Path,required=True);args=p.parse_args()
if args.output.exists():raise SystemExit('Refusing existing output tree')
meta=json.loads((ROOT/'audio/sio/upstream.json').read_text())
with tempfile.TemporaryDirectory(prefix='j86-upstream-sio-') as temporary:
 patches=[]
 for entry in meta['patches']:
  api=f"repos/{meta['repo']}/contents/{entry['path']}?ref={meta['commit']}"
  reply=json.loads(subprocess.check_output(['gh','api',api]));data=base64.b64decode(reply['content'])
  if hashlib.sha256(data).hexdigest()!=entry['sha256']:raise SystemExit('Upstream source checksum mismatch')
  path=pathlib.Path(temporary)/pathlib.Path(entry['path']).name;path.write_bytes(data);patches.append(path)
 args.output.mkdir(parents=True)
 for patch in [*patches,ROOT/'audio/sio/patches/0001-j86-iop-v1-experimental.patch',ROOT/'audio/sio/patches/0002-j86-preserve-inherited-remap.patch']:
  subprocess.run(['git','-C',str(args.output),'apply','--include=drivers/soc/apple/apple-sio-core.c','--include=drivers/dma/apple-sio-dma.c','--include=include/linux/soc/apple/sio.h',str(patch.resolve())],check=True)
print('Assembled pinned public SIO sources with experimental J86 patch. Nothing built, staged or booted.')
