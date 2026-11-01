#!/usr/bin/env python3
"""Concurrent launchers serialize startup without losing arguments or exit codes."""
import importlib.machinery,importlib.util,pathlib,subprocess,sys,tempfile,time
root=pathlib.Path(__file__).resolve().parents[1]
loader=importlib.machinery.SourceFileLoader('browser',str(root/'j86-browser'))
spec=importlib.util.spec_from_loader(loader.name,loader);m=importlib.util.module_from_spec(spec);loader.exec_module(m)
with tempfile.TemporaryDirectory() as tmp:
 p=pathlib.Path(tmp);worker=p/'worker.py';log=p/'log'
 worker.write_text('import pathlib,sys,time\nwith pathlib.Path(sys.argv[1]).open("a") as f:f.write(sys.argv[2]+" "+str(time.time())+"\\n");f.flush()\ntime.sleep(1.2)\n')
 runner=p/'runner.py';runner.write_text('import runpy,sys\nm=runpy.run_path(sys.argv[1]);raise SystemExit(m["launch"]([sys.executable,sys.argv[2],sys.argv[3],sys.argv[4]],sys.argv[5],settle=.8))\n')
 a=subprocess.Popen([sys.executable,str(runner),str(root/'j86-browser'),str(worker),str(log),'first',str(p/'lock')])
 deadline=time.monotonic()+3
 while not log.exists():
  assert time.monotonic()<deadline;time.sleep(.01)
 b=subprocess.Popen([sys.executable,str(runner),str(root/'j86-browser'),str(worker),str(log),'second',str(p/'lock')])
 assert a.wait(timeout=4)==b.wait(timeout=4)==0
 lines=[line.split() for line in log.read_text().splitlines()]
 assert [v[0] for v in lines]==['first','second']
 assert float(lines[1][1])-float(lines[0][1])>=.5
 assert m.launch([sys.executable,'-c','raise SystemExit(7)'],p/'lock',settle=.8)==7
with tempfile.TemporaryDirectory() as tmp:
 p=pathlib.Path(tmp);profile=p/'user.js';original=(root/'firefox-user.js').read_text();profile.write_text(original)
 m.configure_network(p,True);assert 'user_pref("network.proxy.type", 0);' in profile.read_text()
 assert 'network.proxy.socks_remote_dns' in profile.read_text()
 m.configure_network(p,False);assert profile.read_text()==original
 profile.write_text('unexpected format')
 try:m.configure_network(p,True)
 except RuntimeError:pass
 else:raise AssertionError('Unknown profile format accepted')
print('Browser startup: concurrent launches queued, arguments retained, exit status preserved')
