#!/usr/bin/python3
"""Apps in the dedicated Mac-backed overlay; local desktop-user requests only."""
import configparser,json,os,pathlib,re,shlex,socket,struct,subprocess,signal,selectors,time
HOME=pathlib.Path('/home/tablet');RUNTIME=pathlib.Path('/run/user/1000')
SOCKET=pathlib.Path('/run/j86-apps.sock')
READY=pathlib.Path('/run/j86-apps-ready')
INSTALLER=pathlib.Path('/run/j86-apps-installer-enabled')
TRANSACTION=pathlib.Path('/run/j86-apps-transaction.json')
MEMINFO=pathlib.Path('/proc/meminfo')
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

def stream_process(command,client,timeout=1800,kill_grace=5):
 # Drain fixed chunks, including output without newlines. Never retry pacman.
 # A timeout terminates/reaps the process group; an unreapable process is an
 # uncertain transaction and its marker must remain for manual recovery.
 p=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
 connected=True;previous=client.gettimeout();client.settimeout(2)
 deadline=time.monotonic()+timeout
 try:
  with selectors.DefaultSelector() as selector:
   selector.register(p.stdout,selectors.EVENT_READ)
   while selector.get_map() or p.poll() is None:
    if time.monotonic()>=deadline:
     os.killpg(p.pid,signal.SIGTERM)
     try:p.wait(timeout=kill_grace)
     except subprocess.TimeoutExpired:
      os.killpg(p.pid,signal.SIGKILL)
      try:p.wait(timeout=kill_grace)
      except subprocess.TimeoutExpired:raise RuntimeError('Transaction process could not be reaped; keep installer disabled')
     raise RuntimeError('Transaction timed out; installer disabled pending storage review')
    for key,_ in selector.select(min(.1,max(0,deadline-time.monotonic()))):
     data=os.read(key.fd,8192)
     if not data:selector.unregister(key.fileobj);continue
     if connected:
      try:client.sendall(data)
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

def install_resources():
 values={line.split(':',1)[0]:line.split(':',1)[1].split()[0] for line in MEMINFO.read_text().splitlines() if ':' in line}
 if int(values.get('MemAvailable','0')) < 192*1024:
  raise ValueError('Close Firefox and other apps, then retry installing; available memory is too low')

def storage_health():
 text=pathlib.Path('/etc/pacman.conf').read_text()
 if not re.search(r'^SigLevel\s*=\s*Required DatabaseOptional\s*$',text,re.M):raise ValueError('Package signatures must remain required')
 directory=pathlib.Path('/var/lib/j86-apps');directory.mkdir(exist_ok=True)
 p=directory/'health'
 with p.open('w') as f:f.write('J86 app storage writable\n');f.flush();os.fsync(f.fileno())
 if p.read_text()!='J86 app storage writable\n':raise OSError('App storage readback mismatch')
if TRANSACTION.exists():raise SystemExit('Uncertain previous transaction; inspect storage/processes before restarting')
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
    client.settimeout(5);action=None
    try:
     _,uid,_=struct.unpack('3i',client.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
     if uid not in (0,1000):raise ValueError('Wrong desktop user')
     raw=b'';request_deadline=time.monotonic()+5
     while b'\n' not in raw:
      remaining=request_deadline-time.monotonic()
      if remaining<=0:raise ValueError('Request deadline expired')
      client.settimeout(remaining)
      part=client.recv(1024)
      if not part or len(raw)+len(part)>4096:raise ValueError('Invalid request')
      raw+=part
     client.settimeout(2)
     req=json.loads(raw.split(b'\n',1)[0]);action=req.get('action');name=req.get('name','')
     if action=='health':
      if TRANSACTION.exists():raise ValueError('Transaction active or uncertain; installer remains disabled')
      storage_health()
      READY.write_text('J86 app storage ready\n');os.chmod(READY,0o644)
      client.sendall(b'J86_STORAGE_HEALTHY\nEXIT:0\n')
     elif action=='install':
      if not re.fullmatch(r'[a-z0-9][a-z0-9+_.@-]*',name):raise ValueError('Enter one repository package name')
      if not INSTALLER.is_file():raise ValueError('Installer is disabled; explicitly qualify and enable the Mac write path first')
      install_resources()
      READY.unlink(missing_ok=True)
      fd=os.open(TRANSACTION,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
      with os.fdopen(fd,'w') as f:json.dump({'package':name,'daemon_pid':os.getpid(),'started':time.time()},f)
      ring=pathlib.Path('/etc/pacman.d/gnupg')
      if not ((ring/'pubring.gpg').exists() or (ring/'pubring.kbx').exists()):
       for command in (['/usr/bin/pacman-key','--init'],['/usr/bin/pacman-key','--populate','archlinuxarm']):
        if stream_process(command,client)!=0:raise ValueError('Official package keyring initialization failed; signatures remain required')
      # Upgrade this isolated app root consistently; avoid an Arch partial upgrade.
      code=stream_process(['/usr/bin/pacman','-Syu','--needed','--noconfirm','--',name],client)
      try:storage_health()
      except (OSError,ValueError):
       READY.unlink(missing_ok=True);raise
      if code!=0:raise RuntimeError('Package operation failed; installer disabled pending review (exit '+str(code)+')')
      TRANSACTION.unlink()
      READY.write_text('J86 app storage ready\n');os.chmod(READY,0o644)
      if code==0:publish()
      client.sendall(('\nEXIT:'+str(code)+'\n').encode())
     elif action=='launch':
      _,cfg=desktop(name);entry=cfg['Desktop Entry'];command=[v for v in shlex.split(entry['Exec']) if not v.startswith('%')]
      if entry.get('Terminal','false').lower()=='true':command=['/usr/bin/foot','--',*command]
      with (RUNTIME/'j86-app-launch.log').open('ab') as log:
       subprocess.Popen(command,env=env(),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,preexec_fn=user,start_new_session=True)
      client.sendall(b'Application launch requested.\nEXIT:0\n')
     else:raise ValueError('Unknown app action')
    except (OSError,ValueError,KeyError,RuntimeError,configparser.Error) as error:
     if action=='health' or TRANSACTION.exists():READY.unlink(missing_ok=True);INSTALLER.unlink(missing_ok=True)
     try:client.sendall((str(error)+'\nEXIT:1\n').encode())
     except OSError:pass
 finally:
  SOCKET.unlink(missing_ok=True);READY.unlink(missing_ok=True)
