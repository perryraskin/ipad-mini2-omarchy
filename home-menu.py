#!/usr/bin/env python3
"""Exact J86 session keys. Screen off is not SoC suspend."""
import argparse,glob,json,os,pathlib,re,select,signal,socket,struct,subprocess,time,xml.etree.ElementTree as ET

class PowerButton:
 def __init__(self,short,long):
  self.short=short;self.long=long;self.started=None;self.fired=False
 def event(self,value,now):
  if value==1 and self.started is None:self.started=now;self.fired=False
  elif value==0 and self.started is not None:
   self.tick(now)
   if not self.fired:self.short()
   self.started=None
 def tick(self,now):
  if self.started is not None and not self.fired and now-self.started>=1.2:
   self.fired=True;self.long()

class VolumeKeys:
 """RAM-only mode; audio never silently falls back to backlight control."""
 def __init__(self,brightness,volume):
  self.mode='brightness';self.brightness=brightness;self.volume=volume
 def command(self,command):
  if command=='keys-brightness':self.mode='brightness'
  elif command=='keys-volume':self.mode='volume'
  else:return False
  return True
 def event(self,code):
  (self.volume if self.mode=='volume' else self.brightness)(1 if code==115 else -1)

def native_audio_sink(inspect):
 return bool(re.search(r'media\.class\s*=\s*"Audio/Sink"',inspect) and
             re.search(r'api\.alsa\.path\s*=\s*"[^"\n]+"',inspect) and
             not re.search(r'node\.name\s*=\s*"auto_null"',inspect))

