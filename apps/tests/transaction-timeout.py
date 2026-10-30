#!/usr/bin/env python3
"""A silent/blocked userspace package child must not monopolize the service."""
import ast,os,pathlib,selectors,signal,socket,subprocess,sys,tempfile,time
source=pathlib.Path(__file__).resolve().parents[1]/'session-daemon.py'
node=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='stream_process')
scope={k:globals()[k] for k in ('subprocess','os','selectors','signal','time')}
exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),scope)
with tempfile.TemporaryDirectory() as tmp:
 pidfile=pathlib.Path(tmp)/'pid'
 left,right=socket.socketpair()
 command=[sys.executable,'-c',"import os,pathlib,sys,time;pathlib.Path(sys.argv[1]).write_text(str(os.getpid()));time.sleep(60)",str(pidfile)]
 start=time.monotonic()
 try:scope['stream_process'](command,left,timeout=.3,kill_grace=.5)
 except RuntimeError as e:assert 'timed out' in str(e)
 else:raise AssertionError('Silent child did not time out')
 assert time.monotonic()-start<3
 pid=int(pidfile.read_text())
 try:os.kill(pid,0)
 except ProcessLookupError:pass
 else:raise AssertionError('Timed-out child survived')
 assert left.gettimeout() is None
 left.close();right.close()
print('Package watchdog: silent child terminated/reaped, bounded exit, socket timeout restored')
