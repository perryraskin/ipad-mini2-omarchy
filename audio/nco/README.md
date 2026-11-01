# Fixed-format A7 NCO model

`j86-nco-plan.h` computes only the primary-parent NCO1 plan for the fixed
12.288 MHz MCLK. It has no MMIO executor, clock provider, DT binding or loader.
The supplied parent frequency must never be treated as a measured J86 clock.

The exact hash-guarded stock implementation at 0x82c1fc8 is independently
executed by `derive-mca.py --nco-model --nco-parent-rate HZ --nco-backend PATH`.
Six synthetic parents (96, 192, 240, 400 and 600 MHz, plus 342857142 Hz) match
all six C-plan writes. The last value uses stock's exact 2400000000/7 rational
special case. Tests do not establish which provider/mux is active on hardware.

A7 differs from the modern Asahi NCO implementation: channel stride is 0x1000,
coarse-divisor offset is 3 in this stock path, accumulator initialization is
`(remainder ^ 0x80000000) - denominator*rate`, and the observed enable control
includes 0x1000. Do not substitute the modern offset2/neutral-accumulator words.
The modeled writer waits for control bit30 before parameter writes; busy bits
are modeled clear. A future executor needs bounded waits and an error path.

Only the first-parent, argument-flags-zero path is admitted. Alternate provider
selection/fallback, crystal limits, parent/gate leases, shared channels, restore
and real-rate measurement are unresolved. The register words must not be run
as a hardware script. No NCO, routing or amplifier writes were made on the iPad.

```sh
cc -std=c11 -Wall -Wextra -Werror audio/nco/tests/plan.c -o /tmp/j86-nco-plan
python audio/derive-mca.py /path/to/exact/kernelcache --nco-model \
  --nco-parent-rate 342857142 --nco-backend /tmp/j86-nco-plan
```
