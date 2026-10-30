#!/usr/bin/env python3
import argparse,importlib.util,pathlib,tempfile
spec=importlib.util.spec_from_file_location('iio',pathlib.Path(__file__).resolve().parents[1]/'rotation/iio-source.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as tmp:
 p=pathlib.Path(tmp)
 for key,value in {'in_accel_x_raw':'10','in_accel_y_raw':'20','in_accel_z_raw':'30','in_accel_scale':'.5','in_accel_offset':'2'}.items():(p/key).write_text(value)
 assert m.read(p,m.mapping('y,-x,z'))==[11,-6,16]
 (p/'in_accel_x_scale').write_text('.25');(p/'in_accel_x_offset').write_text('0')
 assert m.read(p,m.mapping('x,y,z'))==[2.5,11,16]
 for bad in ('x,x,z','x,y','x,y,zz'):
  try:m.mapping(bad)
  except argparse.ArgumentTypeError:pass
  else:raise AssertionError(bad)
 (p/'in_accel_scale').write_text('0')
 try:m.read(p,m.mapping('x,y,z'))
 except ValueError:pass
 else:raise AssertionError('Zero scale accepted')
print('IIO source: explicit mapping, shared/per-axis scale and offset guards passed')
