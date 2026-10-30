#!/usr/bin/env python3
import importlib.util,pathlib,math
spec=importlib.util.spec_from_file_location('rotation',pathlib.Path(__file__).resolve().parents[1]/'rotation/policy.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
p=m.Policy()
for i in range(8):assert p.sample(0,9.81,0,i*.1) is None
# Acknowledge only after a real helper success; failed actions remain retryable.
t=p.sample(0,9.81,0,.9);assert t=='portrait';assert p.sample(0,9.81,0,1)=='portrait'
p.acknowledge(t);assert p.sample(0,9.81,0,1.1) is None
for i in range(12,23):assert p.sample(0,0,9.81,i*.1) is None
for i in range(23,34):assert p.sample(7,7,0,i*.1) is None
for i in range(34,45):t=p.sample(9.81,0,0,i*.1)
assert t=='landscape';p.acknowledge(t)
assert p.sample(-9.81,0,0,10) is None # stale stream resets dwell
try:p.sample(math.nan,0,0,10.1)
except ValueError:pass
else:raise AssertionError('NaN accepted')
try:p.sample(0,9.81,0,9)
except ValueError:pass
else:raise AssertionError('Time reversal accepted')
print('Rotation policy: dwell, flat/diagonal rejection, stale stream and acknowledgment passed')
