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
serial configuration. GPIO/keepalive callbacks at 0x81f582c/0x81f6478 remain
mocked. MCA's NCO clock and the amplifier's declared 12MHz MCLK must not be
conflated; actual codec clock/power qualification is still pending.
