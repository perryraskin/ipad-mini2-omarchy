#!/usr/bin/env python3
"""Audit saved blkid export/fstab text on the host; never probe or modify a device."""
import argparse
import json
import pathlib
import stat


def audit(inventory, fstab):
    records = []
    for block in inventory.strip().split('\n\n'):
        record = {}
        for line in block.splitlines():
            key, sep, value = line.partition('=')
            if not sep or key in record:
                raise ValueError('Malformed or duplicate blkid field')
            record[key] = value
        if record:
            if not record.get('DEVNAME', '').startswith('/dev/'):
                raise ValueError('Missing absolute DEVNAME')
            records.append(record)
    roots = [line.split() for line in fstab.splitlines()
             if line.strip() and not line.lstrip().startswith('#')]
    roots = [row for row in roots if len(row) >= 2 and row[1] == '/']
    if len(roots) != 1 or len(roots[0]) < 4:
        raise ValueError('Require exactly one complete root fstab entry')
    selector, sep, identity = roots[0][0].partition('=')
    if selector not in ('UUID', 'PARTUUID') or not sep or not identity:
        raise ValueError('Root must explicitly use UUID= or PARTUUID=')
    # blkid export calls the GPT partition identifier PART_ENTRY_UUID.
    field = {'UUID': 'UUID', 'PARTUUID': 'PART_ENTRY_UUID'}[selector]
    matches = [r for r in records if r.get(field) == identity]
    if len(matches) != 1:
        raise ValueError('Root identity is absent or ambiguous in saved inventory')
    record = matches[0]
    if roots[0][2] != record.get('TYPE'):
        raise ValueError('Root filesystem type disagrees with saved inventory')
    if record['TYPE'] != 'ext4':
        raise ValueError('Only a separate ext4 candidate is modeled; never the iOS APFS root')
    return {'identity_match': True, 'candidate_device': record['DEVNAME'],
            'selector': selector,
            'required_link_directory': '/dev/disk/by-' + selector.lower(),
            'live_link_resolution': 'NOT_CHECKED', 'install_ready': False,
            'boot_default': 'RAM',
            'remaining': ['Verify early-boot udev/blkid support for ASP block names',
                          'Verify live link target against the captured partition identity',
                          'Qualify exact-board read-only ASP transport and recovery',
                          'Obtain explicit owner approval before any internal writes']}


def saved_text(path):
    # Do not accept device nodes/FIFOs as offline input, including through symlinks.
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError('Input must be a saved regular host file')
    if path.stat().st_size > 1024 * 1024:
        raise ValueError('Input exceeds 1 MiB')
    return path.read_text()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--blkid-export', type=pathlib.Path, required=True)
    p.add_argument('--fstab', type=pathlib.Path, required=True)
    a = p.parse_args()
    try:
        print(json.dumps(audit(saved_text(a.blkid_export), saved_text(a.fstab)), indent=2))
    except (ValueError, OSError) as error:
        p.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
