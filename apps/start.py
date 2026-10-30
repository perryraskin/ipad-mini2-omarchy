#!/usr/bin/env python3
"""Start the separately stored J86 app overlay for the verified RAM session."""
import base64,hashlib,io,pathlib,re,socket,subprocess,sys,tarfile,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from sessionlib import config,network,network_checked
c=config()
if network('uname -r').strip()!='7.0.12-gdfa4d4208131-dirty':raise SystemExit('Build the matching OverlayFS module before enabling apps on this kernel.')
image=ROOT/'private-data/apps-overlay.ext4'
if not image.is_file() or image.is_symlink():raise SystemExit('Dedicated apps disk is missing')
def backend_ready():
 try:
  with socket.create_connection(('127.0.0.1',10814),timeout=2) as sock:return sock.recv(8)==b'NBDMAGIC'
 except OSError:return False
if not backend_ready():
 subprocess.run(['limactl','start','j86-build'],check=True)
 with (ROOT/'private-data/apps-backend.log').open('ab') as log:
  subprocess.Popen(['limactl','shell','j86-build','env','J86_TASK_ROOT='+str(ROOT),'bash','-c','exec nbdkit -f -o --filter=log -p 10814 -i 127.0.0.1 -P "$HOME/j86-apps-nbdkit.pid" file "$J86_TASK_ROOT/private-data/apps-overlay.ext4" logfile="$J86_TASK_ROOT/private-data/apps-nbd-requests.log"'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 for _ in range(20):
  if backend_ready():break
  time.sleep(.5)
 else:raise SystemExit('Standard NBD backend not ready; inspect private-data/apps-backend.log')
port=subprocess.run(['lsof','-nP','-iTCP@'+c['host_ip']+':10812','-sTCP:LISTEN','-Fp'],capture_output=True,text=True)
pids=re.findall(r'^p(\d+)$',port.stdout,re.M)
if pids:
 assert len(pids)==1
 command=subprocess.check_output(['ps','-p',pids[0],'-o','command='],text=True).strip()
 cwd=subprocess.check_output(['lsof','-a','-p',pids[0],'-d','cwd','-Fn'],text=True)
 suffix='serve-apps-disk.py '+c['host_ip']+' '+c['device_ip']
 assert command.endswith(str(ROOT/'serve-apps-disk.py')+' '+c['host_ip']+' '+c['device_ip']) or (command.endswith(suffix) and '\nn'+str(ROOT)+'\n' in cwd)
else:
 with (ROOT/'private-data/apps-server.log').open('ab') as log:
  subprocess.Popen([sys.executable,str(ROOT/'serve-apps-disk.py'),c['host_ip'],c['device_ip']],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
if not network('test -d /sys/module/overlay && echo LOADED').strip():
 module=ROOT/'apps/kernel/j86_overlay.ko'
 assert hashlib.sha256(module.read_bytes()).hexdigest()=='c6a0b7f217493f252fc070da11e754acfe195f9aa056418ea9111d2a39fe3642'
 subprocess.run([sys.executable,str(ROOT/'touch/tools/push-probe.py'),str(module)],check=True)
mounted=network("grep ' /mnt/j86-apps overlay rw,' /proc/mounts")
if not mounted.strip():
 encoded=base64.b64encode((ROOT/'apps/mount-layer.sh').read_bytes()).decode()
 result=network_checked("set -e\nbusybox base64 -d <<'J86_MOUNT_APPS' > /tmp/j86-apps-mount.sh\n"+encoded+"\nJ86_MOUNT_APPS\nsh /tmp/j86-apps-mount.sh "+c['host_ip'],timeout=30)
 if 'APPS_LAYER_READY' not in result:raise SystemExit(result)
archive=io.BytesIO()
with tarfile.open(fileobj=archive,mode='w:gz') as t:
 t.add(ROOT/'apps/session-daemon.py',arcname='j86-apps-daemon.py')
 t.add(ROOT/'apps/configure-proxy.py',arcname='j86-apps-proxy.py')
encoded=base64.b64encode(archive.getvalue()).decode()
print(network_checked("set -e\nbusybox base64 -d <<'J86_APPS_DAEMON' | busybox tar -xz -C /mnt/omarchy/run\n"+encoded+"\nJ86_APPS_DAEMON\n"),end='')
result=network_checked('busybox chroot /mnt/j86-apps /usr/bin/python /run/j86-apps-proxy.py '+c['host_ip']+' && echo J86_PROXY_CONFIGURED')
if 'J86_PROXY_CONFIGURED' not in result:raise SystemExit('App storage/proxy configuration failed; service stays disabled.\n'+result)
client=base64.b64encode((ROOT/'desktop/j86-apps').read_bytes()).decode()
print(network_checked("set -e\nmkdir -p /mnt/omarchy/home/tablet/.local/bin\nbusybox base64 -d <<'J86_APPS_CLIENT' > /mnt/omarchy/home/tablet/.local/bin/j86-apps\n"+client+"\nJ86_APPS_CLIENT\nchmod 755 /mnt/omarchy/home/tablet/.local/bin/j86-apps\nchown 1000:1000 /mnt/omarchy/home/tablet/.local/bin/j86-apps"),end='')
if network('test -S /mnt/omarchy/run/j86-apps.sock && echo PRESENT').strip():
 print('App service socket already present; preserving it.');raise SystemExit(0)
print(network('busybox chroot /mnt/j86-apps /usr/bin/python /run/j86-apps-daemon.py >/mnt/omarchy/run/j86-apps.log 2>&1 </dev/null &\necho APPS_SERVICE_REQUESTED'),end='')
for _ in range(10):
 if network('test -S /mnt/omarchy/run/j86-apps.sock && echo READY').strip():print('App service ready.');break
 time.sleep(.25)
else:raise SystemExit(network('tail -15 /mnt/omarchy/run/j86-apps.log'))
