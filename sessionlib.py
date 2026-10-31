import errno,glob,json,os,pathlib,re,select,socket,subprocess,termios,time,uuid
ROOT=pathlib.Path(__file__).resolve().parent
STATE=ROOT/'session.json'

def config():
 return json.loads(STATE.read_text())

def discover_network(timeout=20):
 deadline=time.monotonic()+timeout
 while True:
  text=subprocess.check_output(['networksetup','-listallhardwareports'],text=True)
  match=re.search(r'Hardware Port: pomme USB bring-up gadget\nDevice: (\w+)',text)
  ips=[]
  if match:
   interface=match.group(1)
   info=subprocess.check_output(['ifconfig',interface],text=True)
   ips=re.findall(r'\binet (169\.254\.\d+\.\d+)',info)
  if ips:break
  if time.monotonic()>=deadline:raise RuntimeError('USB network/link-local address did not become ready; inspect macOS network setup, not DFU')
  time.sleep(.25)
 host=ips[0];octets=host.split('.');octets[-1]=str(int(octets[-1])+1 if int(octets[-1])<254 else int(octets[-1])-1)
 value={'interface':interface,'host_ip':host,'device_ip':'.'.join(octets)}
 STATE.write_text(json.dumps(value,indent=2)+'\n');return value

def serial(command,timeout=15):
 deadline=time.monotonic()+10
 while True:
  ports=glob.glob('/dev/cu.usbmodempomme*')
  if len(ports)==1:break
  if len(ports)>1 or time.monotonic()>=deadline:raise RuntimeError('Expected one pomme USB serial port, got '+str(ports))
  time.sleep(.2)
 fd=os.open(ports[0],os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK)
 try:
  a=termios.tcgetattr(fd);a[0]=a[1]=a[3]=0;a[2]|=termios.CLOCAL|termios.CREAD
  termios.tcsetattr(fd,termios.TCSANOW,a)
  marker='DONE_'+uuid.uuid4().hex
  wire=(command+"; printf '\\n"+marker+"\\n'\n").encode()
  if len(wire)>1000:raise RuntimeError('Serial command too long; use network transfer.')
  if os.write(fd,b'\n'+wire)!=len(wire)+1:raise RuntimeError('Incomplete serial write')
  data=b'';deadline=time.monotonic()+timeout
  while time.monotonic()<deadline:
   if select.select([fd],[],[],max(0,deadline-time.monotonic()))[0]:
    data+=os.read(fd,65536)
    if ('\n'+marker+'\n').encode() in data.replace(b'\r',b''):
     return data.decode(errors='replace')
  raise RuntimeError('Serial command did not acknowledge; inspect state before repeating it.')
 finally:os.close(fd)

def network(command,timeout=40,binary=False):
 c=config();connect_deadline=time.monotonic()+5
 while True:
  s=socket.socket();s.settimeout(max(.05,connect_deadline-time.monotonic()))
  try:
   s.setsockopt(socket.IPPROTO_IP,25,socket.if_nametoindex(c['interface']))
   s.bind((c['host_ip'],0));s.connect((c['device_ip'],23))
   break
  except OSError as e:
   s.close()
   if e.errno==65:raise RuntimeError('macOS refused USB network access. Enable T3 Code in System Settings > Privacy & Security > Local Network. Do not redo DFU for this error.') from e
   # BusyBox respawns its single nc listener after each command. A refused
   # connect sent no command bytes, so waiting for that listener is safe.
   # Never retry after connection/send, where execution could be uncertain.
   if e.errno!=errno.ECONNREFUSED or time.monotonic()>=connect_deadline:raise
   time.sleep(.1)
 marker='DONE_'+uuid.uuid4().hex
 script='exec 2>&1\n'+command+"\nprintf '\\n"+marker+"\\n'\nexit\n"
 data=b''
 try:
  s.sendall(script.encode());deadline=time.monotonic()+timeout
  while True:
   remaining=deadline-time.monotonic()
   if remaining<=0:raise TimeoutError('USB shell total response deadline exceeded; inspect state before retrying')
   s.settimeout(remaining)
   part=s.recv(1024*1024)
   if not part:break
   data+=part
   if ('\n'+marker+'\n').encode() in data:break
 finally:s.close()
 if marker.encode() not in data:raise RuntimeError('Network command ended without acknowledgment: '+data[-1000:].decode(errors='replace'))
 return data.rsplit(('\n'+marker+'\n').encode(),1)[0].decode(errors='replace')


def network_checked(command,timeout=40):
 """Run in a subshell and require its exit status, not just transport ACK."""
 marker='STATUS_'+uuid.uuid4().hex
 output=network('(\n'+command+"\n)\nprintf '\\n"+marker+":%s\\n' \"$?\"",timeout=timeout)
 body,sep,status=output.rpartition('\n'+marker+':')
 if not sep or not re.fullmatch(r'[0-9]+\s*',status):
  raise RuntimeError('Missing remote command exit status')
 if int(status):raise RuntimeError('Remote command failed ('+status.strip()+'): '+body[-4000:])
 return body
