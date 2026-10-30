#!/usr/bin/env python3
"""Exercise real UNIX daemon request/state flow with synthetic package operations.

Harness changes only board/root assertions, paths, caller UID and the external
package/storage/publish functions. No real pacman, mounts or device calls occur.
"""
import ast,json,os,pathlib,signal,socket,subprocess,sys,tempfile,time
if not hasattr(socket,'SO_PEERCRED'):
 print('SKIP: Linux SO_PEERCRED required; run in Linux CI/build VM');raise SystemExit(0)
source=pathlib.Path(__file__).resolve().parents[1]/'session-daemon.py'
with tempfile.TemporaryDirectory() as tmp:
 root=pathlib.Path(tmp);tree=ast.parse(source.read_text());body=[]
 replacements={'HOME':root/'home','RUNTIME':root/'runtime','SOCKET':root/'apps.sock','READY':root/'ready','INSTALLER':root/'enabled','TRANSACTION':root/'transaction.json'}
 for node in tree.body:
  if isinstance(node,ast.Assert):continue
  if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in replacements:
   node.value=ast.parse('pathlib.Path('+repr(str(replacements[node.targets[0].id]))+')',mode='eval').body
  if isinstance(node,ast.FunctionDef) and node.name in ('storage_health','publish'):
   node.body=[ast.Pass()]
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
 log=(root/'log').open('w+')
 process=subprocess.Popen([sys.executable,str(script)],stdout=log,stderr=log)
 def request(name):
  with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as c:
   c.settimeout(8);c.connect(str(root/'apps.sock'));c.sendall(json.dumps({'action':'install','name':name}).encode()+b'\n');out=b''
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
  assert b'Installer is disabled' in request('test') and not (root/'transaction.json').exists()
  # A half-written request cannot indefinitely monopolize the serial service.
  with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as slow:
   slow.connect(str(root/'apps.sock'));slow.sendall(b'{')
   start=time.monotonic();assert b'Installer is disabled' in request('test');assert time.monotonic()-start<7
  (root/'enabled').touch();assert b'EXIT:0' in request('test')
  assert (root/'ready').exists() and not (root/'transaction.json').exists()
  assert b'EXIT:1' in request('fail')
  assert not (root/'ready').exists() and not (root/'enabled').exists() and (root/'transaction.json').exists()
  assert b'Installer is disabled' in request('test')
 finally:
  process.terminate();process.wait(timeout=5);log.close()
 restarted=subprocess.run([sys.executable,str(script)],capture_output=True,text=True,timeout=5)
 assert restarted.returncode!=0 and 'Uncertain previous transaction' in restarted.stderr
print('Installer gate: explicit opt-in, bounded request, success/failure state and uncertain-restart refusal passed')
