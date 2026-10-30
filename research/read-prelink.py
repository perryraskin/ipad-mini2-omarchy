#!/usr/bin/env python3
"""Read classic prelinked-kernel plist with IOKit XML ID/IDREF support."""
import base64,pathlib,struct,xml.etree.ElementTree as ET

def prelink(path):
 data=pathlib.Path(path).read_bytes()
 if data[:4]!=b'\xcf\xfa\xed\xfe':raise ValueError('Expected little-endian Mach-O64')
 offset=32;xml=None;segments=[]
 for _ in range(struct.unpack_from('<I',data,16)[0]):
  cmd,size=struct.unpack_from('<II',data,offset)
  if cmd==0x19:
   name=data[offset+8:offset+24].rstrip(b'\0').decode();vm,sizevm,fileoff,filesize=struct.unpack_from('<QQQQ',data,offset+24)
   segments.append((name,vm,sizevm,fileoff,filesize))
   if name=='__PRELINK_INFO':
    for i in range(struct.unpack_from('<I',data,offset+64)[0]):
     s=offset+72+i*80
     if data[s:s+16].rstrip(b'\0')==b'__info':
      length=struct.unpack_from('<Q',data,s+40)[0];start=struct.unpack_from('<I',data,s+48)[0];xml=data[start:start+length].rstrip(b'\0')
  offset+=size
 if xml is None:raise ValueError('No classic prelink plist')
 root=ET.fromstring(xml);ids={n.attrib['ID']:n for n in root.iter() if 'ID' in n.attrib};cache={}
 def parse(n):
  if 'IDREF' in n.attrib:return parse(ids[n.attrib['IDREF']])
  i=n.attrib.get('ID')
  if i in cache:return cache[i]
  if n.tag=='dict':
   c=list(n);value={parse(c[j]):parse(c[j+1]) for j in range(0,len(c),2)}
  elif n.tag=='array':value=[parse(c) for c in n]
  elif n.tag in ('key','string'):value=n.text or ''
  elif n.tag=='integer':value=int(n.text or '0',0)
  elif n.tag in ('true','false'):value=n.tag=='true'
  elif n.tag=='data':value=base64.b64decode(n.text or '')
  else:raise ValueError(n.tag)
  if i:cache[i]=value
  return value
 return parse(root),segments,data
