#!/usr/bin/env python3
import importlib.util,pathlib
spec=importlib.util.spec_from_file_location('keys',pathlib.Path(__file__).resolve().parents[2]/'home-menu.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
log=[];v=m.VolumeKeys(lambda d:log.append(('brightness',d)),lambda d:log.append(('volume',d)))
v.event(115);assert log==[('brightness',1)]
assert v.command('keys-volume');v.event(114);assert log[-1]==('volume',-1)
assert not v.command('unknown');assert v.mode=='volume'
assert v.command('keys-brightness');v.event(114);assert log[-1]==('brightness',-1)
def fail(d):raise RuntimeError('no sink')
v.volume=fail;v.command('keys-volume');before=list(log)
try:v.event(115)
except RuntimeError:pass
else:raise AssertionError('Sink failure was swallowed')
assert log==before
p=m.PowerButton(lambda:log.append('short'),lambda:log.append('long'))
p.event(1,0);p.event(0,.5);assert log[-1]=='short'
p.event(1,2);p.tick(3.3);p.tick(4);p.event(0,5);assert log.count('long')==1
print('Session keys: default, explicit mode, sink failure and hold/release passed')

assert not m.native_audio_sink('media.class = \"Audio/Sink\"\nnode.name = \"auto_null\"')
assert m.native_audio_sink('media.class = \"Audio/Sink\"\napi.alsa.path = \"hw:0,0\"')
