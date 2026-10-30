#!/usr/bin/env python3
import importlib.util,pathlib,tempfile
spec=importlib.util.spec_from_file_location('power',pathlib.Path(__file__).resolve().parents[1]/'suspend-preflight.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as tmp:
 root=pathlib.Path(tmp)
 for name,value in {'sys/power/state':'freeze mem','sys/power/mem_sleep':'[s2idle]','proc/self/mountinfo':'42 1 43:0 / / ro - ext4 /dev/nbd2 ro','proc/cmdline':'root=/dev/nbd2'}.items():
  p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(value)
 r=m.inspect(root);assert r['network_block_root_or_mount'] and not r['ready'] and not r['enabled']
 (root/'proc/self/mountinfo').write_text('');(root/'proc/cmdline').write_text('')
 r=m.inspect(root);assert not r['network_block_root_or_mount'] and not r['ready']
 (root/'sys/power/state').unlink();assert 'Suspend is absent from this kernel' in m.inspect(root)['blockers']
print('Suspend preflight fails closed for NBD, unqualified wake and missing kernel support')
