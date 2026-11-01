#!/usr/bin/env python3
"""Candidate selector rejects mismatched identity, missing hashes and path escape."""
import ast,hashlib,json,pathlib,tempfile,types
source=pathlib.Path(__file__).resolve().parents[1]/'ipad-linux'
node=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='boot_profile')
with tempfile.TemporaryDirectory() as tmp:
 root=pathlib.Path(tmp);directory='audio/build/candidate';out=root/directory;out.mkdir(parents=True)
 names=('j86-ramboot.bin','evdev.ko','j86_touch.ko','j86_hsic_range.ko','j86_wifi_host.ko')
 profile={'board':'J86','page_size':4096,'kernel_release':'7.0.12-j86-audio2','payload':directory+'/j86-ramboot.bin','evdev':directory+'/evdev.ko','touch_manifest':'private-data/audio-candidate-touch-assets.json','sha256':{}}
 for name in names:
  (out/name).write_bytes(name.encode());profile['sha256'][directory+'/'+name]=hashlib.sha256(name.encode()).hexdigest()
 scope={'ROOT':root,'a':types.SimpleNamespace(profile='audio-candidate'),'json':json,'hashlib':hashlib,'pathlib':pathlib}
 exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),scope)
 def call(p):
  (out/'boot-profile.json').write_text(json.dumps(p));return scope['boot_profile']()
 assert call(profile)['kernel_release']=='7.0.12-j86-audio2'
 for field,value in [('kernel_release','other'),('payload','assets/known-good.bin'),('touch_manifest','../bad')]:
  bad=dict(profile);bad[field]=value
  try:call(bad)
  except RuntimeError:pass
  else:raise AssertionError(field)
 bad=dict(profile);bad['sha256']={}
 try:call(bad)
 except RuntimeError:pass
 else:raise AssertionError('Incomplete hashes accepted')
 (out/'evdev.ko').write_bytes(b'corrupt')
 try:call(profile)
 except RuntimeError:pass
 else:raise AssertionError('Corrupt sidecar accepted')
print('Boot selector: inactive audio2 identity, full hash coverage, safe paths and corruption refusal passed')

# Execute the actual start() path with an already enumerated Linux gadget.
start=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='start')
calls=[]
def forbidden(*args):raise AssertionError('Isolated start reached desktop/proxy path')
scope={'a':types.SimpleNamespace(isolated=True),'verify_assets':lambda:None,
 'boot_profile':lambda:{'kernel_release':'7.0.12-j86-audio2'},
 'glob':types.SimpleNamespace(glob=lambda _:['gadget']),
 'serial':lambda cmd:'Apple iPad mini 2 (Cellular) 7.0.12-j86-audio2',
 'discover_network':lambda:{'device_ip':'169.254.1.2'},
 'network':lambda cmd:calls.append(cmd) or 'USB_NETWORK_PREFLIGHT_OK',
 'ensure_web_proxy':forbidden,'start_touch':forbidden}
exec(compile(ast.Module(body=[start],type_ignores=[]),str(source),'exec'),scope)
scope['start']()
assert calls==['echo USB_NETWORK_PREFLIGHT_OK']
print('Isolated boot stops before desktop, touch, proxy and storage setup')
