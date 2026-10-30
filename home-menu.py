#!/usr/bin/env python3
"""Exact J86 session keys. Screen off is not SoC suspend."""
import argparse,glob,os,pathlib,select,socket,struct,subprocess,time

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
 def shell(*command):
  return subprocess.run(['/usr/bin/setpriv','--reuid=1000','--regid=1000','--init-groups','/usr/bin/env','HOME=/home/tablet','XDG_RUNTIME_DIR=/run/user/1000','OMARCHY_PATH=/home/tablet/.local/share/omarchy-ipad','PATH=/home/tablet/.local/bin:/usr/local/bin:/usr/bin',*command],timeout=8)
 def menu(name):shell('/usr/local/bin/omarchy-shell','shell','summon','omarchy.menu','{"menu":"'+name+'"}')
 saved=None;touch=pathlib.Path('/sys/module/j86_touch/parameters')
 def screen_toggle():
  nonlocal saved
  if saved is None:
   saved=max(1,int((backlight/'brightness').read_text()))
   (touch/'enabled').write_text('N\n');deadline=time.monotonic()+8
   while (touch/'state').read_text().strip()!='0':
    if time.monotonic()>deadline:
     saved=None;(touch/'enabled').write_text('Y\n');raise RuntimeError('Touch did not stop; screen left on')
    time.sleep(.05)
   brightness(0);print('Screen off; touch stopped. System remains awake.',flush=True)
  else:
   brightness(saved);saved=None;(touch/'enabled').write_text('Y\n');print('Screen on; touch restart requested.',flush=True)
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
       current=int((backlight/'brightness').read_text())
       print('Volume-key brightness:',brightness(max(1,current+maximum//20*(1 if code==115 else -1))),flush=True)
     except (OSError,RuntimeError,subprocess.SubprocessError) as error:print('Key action failed:',error,flush=True)
  finally:
   control.unlink(missing_ok=True)
   if saved is not None:brightness(saved);(touch/'enabled').write_text('Y\n')

if __name__=='__main__':main()
