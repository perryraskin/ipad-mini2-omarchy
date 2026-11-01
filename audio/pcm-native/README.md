# Native J86 ALSA playback checkpoint

Perry clearly heard a two-second 500 Hz tone from the iPad mini 2 speakers through
ALSA in the isolated `7.0.12-j86-audio2` RAM session. This is physical confirmation,
not just a successful DMA transfer. The tested private v2 driver completed a
one-second muted stream, the two-second tone, and ten seconds muted, with result0
and matching start/stop counts. Preparing then closing without starting also passed.

An explicit drop test exposed a stop-protocol error (`-EPROTO`); the driver reset
the amps and poisoned its session, correctly refusing subsequent playback. The
helper's successful drop/close alone was insufficient: kernel status caught it.
The corrected source here accepts pending descriptor-submit ACKs while awaiting
STOP, and validates status packets. This is a candidate fix, not live-qualified:
the original failure did not retain the unexpected packet, so its precise cause
still requires confirmation. Do not clear poison, unload modules, or reload SIO
firmware to bypass a failed stop. Recover with a clean RAM boot.

## Source and prerequisites

`j86_pcm_native.c` is a fixed-format ALSA PCM with mute and -60..0 dB mixer controls,
48 kHz stereo S16_LE, four 1024-frame periods, and prepare-time clock/amp setup.
Output defaults muted at -30 dB. Amp status, reset, clock and route cleanup are
checked; coherent memory and provider ownership remain pinned until RAM reboot.
Do not enable persistent output or desktop autostart yet.

Unlike the confirmed private v2 module, this source contains no speaker calibration
and no hardcoded module-address bridge. `request_firmware_direct` requires the
owner's exact 40-byte `apple/j86-speaker-config.bin`, plus its explicit SHA256 in
`calibration_sha256`. Supply it only to the RAM firmware directory; never distribute
it or substitute another board's records. No internal-storage access is involved.

Activation requires `allow_pcm=1`, exact J86, 4 KiB pages and matching kernel;
it also requires an existing **exclusive, healthy** retained transport provider
(`j86_audio_session_claim`, or the private v2 `j86_pcm_v2_claim`). The first is a
future integration interface, not a shipped cold-start implementation. Neither
is recreated by this module. I2C2 must already be enabled and owned by that same
session. Current generic SIO A7 activation remains blocked; this is **not a turnkey
fresh-boot audio installer**. Default load refuses before touching hardware.

The source builds with `bash audio/pcm-native/build.sh` against the prepared Lima
`j86-build` audio kernel. No firmware/calibration is needed to compile. The public
build omits all private bench sources and binaries. `tests/plans.py` compares 1003
synthetic calibration inputs against the stock-derived Python codec oracle;
`tests/protocol.c` checks stop traffic classification. These tests do not prove
hardware recovery, sample rate accuracy, long-duration thermal behavior, speaker
channel separation, desktop integration or coexistence with touch/Wi-Fi.

`test-playback.c` is the bounded libasound exerciser (link with `-lasound -lm`).
Modes: `--silence`, `--tone`, `--prepare-close`, `--drop`; durations1..10seconds.
Tone uses peak1000/32768,500Hz,5ms ramps. Always inspect kernel result and matching
start/stop counts after close; the helper cannot certify asynchronous cleanup.
Physical volume-button handoff and app audio remain in HANDS-ON-QUEUE.md.
