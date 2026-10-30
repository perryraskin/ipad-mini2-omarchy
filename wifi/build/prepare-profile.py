#!/usr/bin/env python3
"""Prepare an inactive candidate boot profile; never boots or replaces assets."""
import hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[2];candidate=ROOT/'wifi/build/candidate'
assert (candidate/'kernel.release').read_text().strip()=='7.0.12-j86-wifi1'
assert 'CONFIG_ARM64_4K_PAGES=y' in (candidate/'kernel.config').read_text()
files={name:hashlib.sha256((candidate/name).read_bytes()).hexdigest() for name in ('j86-ramboot.bin','evdev.ko','j86_touch.ko','j86_hsic_range.ko','j86_wifi_host.ko')}
old=json.loads((ROOT/'touch/native/assets.json').read_text())
manifest=[dict(e) for e in old]
for e in manifest:
 if e['target']=='/tmp/j86_touch.ko':e.update(source='wifi/build/candidate/j86_touch.ko',sha256=files['j86_touch.ko'])
private=ROOT/'private-data/candidate-touch-assets.json';private.parent.mkdir(exist_ok=True,mode=0o700);private.write_text(json.dumps(manifest,indent=2)+'\n');private.chmod(0o600)
profile={'board':'J86','kernel_release':'7.0.12-j86-wifi1','page_size':4096,'boot_tested':False,'payload':'wifi/build/candidate/j86-ramboot.bin','evdev':'wifi/build/candidate/evdev.ko','touch_manifest':'private-data/candidate-touch-assets.json','sha256':{'wifi/build/candidate/'+k:v for k,v in files.items()}}
profile['wireless']={'hsic_module':'wifi/build/candidate/j86_hsic_range.ko','host_module':'wifi/build/candidate/j86_wifi_host.ko','host_starts_disabled':True,'firmware_qualified':False,'autostart':False}
(candidate/'boot-profile.json').write_text(json.dumps(profile,indent=2)+'\n')
print('Prepared candidate profile only. Default boot assets and live device unchanged.')
