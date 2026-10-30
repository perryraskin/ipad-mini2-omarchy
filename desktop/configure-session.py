#!/usr/bin/python3
"""Configure only the RAM home for the exact J86 desktop."""
import configparser,json,os,pathlib,shutil,sys,xml.etree.ElementTree as ET
assert pathlib.Path('/proc/device-tree/model').read_bytes().rstrip(b'\0')==b'Apple iPad mini 2 (Cellular)'
assert os.geteuid()==0
home=pathlib.Path('/home/tablet');source=pathlib.Path(__file__).resolve().parent
host=sys.argv[1]
import ipaddress
assert ipaddress.ip_address(host).is_link_local
bin=home/'.local/bin';bin.mkdir(parents=True,exist_ok=True)
shutil.copyfile(source/'j86-screen-control',bin/'j86-screen-control');(bin/'j86-screen-control').chmod(0o755)
shutil.copyfile(source/'j86-apps',bin/'j86-apps');(bin/'j86-apps').chmod(0o755)
shutil.copyfile(source/'j86-rotate',bin/'j86-rotate');(bin/'j86-rotate').chmod(0o755)
profile=home/'.mozilla/firefox/j86-usb';profile.mkdir(parents=True,exist_ok=True)
(profile/'user.js').write_text((source/'firefox-user.js').read_text().replace('169.254.21.15',host))
(bin/'j86-browser').write_text('#!/bin/sh\nexport MOZ_ENABLE_WAYLAND=1 GDK_BACKEND=wayland LIBGL_ALWAYS_SOFTWARE=1\nexec /usr/bin/firefox --profile /home/tablet/.mozilla/firefox/j86-usb "$@"\n')
(bin/'j86-browser').chmod(0o755)
apps=home/'.local/share/applications';apps.mkdir(parents=True,exist_ok=True)
text=pathlib.Path('/usr/share/applications/firefox.desktop').read_text()
text=text.replace('Exec=/usr/lib/firefox/firefox %u','Exec=/home/tablet/.local/bin/j86-browser %u')
(apps/'firefox.desktop').write_text(text)
mime=home/'.config/mimeapps.list';cfg=configparser.ConfigParser();cfg.read(mime)
if not cfg.has_section('Default Applications'):cfg.add_section('Default Applications')
for kind in ('text/html','x-scheme-handler/http','x-scheme-handler/https'):cfg['Default Applications'][kind]='firefox.desktop'
with mime.open('w') as f:cfg.write(f)
p=home/'.config/labwc/rc.xml';tree=ET.parse(p);root=tree.getroot()
backup=p.with_suffix('.xml.before-tablet-controls')
if not backup.exists():shutil.copyfile(p,backup)
for parent in root.iter():
 for child in list(parent):
  if child.tag=='keybind' and child.get('key') in ('XF86HomePage','XF86PowerOff','XF86AudioRaiseVolume','XF86AudioLowerVolume'):parent.remove(child)
theme=root.find('theme')
for font in theme.findall('font'):font.set('size','14')
resize=root.find('resize')
if resize is None:resize=ET.SubElement(root,'resize')
for name,value in [('minimumArea','20'),('cornerRange','36'),('popupShow','Always')]:
 child=resize.find(name)
 if child is None:child=ET.SubElement(resize,name)
 child.text=value
mouse=root.find('mouse')
if mouse is None:mouse=ET.SubElement(root,'mouse');ET.SubElement(mouse,'default')
tree.write(p,encoding='unicode')
menu=home/'.config/omarchy/extensions/omarchy-menu.jsonc';menu.parent.mkdir(parents=True,exist_ok=True)
# Preserve any existing extension; merge our entries rather than replacing it.
existing={}
if menu.exists():
 import re
 existing=json.loads(re.sub(r'^\s*//[^\n]*','',menu.read_text(),flags=re.M))
for key in ('screensaver','lock','suspend','hibernate','logout','reboot','shutdown'):
 existing['system.'+key]={'when':'false'}
existing['setup.j86-rotation']={'label':'Rotate screen','icon':'󰑭','action':'/home/tablet/.local/bin/j86-rotate toggle'}
existing['system.screenoff']={'label':'Screen off','icon':'󰖔','action':'/home/tablet/.local/bin/j86-screen-control screen-toggle'}
existing.pop('install.j86-package',None)
for name in ('ai','service','development','editor','style','gaming','browser','webapp','terminal','tui','windows','aur','preinstalls'):
 existing['install.'+name]={'when':'false'}
existing['install']={'label':'Install','icon':'󰉉','when':'test -S /run/j86-apps.sock && test -f /run/j86-apps-ready'}
existing['install.package']={'label':'Install app','icon':'󰉉','action':'/usr/bin/foot /home/tablet/.local/bin/j86-apps install'}
menu.write_text(json.dumps(existing,indent=2)+'\n')
for base in (bin,profile,apps,home/'.config'):
 for current,dirs,files in os.walk(base):
  os.chown(current,1000,1000)
  for name in files:os.chown(pathlib.Path(current)/name,1000,1000,follow_symlinks=False)
print('RAM browser profile, larger window resize areas and power menu configured.')
