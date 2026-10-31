#!/usr/bin/env python3
"""macOS gadget discovery may precede serial/link-local readiness."""
import importlib.util,pathlib,tempfile,types
p=pathlib.Path(__file__).resolve().parents[1]/'sessionlib.py';spec=importlib.util.spec_from_file_location('session',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
clock=[0];calls=[0]
m.time=types.SimpleNamespace(monotonic=lambda:clock[0],sleep=lambda delay:clock.__setitem__(0,clock[0]+delay))
def output(args,**kwargs):
 if args[0]=='networksetup':
  calls[0]+=1
  return '' if calls[0]==1 else 'Hardware Port: pomme USB bring-up gadget\nDevice: en11\n'
 return 'inet6 fe80::1' if calls[0]==2 else 'inet 169.254.91.188 netmask 0xffff0000'
m.subprocess=types.SimpleNamespace(check_output=output)
with tempfile.TemporaryDirectory() as tmp:
 m.STATE=pathlib.Path(tmp)/'session.json';c=m.discover_network(timeout=2)
 assert c=={'interface':'en11','host_ip':'169.254.91.188','device_ip':'169.254.91.189'} and calls[0]==3
 assert m.STATE.exists()
 m.subprocess=types.SimpleNamespace(check_output=lambda *args,**kwargs:'');clock[0]=0
 try:m.discover_network(timeout=.5)
 except RuntimeError:pass
 else:raise AssertionError('Discovery did not time out')
 assert clock[0]<=.75
print('USB readiness: delayed interface/address discovery and finite timeout passed')
