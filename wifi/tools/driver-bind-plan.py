#!/usr/bin/env python3
"""Emit an inactive firmware/module binding plan; no device or rootfs writes."""
import argparse,hashlib,json,pathlib,re,subprocess

def plan(stage,module):
 receipt=json.loads((stage/'stage.json').read_text());name='brcm/brcmfmac43241b5-j86.bin';blob=(stage/name).read_bytes()
 if receipt.get('name')!=name or receipt.get('enabled') is not False or receipt.get('rf_qualified') is not False or receipt.get('autostart') is not False:raise ValueError('Require disabled exact-J86 stage receipt')
 if receipt.get('sha256')!=hashlib.sha256(blob).hexdigest() or receipt.get('size')!=len(blob):raise ValueError('Firmware integrity failure')
 # Validate the compiled module's firmware dependency and opt-in parameter.
 # Offline modinfo is metadata inspection only; the module is never loaded.
 firmware=subprocess.check_output(['modinfo','-F','firmware',str(module)],text=True).splitlines()
 params=subprocess.check_output(['modinfo','-F','parm',str(module)],text=True).splitlines()
 alias=subprocess.check_output(['modinfo','-F','alias',str(module)],text=True).splitlines()
 vermagic=subprocess.check_output(['modinfo','-F','vermagic',str(module)],text=True).strip()
 if name not in firmware:raise ValueError('Module does not request staged firmware filename')
 if not any(v.startswith('j86_allow_firmware:') for v in params):raise ValueError('Module lacks default-off firmware gate')
 if not any(v.startswith('usb:v0A5CpBD1C') for v in alias):raise ValueError('Module does not bind exact observed USB identity')
 return {'board':'apple,j86','usb':'0a5c:bd1c','chip':'0x4324','revision':6,'firmware':name,'firmware_sha256':receipt['sha256'],'module_sha256':hashlib.sha256(module.read_bytes()).hexdigest(),'vermagic':vermagic,'module_options':{'j86_allow_firmware':False},'host_enabled':False,'autostart':False,'rf_qualified':False,'activation':False}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--stage',type=pathlib.Path,required=True);p.add_argument('--module',type=pathlib.Path,required=True);a=p.parse_args();print(json.dumps(plan(a.stage,a.module),indent=2))
if __name__=='__main__':main()
