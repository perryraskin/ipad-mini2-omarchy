#!/usr/bin/env python3
"""Compare compiled runtime plans against independent stock-derived Python model."""
import ctypes, importlib.util, pathlib, random, subprocess, tempfile
root=pathlib.Path(__file__).resolve().parents[3]
s=importlib.util.spec_from_file_location('plan',root/'audio/codec/plan.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Op(ctypes.Structure):
 _fields_=[(k,ctypes.c_ubyte) for k in ('amp','register','value','mask')]
class Plan(ctypes.Structure):
 _fields_=[('revision',Op*22),('serial',Op*32),('boost',Op*4),('power',Op*24),('status',Op*24),('nr',ctypes.c_uint)]
with tempfile.TemporaryDirectory() as tmp:
 p=pathlib.Path(tmp)
 (p/'wrapper.c').write_text('#include "codec-plan.h"\nvoid build(const unsigned char *r, struct j86_codec_plan *p){j86_codec_plan(r,p);}\n')
 subprocess.run(['cc','-shared','-fPIC','-Wall','-Wextra','-Werror','-I',str(root/'audio/pcm-native'),str(p/'wrapper.c'),'-o',str(p/'plan.so')],check=True)
 lib=ctypes.CDLL(str(p/'plan.so'));lib.build.argtypes=[ctypes.c_char_p,ctypes.POINTER(Plan)]
 rng=random.Random(86)
 records=[bytes(40),bytes([255])*40,bytes(range(40))]+[bytes(rng.randrange(256) for _ in range(40)) for _ in range(1000)]
 for record in records:
  plan=Plan();lib.build(record,ctypes.byref(plan));expected=m.plans(record)
  for field,stage in [('revision','revision setup'),('boost','boost setup'),('power','power config'),('status','status setup')]:
   ops=getattr(plan,field);ops=ops[:plan.nr] if field=='revision' else ops
   actual=[{k:getattr(o,k) for k in ('amp','register','value','mask')} for o in ops]
   assert actual==expected[stage],stage
  for a in range(2):
   serial=list(plan.serial)[a*16:(a+1)*16]
   assert all(o.amp==a for o in serial)
   assert next(o.value for o in serial if o.register==0x36)==0x20+2*a
print('PASS: 1003 runtime codec plans match stock-derived oracle; stereo routing checked')
