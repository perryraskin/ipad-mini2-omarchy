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
