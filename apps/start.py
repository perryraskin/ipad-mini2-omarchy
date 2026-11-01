#!/usr/bin/env python3
"""Start the separately stored J86 app overlay for the verified RAM session."""
import argparse,base64,hashlib,io,json,pathlib,re,shlex,socket,subprocess,sys,tarfile,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from sessionlib import config,network,network_checked
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--enable-installer',action='store_true',help='Explicit opt-in after write-path qualification');parser.add_argument('--experimental-audio2-storage',action='store_true',help='Explicit diagnostic only: audio2 bulk writes are not qualified');args=parser.parse_args()
c=config()
# Clear stale exposure before startup; launching apps does not require an installer.
network_checked('rm -f /mnt/omarchy/run/j86-apps-installer-enabled')
kernel=network('uname -r').strip()
profiles={
 '7.0.12-gdfa4d4208131-dirty':('j86_overlay.ko','c6a0b7f217493f252fc070da11e754acfe195f9aa056418ea9111d2a39fe3642'),
 '7.0.12-j86-audio2':('j86_overlay_audio2.ko','ae9fb578a5ad1bc7f3e4c788f72a88f6085753454e57fee3674e53ddc472b870'),
}
if kernel=='7.0.12-j86-audio2' and not args.experimental_audio2_storage:raise SystemExit('Audio2 storage requires its explicit experimental opt-in; installer enablement also requires a matching qualification receipt.')
if kernel not in profiles:raise SystemExit('No matched OverlayFS profile for this kernel.')
if args.enable_installer:
 receipt=ROOT/'private-data/apps-qualified.json'
 if receipt.is_symlink() or not receipt.is_file():raise SystemExit('No reviewed write qualification; installer stays hidden.')
 qualification=json.loads(receipt.read_text())
 required={'apps/mount-layer.sh','apps/start.py','apps/session-daemon.py','apps/configure-proxy.py','serve-apps-disk.py'}
 hashes=qualification.get('source_sha256',{})
 if qualification.get('kernel')!=kernel or set(hashes)!=required or any(hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=sha for name,sha in hashes.items()):raise SystemExit('Write qualification does not match this kernel/source; installer stays hidden.')
image=ROOT/'private-data/apps-overlay.ext4'
if not image.is_file() or image.is_symlink():raise SystemExit('Dedicated apps disk is missing')
def enable_installer():
 # An existing filesystem socket/readiness file is not proof of a live daemon.
 # The explicit opt-in must get a fresh bounded fsync/readback health response.
 code="""import pathlib,socket,time
with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as client:
 client.settimeout(5);client.connect('/run/j86-apps.sock');client.sendall(b'{"action":"health"}\\n')
 deadline=time.monotonic()+5;response=b''
 while True:
  remaining=deadline-time.monotonic()
  if remaining<=0:raise SystemExit('Storage health deadline expired')
  client.settimeout(remaining);part=client.recv(1024)
  if not part:break
  response+=part
  if len(response)>4096:raise SystemExit('Unexpected health response')
 if response!=b'J86_STORAGE_HEALTHY\\nEXIT:0\\n':raise SystemExit('Storage health refused installer enablement')
 if not pathlib.Path('/run/j86-apps-ready').is_file() or pathlib.Path('/run/j86-apps-transaction.json').exists():raise SystemExit('Storage state changed; installer stays hidden')
 pathlib.Path('/run/j86-apps-installer-enabled').touch(mode=0o600)
print('INSTALLER_HEALTH_QUALIFIED')
"""
 response=network_checked('busybox chroot /mnt/j86-apps /usr/bin/python -c '+shlex.quote(code),timeout=12)
 if 'INSTALLER_HEALTH_QUALIFIED' not in response:raise SystemExit('No fresh storage health response; installer stays disabled')
def backend_ready():
 try:
  with socket.create_connection(('127.0.0.1',10824),timeout=2) as sock:return sock.recv(8)==b'NBDMAGIC'
 except OSError:return False
# A dedicated OpenSSH forward replaces Lima's automatic TCP forwarding.
# It is local-only; no listening endpoint is exposed to the LAN.
tunnel_spec='127.0.0.1:10824:127.0.0.1:10814'
port=subprocess.run(['lsof','-nP','-iTCP@127.0.0.1:10824','-sTCP:LISTEN','-Fp'],capture_output=True,text=True)
tunnel_pids=re.findall(r'^p(\d+)$',port.stdout,re.M)
if tunnel_pids:
 assert len(tunnel_pids)==1
 command=subprocess.check_output(['ps','-p',tunnel_pids[0],'-o','command='],text=True).strip()
 assert command.startswith('/usr/bin/ssh ') and tunnel_spec in shlex.split(command) and command.endswith(' lima-j86-build'),'Unexpected tunnel listener'
else:
 subprocess.run(['limactl','start','j86-build'],check=True)
 with (ROOT/'private-data/apps-tunnel.log').open('ab') as log:
  subprocess.Popen(['/usr/bin/ssh','-F',str(pathlib.Path.home()/'.lima/j86-build/ssh.config'),'-S','none','-o','ControlMaster=no','-o','ExitOnForwardFailure=yes','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=3','-N','-T','-L',tunnel_spec,'lima-j86-build'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
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
 name,sha=profiles[kernel]
 module=ROOT/'apps/kernel'/name
 assert hashlib.sha256(module.read_bytes()).hexdigest()==sha
 subprocess.run([sys.executable,str(ROOT/'touch/tools/push-probe.py'),str(module)],check=True)
mounted=network("grep ' /mnt/j86-apps overlay rw,' /proc/mounts")
if not mounted.strip():
 tuning=base64.b64encode((ROOT/'apps/usb-transfer-tuning.py').read_bytes()).decode()
 print(network_checked("busybox base64 -d <<'J86_USB_TUNING' > /mnt/omarchy/run/j86-usb-transfer-tuning.py\n"+tuning+"\nJ86_USB_TUNING\nbusybox chroot /mnt/omarchy /usr/bin/python /run/j86-usb-transfer-tuning.py"),end='')
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
 if args.enable_installer:
  enable_installer()
 print('App service socket already present; preserving it. Installer opt-in:',args.enable_installer);raise SystemExit(0)
print(network('busybox chroot /mnt/j86-apps /usr/bin/python /run/j86-apps-daemon.py >/mnt/omarchy/run/j86-apps.log 2>&1 </dev/null &\necho APPS_SERVICE_REQUESTED'),end='')
for _ in range(10):
 if network('test -S /mnt/omarchy/run/j86-apps.sock && test -f /mnt/omarchy/run/j86-apps-ready && echo READY').strip():
  if args.enable_installer:enable_installer()
  print('App service ready. Installer opt-in:',args.enable_installer);break
 time.sleep(.25)
else:raise SystemExit(network('tail -15 /mnt/omarchy/run/j86-apps.log'))
