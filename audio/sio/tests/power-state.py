#!/usr/bin/env python3
import importlib.util,pathlib
p=pathlib.Path(__file__).resolve().parents[1]/'power-state.py'
s=importlib.util.spec_from_file_location('power',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
r=m.compare(0x1f0000ff,0x1400024f)
assert r['control_fields_unchanged'] and not r['exact_word_unchanged']
assert r['after']['state']=='consistent-with-auto-clock-gating'
assert not r['restoration_qualified']
assert not r['unclassified_bits_changed']
assert m.compare(0xff,0xff|(1<<22))['unclassified_bits_changed']
for bit in (m.RESET,m.AUTO_ENABLE,1<<16,m.DEV_DISABLE,1):
 assert not m.compare(0x1f0000ff,0x1400024f^bit)['control_fields_unchanged']
for bit in (m.RESET,m.DEV_DISABLE,m.PARENT_OFF):
 assert m.decode(0x1400024f|bit)['state']=='blocked'
assert m.decode(0x0400024f)['state']=='unresolved'
assert m.decode(0x1f00004f)['state']=='unresolved'
assert m.decode(0)['state']=='off'
assert m.decode(0xff)['state']=='active'
for value in (-1,1<<32,True,'0'):
 try:m.decode(value)
 except ValueError:pass
 else:raise AssertionError(value)
print('PMGR status/control distinction and refusal cases passed; no hardware qualification.')
