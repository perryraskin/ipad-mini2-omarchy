#!/usr/bin/env python3
"""Start exact-J86 native touch in RAM; no iPad storage install."""
import argparse,base64,hashlib,json,pathlib,subprocess,sys,time
from sessionlib import ROOT,network
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--manifest',type=pathlib.Path,default=ROOT/'touch/native/assets.json')
parser.add_argument('--kernel-release',default='7.0.12-gdfa4d4208131-dirty')
args=parser.parse_args()
if network('uname -r').strip()!=args.kernel_release:raise SystemExit('Touch kernel profile mismatch; no module upload attempted')
manifest=json.loads(args.manifest.read_text())
for entry in manifest:
 p=ROOT/entry['source']
 if hashlib.sha256(p.read_bytes()).hexdigest()!=entry['sha256']:
  raise SystemExit('Touch asset checksum mismatch: '+str(p))
modules=[ROOT/e['source'] for e in manifest if e['target']=='/tmp/j86_touch.ko']
if len(modules)!=1:raise SystemExit('Touch manifest must select exactly one module')
module_path=modules[0]
if b'vermagic='+args.kernel_release.encode()+b' ' not in module_path.read_bytes():
 raise SystemExit('Touch module vermagic does not match selected kernel profile')
state=network('cat /sys/module/j86_touch/parameters/state 2>/dev/null')
if state.strip()=='2':
 print('Native J86 touchscreen already ready.');raise SystemExit(0)
if state.strip()=='1':raise SystemExit('Touch startup already in progress; inspect state before retrying.')
if state.strip() not in ('','0'):
 raise SystemExit('Previous touch startup failed; inspect last_result and dmesg before retrying.')
if not state.strip():
 for entry in manifest:
  p=ROOT/entry['source'];target=entry['target'];encoded=base64.encodebytes(p.read_bytes()).decode()
  command="mkdir -p /lib/firmware /tmp/j86-touch\nbusybox base64 -d <<'J86_TOUCH_ASSET' > "+target+"\n"+encoded+"J86_TOUCH_ASSET\n"
  command+=f"actual=$(busybox sha256sum {target}); [ \"${{actual%% *}}\" = {entry['sha256']} ] && echo ASSET_VERIFIED || echo ASSET_FAILED\nchmod 600 {target}"
  if 'ASSET_VERIFIED' not in network(command):raise SystemExit('Device asset verification failed: '+target)
 network('chmod 700 /tmp/load-once')
 # This helper checks every undefined export against this live kernel first.
 subprocess.run([sys.executable,str(ROOT/'touch/tools/push-probe.py'),str(module_path)],check=True)
else:
 print(network('echo Y > /sys/module/j86_touch/parameters/enabled'),end='')
for attempt in range(30):
 state=network('cat /sys/module/j86_touch/parameters/state').strip()
 if state=='2':
  print('Native J86 touchscreen ready.');raise SystemExit(0)
 if state=='3':raise SystemExit(network('cat /sys/module/j86_touch/parameters/last_result; dmesg | tail -8'))
 time.sleep(.4)
raise SystemExit('Native touch has not become ready; inspect state and logs.')
