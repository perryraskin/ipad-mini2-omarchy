# A7 MCA-v1 adaptation checkpoint

`j86-mca-plan.h` replaces the A9 register backend with a pure, fixed-format A7
configuration plan. It has no MMIO executor, clock writes, codec writes, module
loader or activation path. Host C compilation uses `-Wall -Wextra -Werror`.

Orchard reference: hardware commit
`4f15a70b9c59687fe8cd72b6ea2fbb2823c54d92`, patch
`0003-ASoC-apple-Add-S8000-MCA-driver.patch` (Berkay Kösebay, GPL-2.0-only OR MIT).
Reuse its ASoC DAI, dmaengine PCM, period limits and lifecycle design when the
A7 hardware dependencies are qualified. Do not use its register layout, IRQ
mask, codec clock provider, stream-stop reset, or A9 MCLK control word for A7.
This backend is independently transcribed from the exact J86 stock model.

## Evidence and boundaries

Exact owner-cache SHA256:
`d173a651d02329a02d2f23c2859e1e54308a5e94da86ba729777efeb3503da08`.
`derive-mca.py` executes stock configure `0x863b7fc` and TX start `0x863c61c`, plus stop `0x863c8f8` with `--lifecycle-model`
in Unicorn with explicit fake platform callbacks and busy-clear values.
The C backend matched all 40 modeled configure/start/stop writes for the two descriptors. This is
model agreement, not physical playback, interrupt qualification. TX stop invokes the modeled IRQ-object callback, writes TX config0 at0x18 and reset1 at0x44, then polls bit0 clear. Stock does not clear the frame-run bit in this observed stop path; do not add an A9 frame-stop write. Busy bits are modeled as immediately clear, not timed hardware.
Only the fixed 48 kHz/stereo/16-bit bring-up format is admitted by the backend;
other PCM formats are rejected. Reset/flush require bounded busy-clear polls;
the plan cannot simply be written in a loop on real hardware.

MCA1 is `0x20a0c4000`, IRQ148, domain `0x20050`, version1, measured
TX/RX FIFO128 words. A7 places TX config at0x18, TX FIFO at0x20,
RX config at0x2c, frame at0x0c and reset/flush at0x44/0x48. A9 uses
TX0x60, RX0x80, frame0x10 and reset0x0c. Those overlaps make substitution unsafe.

J86 stock ADT names the route `aud1` → `pin1`, argument `0x00330303`, at
switch `0x20a003000`; MCA's second resource is `0x20a002004` (4 bytes).
The exact cache's `AppleAE2I2SSwitch3` personality matches
`i2s-switch,s5l8960x`. This supports investigating the same switch generation
as Orchard's implementation, but does not establish its route direction,
output-enable state, reset ownership or board clock master. No switch write
is included in this backend.

`function-mclk_frequency` resolves to NCO index1. The NCO bank starts at
`0x20e011000`; NCO1 is `0x20e012000`. Stock master configuration requests
12.288 MHz. `derive-mca.py --nco-model` executes the stock NCO algorithm;
its default342857142 Hz parent and24 MHz limit are fake clock-provider inputs,
not measured hardware facts. A clock driver must first resolve the real parent
rates and gate ownership. Do not turn the modeled NCO words into a live script.

ADT SIO TX/RX endpoints are0x2a/0x2b. The16-bit shim is
`[0x21,0,0xcc,0xac,0,0,0]`, and32-bit uses0x22. The frame parameter is4 bytes
for the fixed stereo16 format; it is not FIFO depth. Keep SIO boot disabled.

## Remaining driver work

1. Derive and cross-check exact switch3 route encoder and NCO parent/gate setup,
   including restore paths and interaction with existing power consumers.
2. Add A7 IRQ/status and non-clearing-reset/error-path models. The A9 bit layout is not evidence.
3. Connect this backend to Orchard's DAI/PCM lifecycle only after those operations
   have independent models; retain explicit board, version, format and opt-in gates.
4. Qualify SIO boot and muted cyclic DMA before building a speaker machine driver.
5. Implement exact CS35L19 board-calibrated sequencing with both private speaker
   records. Keep reset/mute asserted until clocks and DMA are stable. No A5 defaults.

Physical stages are ordered in [HANDS-ON-QUEUE.md](../../HANDS-ON-QUEUE.md).
