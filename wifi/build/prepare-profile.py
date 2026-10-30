#!/usr/bin/env python3
"""Prepare an inactive candidate boot profile; never boots or replaces assets."""
import argparse,hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--profile',choices=['candidate','audio-candidate'],default='candidate');args=parser.parse_args()
directory='audio/build/candidate' if args.profile=='audio-candidate' else 'wifi/build/candidate'
release='7.0.12-j86-audio2' if args.profile=='audio-candidate' else '7.0.12-j86-wifi1'
candidate=ROOT/directory
assert (candidate/'kernel.release').read_text().strip()==release
assert 'CONFIG_ARM64_4K_PAGES=y' in (candidate/'kernel.config').read_text()
files={name:hashlib.sha256((candidate/name).read_bytes()).hexdigest() for name in ('j86-ramboot.bin','evdev.ko','j86_touch.ko','j86_hsic_range.ko','j86_wifi_host.ko')}
old=json.loads((ROOT/'touch/native/assets.json').read_text())
manifest=[dict(e) for e in old]
for e in manifest:
 if e['target']=='/tmp/j86_touch.ko':e.update(source=directory+'/j86_touch.ko',sha256=files['j86_touch.ko'])
private=ROOT/('private-data/'+args.profile+'-touch-assets.json');private.parent.mkdir(exist_ok=True,mode=0o700);private.write_text(json.dumps(manifest,indent=2)+'\n');private.chmod(0o600)
profile={'board':'J86','kernel_release':release,'page_size':4096,'boot_tested':False,'payload':directory+'/j86-ramboot.bin','evdev':directory+'/evdev.ko','touch_manifest':str(private.relative_to(ROOT)),'sha256':{directory+'/'+k:v for k,v in files.items()}}
profile['wireless']={'hsic_module':directory+'/j86_hsic_range.ko','host_module':directory+'/j86_wifi_host.ko','host_starts_disabled':True,'firmware_qualified':False,'autostart':False}
if args.profile=='audio-candidate':profile['experimental']={'sio_firmware_boot':False,'mca_bench':False,'oscar_attach':False,'wireless_firmware':False,'installer_qualified':False,'suspend_qualified':False}
(candidate/'boot-profile.json').write_text(json.dumps(profile,indent=2)+'\n')
print('Prepared candidate profile only. Default boot assets and live device unchanged.')
