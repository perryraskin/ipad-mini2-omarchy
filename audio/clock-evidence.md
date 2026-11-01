# J86 boot-declared clock references

`derive-clock.py` executes two stock methods from the exact owner 16H88 cache:
AppleARMIODevice slot0x548 at0x7d48498 translates a bounds-checked index through
its ADT clock-ids, then AppleS5L8960X slot0x540 at0x82c1a58 looks up IDs starting
at0x100 in72-byte records. The SoC initializer at0x82c1524 admits61 records,
loading each first frequency word from a little-endian u32 boot clock table.
The remaining property padding is not another bank. A stock reference tree's
zero placeholder is insufficient; use the owner's live boot ADT privately.

Recovered declared references:

| Consumer | Index | Clock ID | Hz |
| --- | --- | --- | --- |
| NCO | 0 | 0x10b | 342857142 |
| NCO | 1 | 0x10c | 1200000000 |
| NCO | 2 | 0x10d | 24000000 |
| NCO | 3 | 0x10e | 100000000 |
| UART4 | 0 | 0x119 | 24000000 |

The emulator verifies those lookups, out-of-range wrapper indices, and inherited
fallback with an explicitly empty synthetic base table. UART4's second ID4 is
not inferred from the SoC table. These are firmware-declared reference rates,
not frequency-counter measurements or proof of the current parent/mux/gate state.
The NCO primary rate supports the existing stock rational2400000000/7 path;
shared-gate ownership, existing channel-state preservation and restoration remain
unqualified. No NCO/UART rate or control register was written by this model.

Run offline with Unicorn and the local owner-extracted cache/ADT:

```
python audio/derive-clock.py KERNELCACHE --adt LIVE_ADT
```

No cache, ADT, calibration, firmware or identifying logs are published.
