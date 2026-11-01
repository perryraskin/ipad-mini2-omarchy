# J86 Switch3 offline adaptation

`j86-switch-plan.h` is a pure encoder for the exact `aud1`/`pin1` pair, not a
hardware driver. It has no activation path, MMIO access or clock operation.
The two directions, two stock modes and two stock lanes are modeled separately.
Those arguments are not yet assigned physical clock/data direction semantics.
Do not combine their masks into a board routing recipe without the full router.

Exact stock cache SHA256:
`d173a651d02329a02d2f23c2859e1e54308a5e94da86ba729777efeb3503da08`.
`derive-switch.py` verifies the `AppleAE2I2SSwitch3` class string, then executes:

- defaults at `0x863e39c`: fourteen `0x181818` words, one `0x18`, five zeroes;
- word/node counts at `0x863e400` and `0x863e408`: 20 and 15;
- edge encoder at `0x863e54c`: eight `aud1`/`pin1` cases agree with the C backend;
- invalid lane 2: rejected before touching scratch arrays;
- writer at `0x863e3dc`: twenty contiguous 32-bit synthetic stores.

The same cache contains Switch5 and AOPSwitch1 implementations with different
node layouts and write spans. They must not be substituted for Switch3.
In particular, Switch3's writer includes offsets 0x2c through 0x38; the newer
Switch5 writer skips that span. All modeled MMIO is Unicorn memory, not a device.
No owner firmware bytes or calibration are included in these sources.

Reproduce locally with an owner-extracted cache and Unicorn installed:

```sh
cc -std=c11 -Wall -Wextra -Werror audio/switch/tests/plan.c -o /tmp/j86-switch-plan
python audio/derive-switch.py /path/to/exact/kernelcache --backend /tmp/j86-switch-plan
```

The C build/argument guards run in public CI; stock-code agreement was checked
locally and requires the private cache. Next: reconstruct the superclass graph
router and ADT default routes, resolve the meaning of `0x00330303`, ownership,
restore paths and clock-master selection. Then qualify NCO parent/gates and SIO
while both amplifiers remain reset. There is no live routing/playback result.

## Full isolated TX graph model

`derive-router.py` now executes the exact superclass router at 0x7d634c8,
its connection evaluator and the platform-function wrapper at 0x7d6347c.
The J86 switch ADT has no default-routes property. The model starts with an
empty 15-node graph and the stock 20-word defaults, and uses this board's
`aud1`/`pin1` descriptor argument 0x00330303. Locks, OSArray allocation,
diagnostic strings, property publication and notifications are explicit fakes;
unknown calls or instruction-budget exhaustion fail the model.

`derive-mca.py --lifecycle-model --route-call-model` separately captures MCA's
TX-start callback mask2 with value1 for slave and value2 for master, then stop
mask0/value0. Feeding these into the full router produces the two complete C
TX tables. Both stop paths return to the modeled defaults. This adds a complete
isolated graph result, not a method for importing existing live hardware routes.

```sh
python audio/derive-router.py /path/to/exact/kernelcache --backend /tmp/j86-switch-plan
```

Real clock ownership, coexistence with other consumers, preservation of live
state, clock-parent selection and hardware restore still need qualification.
No switch register was written on the iPad. A full table from a fresh fake graph
is not a safe live programming recipe.
