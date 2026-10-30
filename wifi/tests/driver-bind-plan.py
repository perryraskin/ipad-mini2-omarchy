#!/usr/bin/env python3
import hashlib,importlib.util,json,pathlib,tempfile,unittest.mock
root=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('bind',root/'wifi/tools/driver-bind-plan.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as tmp:
 stage=pathlib.Path(tmp);(stage/'brcm').mkdir();blob=b'synthetic test only';name='brcm/brcmfmac43241b5-j86.bin';(stage/name).write_bytes(blob);module=stage/'test.ko';module.write_bytes(b'synthetic module metadata test')
 receipt={'name':name,'enabled':False,'rf_qualified':False,'autostart':False,'size':len(blob),'sha256':hashlib.sha256(blob).hexdigest()};(stage/'stage.json').write_text(json.dumps(receipt))
 metadata={'firmware':name+'\n','parm':'j86_allow_firmware:default off (bool)\n','alias':'usb:v0A5CpBD1Cd*dc*dsc*dp*icFFisc02ipFFin*\n','vermagic':'7.0.12-j86-audio2 SMP mod_unload aarch64\n'}
 with unittest.mock.patch.object(m.subprocess,'check_output',side_effect=lambda args,**kwargs:metadata[args[2]]):
  assert m.plan(stage,module)['activation'] is False
  for key in ('firmware','parm','alias'):
   original=metadata[key];metadata[key]=''
   try:m.plan(stage,module)
   except ValueError:pass
   else:raise AssertionError(key)
   metadata[key]=original
  (stage/name).write_bytes(b'corrupt')
  try:m.plan(stage,module)
  except ValueError:pass
  else:raise AssertionError('Corrupt stage accepted')
print('Wi-Fi binding plan: compiled firmware/alias/opt-in metadata and integrity guards passed')
