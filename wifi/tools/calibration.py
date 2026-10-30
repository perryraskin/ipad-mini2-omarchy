#!/usr/bin/env python3
"""Exact J86 stock DT-to-NVRAM calibration mapping; pure, offline transformation.

Validated against the matching stock-code model. This is not RF qualification.
The caller must establish the board, stock firmware, vendor and owner data.
"""
import struct

def derive(props):
 expected={'tx-calibration-2.4':12,'tx-calibration-5.0':36,
           'rx-calibration-2.4':54,'rx-calibration-5.0':32}
 for key,size in expected.items():
  raw=props.get(key,b'')
  if len(raw)!=size or raw.startswith(b'syscfg/'):
   raise ValueError('Require exact live '+key+' record')
 # Optional forms require different stock presence flags and are unported.
 for key in ('rx-calibration-temp','freq-group-2g-calibration'):
  if key in props:raise ValueError('Unported optional calibration: '+key)
 result={}
 tx2=struct.unpack('<6h',props['tx-calibration-2.4'])
 tx5=struct.unpack('<18h',props['tx-calibration-5.0'])
 for chain in range(2):
  for word,source in enumerate((2,0,1)):
   result[f'pa2gw{word}a{chain}']=str(tx2[chain*3+source])
   for band,offset in [('5gl',0),('5g',3),('5gh',6)]:
    result[f'pa{band}w{word}a{chain}']=str(tx5[chain*9+offset+source])
 for key,names,chunk in [
  ('rx-calibration-2.4',('2g','2gh','2ghh'),18),
  ('rx-calibration-5.0',('5gl','5gml','5gmu','5gh'),8)]:
  raw=props[key];values=struct.unpack('<'+'b'*len(raw),raw)
  for index,name in enumerate(names):
   result['rssi_gain_delta_'+name]=','.join(str(v) for v in values[index*chunk:(index+1)*chunk])
 return result
