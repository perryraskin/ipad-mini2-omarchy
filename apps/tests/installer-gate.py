#!/usr/bin/env python3
"""Exercise real UNIX daemon request/state flow with synthetic package operations.

Harness changes only board/root assertions, paths, caller UID and the external
package/storage/publish functions. No real pacman, mounts or device calls occur.
"""
import ast,json,os,shlex,pathlib,signal,socket,subprocess,sys,tempfile,time
if not hasattr(socket,'SO_PEERCRED'):
 print('SKIP: Linux SO_PEERCRED required; run in Linux CI/build VM');raise SystemExit(0)
source=pathlib.Path(__file__).resolve().parents[1]/'session-daemon.py'
with tempfile.TemporaryDirectory() as tmp:
 root=pathlib.Path(tmp);tree=ast.parse(source.read_text());body=[]
 replacements={'HOME':root/'home','RUNTIME':root/'runtime','SOCKET':root/'apps.sock','READY':root/'ready','INSTALLER':root/'enabled','TRANSACTION':root/'transaction.json','MEMINFO':root/'meminfo'}
 for node in tree.body:
  if isinstance(node,ast.Assert):continue
  if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in replacements:
   node.value=ast.parse('pathlib.Path('+repr(str(replacements[node.targets[0].id]))+')',mode='eval').body
  if isinstance(node,ast.FunctionDef) and node.name=='publish':node.body=[ast.Pass()]
  if isinstance(node,ast.FunctionDef) and node.name=='storage_health':
   node.body=ast.parse("if pathlib.Path("+repr(str(root/'storage-fail'))+").exists():raise OSError('Synthetic storage failure')").body
  if isinstance(node,ast.FunctionDef) and node.name=='stream_process':
   node=ast.parse("def stream_process(command,client):\n time.sleep(.2)\n return 17 if command[-1]=='fail' else 0\n").body[0]
  body.append(node)
 class Credentials(ast.NodeTransformer):
  def visit_Compare(self,node):
   self.generic_visit(node)
   if isinstance(node.left,ast.Name) and node.left.id=='uid':
    node.comparators=[ast.Tuple(elts=[ast.Constant(0),ast.Constant(os.getuid())],ctx=ast.Load())]
   return node
 tree=Credentials().visit(ast.Module(body=body,type_ignores=[]));ast.fix_missing_locations(tree)
 script=root/'daemon.py';script.write_text(ast.unparse(tree))
 # Skip real keyring preparation by answering True for that specific fixture path.
 text=script.read_text().replace("ring = pathlib.Path('/etc/pacman.d/gnupg')",'ring = pathlib.Path('+repr(str(root/'ring'))+')');script.write_text(text.replace('os.chown(SOCKET, 0, 1000)','None'))
 (root/'ring').mkdir();(root/'ring/pubring.gpg').write_text('synthetic')
 (root/'meminfo').write_text('MemAvailable: 524288 kB\n')
 log=(root/'log').open('w+')
 process=subprocess.Popen([sys.executable,str(script)],stdout=log,stderr=log)
 def request(name,action='install'):
  with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as c:
   c.settimeout(8);c.connect(str(root/'apps.sock'));c.sendall(json.dumps({'action':action,'name':name}).encode()+b'\n');out=b''
   while True:
    b=c.recv(8192)
    if not b:return out
    out+=b
 try:
  deadline=time.monotonic()+5
  while not (root/'ready').exists():
   if process.poll() is not None:raise AssertionError('Daemon exited: '+(root/'log').read_text())
   if time.monotonic()>deadline:raise AssertionError('No readiness')
   time.sleep(.01)
  assert request('',action='health')==b'J86_STORAGE_HEALTHY\nEXIT:0\n'
  assert b'Installer is disabled' in request('test') and not (root/'transaction.json').exists()
  # A half-written request cannot indefinitely monopolize the serial service.
  with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as slow:
   slow.connect(str(root/'apps.sock'));slow.sendall(b'{')
   start=time.monotonic();assert b'Installer is disabled' in request('test');assert time.monotonic()-start<7
  # Execute the production enable helper's embedded health client against this
  # real daemon socket, with only its RAM paths mapped into the fixture.
  start_source=source.parent/'start.py'
  helper=next(n for n in ast.parse(start_source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='enable_installer')
  def network_checked(command,timeout):
   args=shlex.split(command);assert args[:5]==['busybox','chroot','/mnt/j86-apps','/usr/bin/python','-c']
   code=args[5]
   for original,target in [('/run/j86-apps.sock',root/'apps.sock'),('/run/j86-apps-ready',root/'ready'),('/run/j86-apps-transaction.json',root/'transaction.json'),('/run/j86-apps-installer-enabled',root/'enabled')]:code=code.replace(original,str(target))
   return subprocess.check_output([sys.executable,'-c',code],text=True,stderr=subprocess.PIPE,timeout=timeout)
  scope={'shlex':shlex,'network_checked':network_checked}
  exec(compile(ast.Module(body=[helper],type_ignores=[]),str(start_source),'exec'),scope)
  scope['enable_installer']();assert (root/'enabled').exists()
  (root/'meminfo').write_text('MemAvailable: 65536 kB\n')
  assert b'Close Firefox' in request('test')
  assert not (root/'transaction.json').exists() and (root/'ready').exists()
  (root/'meminfo').write_text('MemAvailable: 524288 kB\n')
  assert b'EXIT:0' in request('test')
  assert (root/'ready').exists() and not (root/'transaction.json').exists()
  (root/'storage-fail').touch();assert b'EXIT:1' in request('',action='health')
  assert not (root/'ready').exists() and not (root/'enabled').exists()
  (root/'storage-fail').unlink();scope['enable_installer']()
  assert b'EXIT:1' in request('fail')
  assert not (root/'ready').exists() and not (root/'enabled').exists() and (root/'transaction.json').exists()
  assert b'Installer is disabled' in request('test')
  assert b'EXIT:1' in request('',action='health') and not (root/'ready').exists()
 finally:
  process.terminate();process.wait(timeout=5);log.close()
 restarted=subprocess.run([sys.executable,str(script)],capture_output=True,text=True,timeout=5)
 assert restarted.returncode!=0 and 'Uncertain previous transaction' in restarted.stderr
print('Installer gate: explicit opt-in, bounded request, success/failure state and uncertain-restart refusal passed')
