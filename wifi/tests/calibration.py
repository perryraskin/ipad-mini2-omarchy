#!/usr/bin/env python3
"""Exact signed conversion/order plus malformed owner-data rejection."""
import importlib.util,pathlib,struct
p=pathlib.Path(__file__).resolve().parents[1]/'tools/calibration.py'
spec=importlib.util.spec_from_file_location('calibration',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
props={
 'tx-calibration-2.4':struct.pack('<6h',-32768,-1,32767,7,-8,9),
 'tx-calibration-5.0':struct.pack('<18h',*range(-9,9)),
 'rx-calibration-2.4':struct.pack('<54b',*range(-27,27)),
 'rx-calibration-5.0':struct.pack('<32b',*range(-16,16))}
result=m.derive(props)
assert len(result)==31
assert [result['pa2gw'+str(i)+'a0'] for i in range(3)]==['32767','-32768','-1']
assert result['pa5ghw0a1']=='8' and result['pa5glw1a0']=='-9'
assert result['rssi_gain_delta_2ghh']==','.join(map(str,range(9,27)))
assert result['rssi_gain_delta_5gmu']==','.join(map(str,range(0,8)))
for key in props:
 for raw in (b'',props[key][:-1],props[key]+b'\0',b'syscfg/'+bytes(len(props[key])-7)):
  bad=dict(props);bad[key]=raw
  try:m.derive(bad)
  except ValueError:pass
  else:raise AssertionError('Malformed calibration accepted')
for key in ('rx-calibration-temp','freq-group-2g-calibration'):
 bad=dict(props);bad[key]=b'\0'
 try:m.derive(bad)
 except ValueError:pass
 else:raise AssertionError('Unported optional format accepted')
print('PASS: signed calibration ordering, both chains/bands, RSSI groups and malformed/unsupported records')
