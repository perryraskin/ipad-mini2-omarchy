#!/usr/bin/env python3
"""Exercise the production subprocess drain without device/root prerequisites."""
import ast,pathlib,socket,subprocess,sys,tempfile,threading
source=pathlib.Path(__file__).resolve().parents[1]/'session-daemon.py'
node=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='stream_process')
scope={'subprocess':subprocess};exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),scope)
with tempfile.TemporaryDirectory() as directory:
 receipt=pathlib.Path(directory)/'done'
 left,right=socket.socketpair();right.close()
 command=[sys.executable,'-c',"import pathlib,sys;sys.stdout.buffer.write(b'x'*1048576);sys.stdout.flush();pathlib.Path(sys.argv[1]).write_text('finished')",str(receipt)]
 result=[]
 worker=threading.Thread(target=lambda:result.append(scope['stream_process'](command,left)),daemon=True)
 worker.start();worker.join(10)
 assert not worker.is_alive(),'Disconnected client blocked transaction pipe'
 assert result==[0] and receipt.read_text()=='finished'
 assert left.gettimeout() is None
 left.close()
print('PASS: disconnected client does not block or orphan transaction; child exits and is reaped')
