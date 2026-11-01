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
(`j86_audio_session_claim`, or the private v2 `j86_pcm_v2_claim`). The first is supplied by the build-tested fresh-start candidate in
[../sio/native-transport](../sio/native-transport/README.md). Neither
is recreated by this PCM module. The consolidated startup chain still needs live
qualification. I2C2 must already be enabled and owned by that same
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
Tone uses peak1000/32768,500Hz,5ms ramps. The helper now reads kernel result after close and fails if cleanup failed or
status is unavailable. Also inspect matching start/stop counts; this does not
replace physical or long-duration qualification.
Physical volume-button handoff and app audio remain in HANDS-ON-QUEUE.md.

## Startup timing follow-up

The consolidated fresh startup passed on hardware (READY,eight ACKs,I2C2,ALSA
registration and prepare-close). The first muted stream failed at4096frames while
the driver reported a clean stop; the next attempt stalled, and command shells
became unavailable although ICMP still replied. The precise stall cause remains
unproven. The revised candidate completes bounded configure/submit ACKs and mixer
setup in the nonatomic START callback before returning to ALSA. A dedicated
high-priority worker then handles completion events, avoiding the old asynchronous
startup delay. It builds with Werror; live qualification is pending.

Read-only module `phase`:0 initial,1 starting,2 hardware started/worker queued,
3 servicing periods,4 cleanup,5 cleanup returned. This supplements result and
start/stop counters; it is not proof of audible output. Run future exercisers as
bounded background processes with log/PID capture so a blocked PCM call does not
occupy the only network command shell. Inspect the existing process before retry.

## Confirmed callback bug and STOP cancellation evidence

The live diagnostic trace exposed a null substream in the worker. The open callback
incorrectly stored its substream only when `snd_pcm_hw_constraint_integer` returned
zero; ALSA also returns a positive value for successful refinement. The corrected
callback accepts all nonnegative results, records the substream, and returns zero.
`tests/open.py` executes the actual callback with0,1 and negative return values.
This fixes a regression introduced during source-driver consolidation; the earlier
private v2 that produced audible output did not have that condition.

A live STOP tail also contained opcode0x68/tag3/parameter0x80/value0xffffffe0,
a canceled buffer completion arriving after STOP ACK. Cleanup now tracks submitted
slots and waits for their success/cancellation completions plus STOP ACK. The actual
stop routine passes tests with both event orders, missing completions and unowned
tags. These fixes build successfully but await fresh-boot hardware qualification;
the diagnostic worker fault means the current boot must not be reused. No forced
handoff, firmware reload or internal-storage write is part of recovery.

## STOP retirement follow-up

Fresh isolated boot with0e9f205 passed prepare-close,1s drain,1s drop,1s
restart/drain and2s drop. A10s transfer wrote all480000frames but cleanup rejected
tagged completion data0xffffffc0. This is not established to be Linux errno-64.
Orchard apple_sio_dispatch assigns success from expected opcode, not response
data; sio_dma_block_done retires inflight requests during stopping without
interpreting response data. The revised STOP handler follows those semantics:
require endpoint42, tagged0x68, owned pending tag and STOP ACK; data does not
count played frames or determine retirement. receive still rejects error
opcodes0x66/0x6a. Normal playback still requires exactly4096bytes per completion.
Host tests cover opaque STOP data, pending ownership, missing ACK/completions and
error opcodes. Live qualification of this revision remains pending.
