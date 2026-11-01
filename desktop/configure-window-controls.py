#!/usr/bin/python3
"""Add touch-sized window sizing actions to the RAM-home Labwc menu."""
import os,pathlib,re,shutil,xml.etree.ElementTree as ET

def configure(directory):
 directory.mkdir(parents=True,exist_ok=True)
 menu=directory/'menu.xml'
 root=ET.parse(menu).getroot() if menu.exists() else ET.Element('openbox_menu')
 if root.tag!='openbox_menu':raise ValueError('Unexpected Labwc menu root')
 if menu.exists() and not menu.with_suffix('.xml.before-j86-sizing').exists():
  shutil.copyfile(menu,menu.with_suffix('.xml.before-j86-sizing'))
 client=root.find("menu[@id='client-menu']")
 if client is None:
  client=ET.SubElement(root,'menu',id='client-menu',label='Window')
  for label,action in [('Restore window','UnMaximize'),('Maximize','Maximize'),('Minimize','Iconify'),('Close','Close')]:
   item=ET.SubElement(client,'item',label=label);ET.SubElement(item,'action',name=action)
 # Only replace our own entries; preserve other window/root menus.
 for child in list(client):
  if child.get('label') in ('Smaller window','Larger window'):client.remove(child)
 for index,(label,amount) in enumerate([('Smaller window',-96),('Larger window',96)]):
  item=ET.Element('item',label=label)
  ET.SubElement(item,'action',name='UnMaximize')
  ET.SubElement(item,'action',name='ResizeRelative',right=str(amount),bottom=str(amount))
  client.insert(index,item)
 ET.indent(root);menu.write_text(ET.tostring(root,encoding='unicode')+'\n')
 override=directory/'themerc-override'
 text=override.read_text() if override.exists() else ''
 for key,value in [('menu.items.padding.x','18'),('menu.items.padding.y','14')]:
  text=re.sub(r'^'+re.escape(key)+r'\s*:.*\n?','',text,flags=re.M)
  text=text.rstrip()+'\n'+key+': '+value+'\n'
 override.write_text(text.lstrip())
 for path in (menu,override):os.chown(path,1000,1000)

if __name__=='__main__':
 if os.geteuid()!=0 or pathlib.Path('/proc/device-tree/model').read_bytes().rstrip(b'\0')!=b'Apple iPad mini 2 (Cellular)':
  raise SystemExit('Requires root in the J86 RAM desktop')
 configure(pathlib.Path('/home/tablet/.config/labwc'))
 print('Touch-sized window menu configured in RAM home')
