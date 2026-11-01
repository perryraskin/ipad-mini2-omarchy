#!/usr/bin/env python3
import importlib.util,pathlib,unittest
p=pathlib.Path(__file__).resolve().parents[1]/'plan.py'
s=importlib.util.spec_from_file_location('plan',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class PlanTests(unittest.TestCase):
 def test_requires_exact_records(self):
  for v in (None,b'',bytes(20),bytes(39),bytes(41),list(range(40))):
   with self.assertRaises(ValueError):m.plans(v)
  with self.assertRaises(ValueError):m.plans(bytes(40),0xa0)
 def test_channels_and_masks(self):
  records=bytes(range(40));p=m.plans(records)
  for stage,ops in p.items():
   for o in ops:
    self.assertIn(o['amp'],(0,1));self.assertLessEqual(o['register'],0x7f)
    self.assertGreater(o['mask'],0);self.assertLessEqual(o['mask'],255)
   if stage=='revision setup':
    for amp in (0,1):
     a=[o for o in ops if o['amp']==amp]
     self.assertEqual(a[-1]['register'],0);self.assertEqual(a[-1]['value'],0)
  for amp in (0,1):
   vol=[o for o in p['power config'] if o['amp']==amp and o['register']==0x10]
   self.assertEqual([o['value'] for o in vol],[0x19])
   self.assertEqual([o['value'] for o in p['power config'] if o['amp']==amp and o['register']==9],[records[amp*20]])
 def test_no_power_enable_or_volume_restore(self):
  for ops in m.plans(bytes([255])*40).values():
   self.assertFalse(any(o['register']==6 for o in ops))
   self.assertFalse(any(o['register']==0x10 and o['value']!=0x19 for o in ops))
unittest.main()
