# J86 speaker codec preparation

Both physical CS35L19 amplifiers returned ID 35a190, revision B0 on the isolated
audio2 kernel. Identity reads passed with reset, keepalive, I2C pin words and
I2C2 power restored exactly, and the temporary I2C bus removed. This establishes
identity, not playback.

`plan.py` models register writes from four exact J86 stock routines: revision
setup, boost setup, power configuration and status setup. It requires both
private 20-byte speaker records; there are no Mini 1 fallback values. The plan
preserves per-channel values and masks. No I2C executor is provided. The status
stage omits the stock read-to-clear reads, and GPIO, delays and callbacks remain
unmodeled. Do not execute these write lists as a power-on sequence.

`derive-amplifier.py` compares all four plans against the exact stock code in
Unicorn. The owner's two records and 12 generated cases passed; generated cases
exercise optional revision writes and distinct channel values. Private input
files and traces are not distributed. Public CI tests input rejection, channel
separation, register bounds, mute and absence of power-enable writes.

Remaining: shared SIO resource ownership/cleanup, real NCO/route ownership,
muted cyclic DMA, checked codec I2C and status handling, verified serial format
and keepalive, then a low-volume bounded physical playback test. No ALSA card or
volume-key audio mode is qualified. The Mini 1 driver is a reference, not a J86
power-on implementation.


The optional `derive-amplifier.py --serial-model` now executes stock serial
configuration at 0x81f4ed4 with explicit synthetic 48kHz, two-byte-slot descriptors
and no sense channels. All 32 operations match the stereo16 plan, including
RX_AUD 0x20/0x22 rather than the Mini1 driver's 32-bit-slot 0x60/0x64. The earlier
model labeled this skipped function a GPIO/keepalive callback; it is actually
serial configuration. The default model still stubs keepalive configuration at 0x81f582c and
amplifier clock control at 0x81f6478; the latter is not a GPIO operation. MCA's NCO clock and the amplifier's declared 12MHz MCLK must not be
conflated; actual codec clock/power qualification is still pending.

`--power-model` now executes the full stock muted power-on/off routines,
including those two helpers. It checks ordered register writes, status reads,
10/8ms power-on and 1/4ms power-off waits, keepalive register configuration,
three initial GPIO transitions and timer start/cancel callbacks. Both optional
keepalive branches pass. External clock, GPIO, timer and elapsed-time services
remain modeled, and the clock-function branch is a synthetic fixture, not a
claim that J86 advertises function-mclk_control. The real J86 speaker node lacks
that property and falls back to the audio provider's clock-control interface.

The live ADT maps MCA1's second region to 0x20a002004, size4. Stock MCA maps it
into object+0x148. With an explicitly modeled 24MHz `nclk` and the stock 12MHz
speaker descriptor, clock-selection routine0x863cda4 produces0x58; disabling
MCLK through0x863cf80 yields0x18. `derive-mca.py --amp-clock-model` checks this
separate register, which earlier models omitted. MCA+0x40 is used as an
interrupt-status/acknowledgement register; it is not this MCLK control.

Live bounded qualification: the separate clock register was stably0. A
RAM-only, default-off test with both amps reset wrote0x58, read0x58, and restored
exactly0. This establishes register access/readback, not physical frequency or
speaker playback. The existing SIO firmware/buffers remain resident and the
successful muted-DMA handoff remains available. The next stage must own this
clock region alongside the amp reset/keepalive and checked I2C lifecycle.

Further live checks on the same isolated RAM boot passed: both B0 amplifiers
powered up digitally muted and returned status00/00, then shut down with reset
and clock restored. The combined muted amplifier/DMA test completed4096bytes.
A subsequent bounded500Hz sine test transferred192000bytes in about one second
(stereo16,48kHz,peak1000/32768,5ms ramps,codec0dB), received completion and stop
ACKs, and restored reset/NCO/switch/clock. Audible confirmation is pending;
this is not yet a qualified ALSA playback device or a speaker-audio success claim.
The temporary bench binaries contain owner calibration and are not distributed.
