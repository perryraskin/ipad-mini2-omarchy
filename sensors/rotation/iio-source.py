#!/usr/bin/env python3
"""Read an explicitly selected future IIO accelerometer; dry-run by default.

No service is installed. Does not configure sensors, load firmware or write IIO.
Axis mapping must come from qualified J86 observations, never a board guess.
"""
import argparse,importlib.util,math,os,pathlib,re,subprocess,time
spec=importlib.util.spec_from_file_location('policy',pathlib.Path(__file__).with_name('policy.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def mapping(value):
 axes=value.split(',')
 if len(axes)!=3 or any(not re.fullmatch('-?[xyz]',a) for a in axes) or len({a[-1] for a in axes})!=3:raise argparse.ArgumentTypeError('Require signed axis permutation, e.g. x,-y,z')
 return axes

def read(device,axes):
 # Offset is in raw counts; scale is SI m/s²/count per the IIO ABI.
 def number(name):return float((device/name).read_text())
 shared=number('in_accel_scale') if (device/'in_accel_scale').exists() else None
 values={}
 for axis in 'xyz':
  raw=number('in_accel_'+axis+'_raw')
  offset=number('in_accel_'+axis+'_offset') if (device/('in_accel_'+axis+'_offset')).exists() else (number('in_accel_offset') if (device/'in_accel_offset').exists() else 0)
  scale=number('in_accel_'+axis+'_scale') if (device/('in_accel_'+axis+'_scale')).exists() else shared
  if scale is None or not math.isfinite(scale) or scale<=0:raise ValueError('Missing/invalid SI scale')
  values[axis]=(raw+offset)*scale
 return [values[a[-1]]*(-1 if a.startswith('-') else 1) for a in axes]

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--device',type=pathlib.Path,required=True);p.add_argument('--axes',type=mapping,required=True);p.add_argument('--expected-name',required=True);p.add_argument('--apply',action='store_true');a=p.parse_args()
 if os.geteuid()!=1000 or pathlib.Path('/proc/device-tree/model').read_bytes().rstrip(b'\0')!=b'Apple iPad mini 2 (Cellular)':raise SystemExit('Exact J86 tablet session required')
 if not re.fullmatch('/sys/bus/iio/devices/iio:device[0-9]+',str(a.device)):raise SystemExit('Require an explicit IIO sysfs device')
 if (a.device/'name').read_text().strip()!=a.expected_name:raise SystemExit('Sensor identity mismatch')
 policy=m.Policy()
 while True:
  target=policy.sample(*read(a.device,a.axes),time.monotonic())
  if target:
   if a.apply:subprocess.run(['/home/tablet/.local/bin/j86-rotate',target],check=True,timeout=10)
   policy.acknowledge(target);print(target,'applied' if a.apply else 'dry-run',flush=True)
  time.sleep(.1)
if __name__=='__main__':main()
