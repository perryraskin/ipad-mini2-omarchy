#!/usr/bin/env python3
import importlib.util
import pathlib
spec = importlib.util.spec_from_file_location('audit', pathlib.Path(__file__).parents[1] / 'root-identity-audit.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
inventory = 'DEVNAME=/dev/asp0p2\nUUID=fs-example\nPART_ENTRY_UUID=gpt-example\nTYPE=ext4\n'
fstab = 'UUID=fs-example / ext4 ro 0 1\n'
assert m.audit(inventory, fstab)['install_ready'] is False
assert m.audit(inventory, fstab)['live_link_resolution'] == 'NOT_CHECKED'
assert m.audit(inventory, fstab.replace('UUID=fs-example', 'PARTUUID=gpt-example'))['candidate_device'] == '/dev/asp0p2'
for inv, fs in [
    (inventory, fstab.replace('fs-example', 'gpt-example')),
    (inventory, fstab.replace('fs-example', 'absent')),
    (inventory + '\n' + inventory.replace('asp0p2', 'asp0p3'), fstab),
    (inventory, fstab + fstab),
    (inventory, fstab.replace('UUID=fs-example', '/dev/asp0p2')),
    (inventory.replace('ext4', 'apfs'), fstab.replace('ext4', 'apfs')),
    (inventory, fstab.replace('ext4', 'xfs')),
    (inventory + 'UUID=duplicate\n', fstab),
]:
    try: m.audit(inv, fs)
    except ValueError: pass
    else: raise AssertionError('Unsafe or ambiguous identity accepted')
try: m.saved_text(pathlib.Path('/dev/null'))
except ValueError: pass
else: raise AssertionError('Device input accepted')
print('Offline root identity: UUID/PARTUUID, missing/duplicate identities, APFS refusal and device-input rejection passed')
