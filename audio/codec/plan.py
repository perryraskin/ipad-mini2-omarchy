#!/usr/bin/env python3
"""Offline J86 CS35L19 write plans. No I2C executor or power-on sequence.

Models only four stock subroutines with board mode=0, no alternate calibration,
zero sense descriptor and caller state=2. GPIO, reads, delays and callbacks
must be implemented separately before this can become a codec driver.
"""
def plans(records, revision=0xb0):
    if not isinstance(records, bytes) or len(records) != 40:
        raise ValueError('Require two exact 20-byte records; no fallback')
    if revision != 0xb0:
        raise ValueError('Only measured B0 revision is supported')
    result = {stage: [] for stage in ('revision setup', 'boost setup', 'power config', 'status setup')}
    def add(stage, amp, reg, value, mask=255):
        result[stage].append(dict(amp=amp, register=reg, value=value, mask=mask))
    for amp in range(2):
        c = records[amp*20:(amp+1)*20]
        stage = 'revision setup'
        for reg, value in [(0,0x99),(0x45,0x3f),(0x46,c[16]),(0x51,0xff),(0x59,0x0a),(0x6b,0x20)]:
            add(stage,amp,reg,value)
        if c[18]: add(stage,amp,0x54,c[18])
        add(stage,amp,0,0)
        if c[17]:
            for reg,value in [(0,0x99),(0x66,c[17]),(0,0)]: add(stage,amp,reg,value)
        add('boost setup',amp,0x0b,c[1]&0x3f)
        add('boost setup',amp,0x0c,c[2],3)
        stage = 'power config'
        for reg,value,mask in [(7,0xf8,255),(8,0x40,0xc0),(9,c[0],255),(0x10,0x19,255),
                               (0xf,0,0x10),(0x11,0x1c,255),(0xe,0xc4,0xcf),(0x12,c[3],0xf0)]:
            add(stage,amp,reg,value,mask)
        for n in range(4): add(stage,amp,0x3a+n,c[12+n])
        stage = 'status setup'
        # Stock reads 0x15 twice and 0x16 twice BEFORE these writes.
        # These reads and their hardware side effects are not represented here.
        for reg,value in [(0x17,0x5a),(0x18,c[19]),(0x17,0)]: add(stage,amp,reg,value)
        for n,mask in enumerate((0x7f,0xff,0x1c,0xff,0x3f,0xff,0x7f,0x9f)):
            add(stage,amp,0x23+n,c[4+n],mask)
        add(stage,amp,0x11,0x14)
    return result