def touch_delivery_config(data,enabled):
 root=ET.fromstring(data)
 libinput=root.find('libinput')
 if libinput is None:libinput=ET.SubElement(root,'libinput')
 matches=[d for d in libinput.findall('device') if d.get('category')=='J86 native touchscreen']
 if len(matches)>1:raise RuntimeError('Ambiguous touchscreen configuration')
 device=matches[0] if matches else ET.SubElement(libinput,'device',category='J86 native touchscreen')
 mode=device.find('sendEventsMode')
 if mode is None:mode=ET.SubElement(device,'sendEventsMode')
 mode.text='yes' if enabled else 'no'
 return ET.tostring(root,encoding='utf-8')

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--test-brightness',action='store_true');args=parser.parse_args()
 if pathlib.Path('/proc/device-tree/model').read_bytes().rstrip(b'\0')!=b'Apple iPad mini 2 (Cellular)':raise SystemExit('Refusing key service on a non-J86 device')
 if os.geteuid()!=0:raise SystemExit('Run the key service as root')
 backlight=pathlib.Path('/sys/class/backlight/20a110000.i2c:pmic@3c:backlight@600')
 maximum=int((backlight/'max_brightness').read_text())
 if maximum!=2047:raise SystemExit('Unexpected backlight range')
 def brightness(value):
  value=max(0,min(maximum,value));(backlight/'brightness').write_text(str(value)+'\n')
  if int((backlight/'brightness').read_text())!=value:raise RuntimeError('Backlight readback mismatch')
  return value
 if args.test_brightness:
  original=int((backlight/'brightness').read_text())
  try:print('Brightness readback:',original,'->',brightness(max(1,original-64)),flush=True)
  finally:brightness(original)
  return
 def shell(*command,capture_output=False,timeout=8):
  return subprocess.run(['/usr/bin/setpriv','--reuid=1000','--regid=1000','--init-groups','/usr/bin/env','HOME=/home/tablet','XDG_RUNTIME_DIR=/run/user/1000','OMARCHY_PATH=/home/tablet/.local/share/omarchy-ipad','PATH=/home/tablet/.local/bin:/usr/local/bin:/usr/bin',*command],timeout=timeout,capture_output=capture_output,text=capture_output)
 def menu(name):shell('/usr/local/bin/omarchy-shell','shell','summon','omarchy.menu','{"menu":"'+name+'"}')
 def key_brightness(direction):
  current=int((backlight/'brightness').read_text())
  print('Volume-key brightness:',brightness(max(1,current+maximum//20*direction)),flush=True)
 def key_volume(direction):
  # The default sink must exist. wpctl failures must not change brightness.
  sink=shell('/usr/bin/wpctl','inspect','@DEFAULT_AUDIO_SINK@',capture_output=True,timeout=1)
  if sink.returncode or not native_audio_sink(sink.stdout):raise RuntimeError('No native ALSA sink; volume unchanged')
  identity=re.search(r'\bid ([0-9]+),',sink.stdout)
  if not identity:raise RuntimeError('No verified sink ID; volume unchanged')
  result=shell('/usr/bin/wpctl','set-volume','--limit','1.0',identity[1],'5%+' if direction>0 else '5%-',timeout=1)
  if result.returncode:raise RuntimeError('No usable PipeWire sink; volume unchanged')
 volume_keys=VolumeKeys(key_brightness,key_volume)
 saved=None
 def touch_delivery(enabled):
  # Keep the qualified scanning firmware alive. Only gate compositor delivery;
  # a firmware restart on every screen wake lost physical contacts in live tests.
  runtime=pathlib.Path('/run/user/1000')
  shell_pid=json.loads((runtime/'omarchy-desktop-ready.json').read_text())['shell_pid']
  values=pathlib.Path('/proc/'+str(shell_pid)+'/environ').read_bytes().split(b'\0')
  pids=[v.split(b'=',1)[1] for v in values if v.startswith(b'LABWC_PID=')]
  if len(pids)!=1 or not pids[0].isdigit():raise RuntimeError('No verified compositor PID')
  pid=int(pids[0]);exe=os.readlink('/proc/'+str(pid)+'/exe')
  if exe not in ('/usr/bin/labwc','/run/j86-desktop/build/labwc-j86-long-press') or pathlib.Path('/proc/'+str(pid)).stat().st_uid!=1000:raise RuntimeError('Unexpected compositor')
  config=pathlib.Path('/home/tablet/.config/labwc/rc.xml')
  before=config.read_bytes();after=touch_delivery_config(before,enabled)
  temporary=config.with_name('rc.xml.screen-next')
  try:
   temporary.write_bytes(after);os.chown(temporary,1000,1000);os.replace(temporary,config)
   os.kill(pid,signal.SIGHUP)
  finally:temporary.unlink(missing_ok=True)
 def screen_toggle():
  nonlocal saved
  if saved is None:
   value=max(1,int((backlight/'brightness').read_text()))
   touch_delivery(False)
   try:brightness(0)
   except Exception:
    touch_delivery(True);raise
   saved=value
   print('Screen off; touch delivery disabled; scanning retained. System remains awake.',flush=True)
  else:
   brightness(saved);touch_delivery(True);saved=None
   print('Screen on; touch delivery enabled without firmware restart.',flush=True)
 def power_menu():
  if saved is not None:screen_toggle()
  menu('system')
 paths=[]
 for candidate in glob.glob('/dev/input/event*'):
  name=pathlib.Path('/sys/class/input')/pathlib.Path(candidate).name/'device/name'
  if name.read_text().strip()=='gpio-keys':paths.append(candidate)
 if len(paths)!=1:raise SystemExit('Expected one gpio-keys device')
 control=pathlib.Path('/run/j86-screen-control.sock')
 if control.exists():raise SystemExit('Screen-control socket already exists; inspect the existing key service')
 power=PowerButton(screen_toggle,power_menu);event=struct.Struct('@llHHi')
 with socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM) as server,open(paths[0],'rb',buffering=0) as keys:
  server.bind(str(control));os.chown(control,0,1000);os.chmod(control,0o660)
  try:
   while True:
    ready,_,_=select.select([keys,server],[],[],.1);power.tick(time.monotonic())
    for source in ready:
     try:
      if source is server:
       command=server.recv(64)
       if command==b'screen-toggle':screen_toggle()
       elif command==b'power-menu':power_menu()
       elif volume_keys.command(command.decode('ascii',errors='replace')):print('Volume keys:',volume_keys.mode,flush=True)
       continue
      data=keys.read(event.size)
      if len(data)!=event.size:return
      _,_,kind,code,value=event.unpack(data)
      if kind!=1:continue
      if code==116:power.event(value,time.monotonic())
      elif code==172 and value==1:
       if saved is not None:screen_toggle()
       else:shell('/usr/local/bin/omarchy-shell','shell','toggle','omarchy.menu','{"menu":"root"}')
      elif code in (114,115) and value in (1,2) and saved is None:
       volume_keys.event(code)
     except (OSError,RuntimeError,subprocess.SubprocessError) as error:print('Key action failed:',error,flush=True)
  finally:
   control.unlink(missing_ok=True)
   if saved is not None:brightness(saved);touch_delivery(True)

if __name__=='__main__':main()
