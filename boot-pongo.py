#!/usr/bin/env python3
"""J86-only, bounded RAM boot to PongoOS. No storage installation."""
import fcntl, hashlib, os, pathlib, signal, subprocess, sys
root=pathlib.Path(__file__).resolve().parent
lock=(root/'usb-session.lock').open('w')
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
q=subprocess.run(['irecovery','-q'],capture_output=True,text=True,timeout=15)
fields=dict(line.split(':',1) for line in q.stdout.splitlines() if ':' in line)
fields={k:v.strip().lower() for k,v in fields.items()}
expected={'PRODUCT':'ipad4,5','MODEL':'j86ap','CPID':'0x8960','BDID':'0x0c','MODE':'dfu'}
if q.returncode or any(fields.get(k)!=v for k,v in expected.items()):
 sys.exit('Refusing USB boot: expected exactly iPad4,5 / J86AP / 8960 / 0c in DFU. '+str({k:fields.get(k) for k in expected}))
args=[str(root/'assets/checkra1n-0.1337.3-macos'),'-Epn','-k',str(root/'assets/pongoos-Pongo.bin')]
print('Verified J86 DFU identity; starting one Pongo RAM upload.',flush=True)
with (root/'pongo-boot.log').open('a') as log:
 proc=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 try:
  result=proc.wait(timeout=90)
 except (subprocess.TimeoutExpired,KeyboardInterrupt):
  os.killpg(proc.pid,signal.SIGTERM)
  try: proc.wait(timeout=3)
  except subprocess.TimeoutExpired:
   os.killpg(proc.pid,signal.SIGKILL); proc.wait()
  sys.exit('Boot process stopped. Inspect USB state and log before retrying.')
print('Loader exit:',result,'— inspect USB and Pongo console to verify handoff.')
