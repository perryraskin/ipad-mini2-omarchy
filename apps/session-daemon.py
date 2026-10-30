#!/usr/bin/python3
"""Apps in the dedicated Mac-backed overlay; local desktop-user requests only."""
import configparser,json,os,pathlib,re,shlex,socket,struct,subprocess,signal
HOME=pathlib.Path('/home/tablet');RUNTIME=pathlib.Path('/run/user/1000')
SOCKET=pathlib.Path('/run/j86-apps.sock')
READY=pathlib.Path('/run/j86-apps-ready')
assert os.geteuid()==0
assert pathlib.Path('/proc/device-tree/model').read_bytes().rstrip(b'\0')==b'Apple iPad mini 2 (Cellular)'
assert any(x.split()[1:3]==['/','overlay'] and 'rw' in x.split()[3].split(',') for x in pathlib.Path('/proc/mounts').read_text().splitlines())

def user():os.initgroups('tablet',1000);os.setgid(1000);os.setuid(1000)
def env():
 value={'HOME':str(HOME),'USER':'tablet','PATH':'/home/tablet/.local/bin:/usr/local/bin:/usr/bin','LANG':'C.UTF-8','XDG_RUNTIME_DIR':str(RUNTIME),'WAYLAND_DISPLAY':'wayland-0','GDK_BACKEND':'wayland','LIBGL_ALWAYS_SOFTWARE':'1'}
 pid=json.loads((RUNTIME/'omarchy-desktop-ready.json').read_text())['shell_pid']
 for item in pathlib.Path('/proc/'+str(pid)+'/environ').read_bytes().split(b'\0'):
  if item.startswith(b'DBUS_SESSION_BUS_ADDRESS='):value['DBUS_SESSION_BUS_ADDRESS']=item.split(b'=',1)[1].decode()
 return value

def stream_process(command,client):
 # A closed terminal must not abandon a package transaction or block its pipe.
 # Bound delivery latency; continue draining and reap the child after disconnect.
 p=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 connected=True
 previous=client.gettimeout();client.settimeout(2)
 try:
  for line in iter(p.stdout.readline,b''):
   if connected:
    try:client.sendall(line)
    except OSError:connected=False
  return p.wait()
 finally:
  p.stdout.close();client.settimeout(previous)

def desktop(name):
 if not re.fullmatch(r'[A-Za-z0-9_.+-]+\.desktop',name):raise ValueError('Invalid application ID')
 p=pathlib.Path('/usr/share/applications')/name
 cfg=configparser.ConfigParser(interpolation=None,strict=False);cfg.optionxform=str;cfg.read(p)
 if 'Desktop Entry' not in cfg or not cfg['Desktop Entry'].get('Exec'):raise ValueError('No launch command')
 return p,cfg

def publish():
 out=HOME/'.local/share/applications';out.mkdir(parents=True,exist_ok=True)
 base=pathlib.Path('/proc/1/root/mnt/omarchy-base/usr/share/applications')
 for p in pathlib.Path('/usr/share/applications').glob('*.desktop'):
  if (base/p.name).exists():continue
  try:
   _,cfg=desktop(p.name);entry=cfg['Desktop Entry']
   if entry.get('NoDisplay','false')=='true':continue
   entry['Exec']='/home/tablet/.local/bin/j86-apps launch '+p.name;entry['Terminal']='false';entry['DBusActivatable']='false'
   entry.pop('TryExec',None)
   target=out/('j86-'+p.name)
   with target.open('w') as f:cfg.write(f,space_around_delimiters=False)
   os.chown(target,1000,1000)
  except (ValueError,configparser.Error):continue

def storage_health():
 text=pathlib.Path('/etc/pacman.conf').read_text()
 if not re.search(r'^SigLevel\s*=\s*Required DatabaseOptional\s*$',text,re.M):raise ValueError('Package signatures must remain required')
 directory=pathlib.Path('/var/lib/j86-apps');directory.mkdir(exist_ok=True)
 p=directory/'health'
 with p.open('w') as f:f.write('J86 app storage writable\n');f.flush();os.fsync(f.fileno())
 if p.read_text()!='J86 app storage writable\n':raise OSError('App storage readback mismatch')
storage_health()
signal.signal(signal.SIGTERM,lambda *_:sys_exit())
def sys_exit():raise SystemExit(0)
if SOCKET.exists():raise SystemExit('Apps service socket already exists; inspect before restarting')
with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as server:
 server.bind(str(SOCKET));os.chown(SOCKET,0,1000);os.chmod(SOCKET,0o660);server.listen(4)
 READY.write_text('J86 app storage ready\n');os.chmod(READY,0o644)
 try:
  while True:
   client,_=server.accept()
   with client:
    try:
     _,uid,_=struct.unpack('3i',client.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
     if uid not in (0,1000):raise ValueError('Wrong desktop user')
     raw=b''
     while b'\n' not in raw:
      part=client.recv(1024)
      if not part or len(raw)+len(part)>4096:raise ValueError('Invalid request')
      raw+=part
     req=json.loads(raw.split(b'\n',1)[0]);action=req.get('action');name=req.get('name','')
     if action=='install':
      if not re.fullmatch(r'[a-z0-9][a-z0-9+_.@-]*',name):raise ValueError('Enter one repository package name')
      ring=pathlib.Path('/etc/pacman.d/gnupg')
      if not ((ring/'pubring.gpg').exists() or (ring/'pubring.kbx').exists()):
       for command in (['/usr/bin/pacman-key','--init'],['/usr/bin/pacman-key','--populate','archlinuxarm']):
        if stream_process(command,client)!=0:raise ValueError('Official package keyring initialization failed; signatures remain required')
      # Upgrade this isolated app root consistently; avoid an Arch partial upgrade.
      code=stream_process(['/usr/bin/pacman','-Syu','--needed','--noconfirm','--',name],client)
      try:storage_health()
      except (OSError,ValueError):
       READY.unlink(missing_ok=True);raise
      if code==0:publish()
      client.sendall(('\nEXIT:'+str(code)+'\n').encode())
     elif action=='launch':
      _,cfg=desktop(name);entry=cfg['Desktop Entry'];command=[v for v in shlex.split(entry['Exec']) if not v.startswith('%')]
      if entry.get('Terminal','false').lower()=='true':command=['/usr/bin/foot','--',*command]
      with (RUNTIME/'j86-app-launch.log').open('ab') as log:
       subprocess.Popen(command,env=env(),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,preexec_fn=user,start_new_session=True)
      client.sendall(b'Application launch requested.\nEXIT:0\n')
     else:raise ValueError('Unknown app action')
    except (OSError,ValueError,KeyError,configparser.Error) as error:
     try:client.sendall((str(error)+'\nEXIT:1\n').encode())
     except OSError:pass
 finally:
  SOCKET.unlink(missing_ok=True);READY.unlink(missing_ok=True)
