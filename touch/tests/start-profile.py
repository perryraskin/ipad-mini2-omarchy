#!/usr/bin/env python3
"""Regression: candidate manifests must load their own module, never baseline."""
import hashlib,json,pathlib,runpy,sys,tempfile,types
from unittest.mock import patch
SCRIPT=pathlib.Path(__file__).resolve().parents[2]/'start-touch.py'
def case(valid):
 with tempfile.TemporaryDirectory() as directory:
  root=pathlib.Path(directory);selected=root/'candidate/j86_touch.ko';selected.parent.mkdir()
  release='7.0.12-j86-wifi1'
  selected.write_bytes(b'vermagic='+(release if valid else 'wrong-kernel').encode()+b' SMP\0')
  manifest=root/'manifest.json';manifest.write_text(json.dumps([{'source':str(selected),'target':'/tmp/j86_touch.ko','sha256':hashlib.sha256(selected.read_bytes()).hexdigest()}]))
  loaded=[];uploads=[]
  def network(command):
   if command=='uname -r':return release
   if command.startswith('cat /sys/module/j86_touch/parameters/state'):return '2' if loaded else ''
   if 'ASSET_VERIFIED' in command:uploads.append(command);return 'ASSET_VERIFIED'
   return ''
  module=types.ModuleType('sessionlib');module.ROOT=root;module.network=network
  def run(command,**kwargs):loaded.append(pathlib.Path(command[-1]));return types.SimpleNamespace(returncode=0)
  with patch.dict(sys.modules,{'sessionlib':module}),patch.object(sys,'argv',[str(SCRIPT),'--manifest',str(manifest),'--kernel-release',release]),patch('subprocess.run',run):
   try:runpy.run_path(str(SCRIPT),run_name='__main__')
   except SystemExit as error:
    if valid:assert error.code==0,error
    else:assert 'vermagic' in str(error)
  if valid:assert loaded==[selected] and len(uploads)==1
  else:assert not loaded and not uploads
case(True);case(False)
print('PASS: selected candidate module loads; wrong vermagic refuses before any upload')
