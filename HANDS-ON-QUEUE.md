# Ordered physical validation checklist

**Next: restore the working RAM desktop, then HDMI.** Speaker output and volume
change are confirmed; remaining audio integration stays queued. The peripheral
order remains HDMI, Bluetooth/wired input, touch rotation, auto-rotation, suspend.

Never restore, repartition, flash, erase or install to iPad internal storage.
Candidate code remains opt-in. Builds and host tests are not hardware qualification.
Stop on unexpected output and retain diagnostics before advancing.

## Release review gate (11 November 2026)

The [v0.3.0 source review](research/A7-UPDATE-2026-11-11.md) was offline only.
For the next qualification session, inspect USB identity, then arrange one fresh
DFU RAM boot with the existing `known-good` payload and confirm the desktop.
Do not replace it with Orchard's experimental J86 image or Mini 3 m-suffix
profiles, enable generic suspend, or use install/launch to follow release notes.
The older healthy-session reuse option below is not a fresh-boot validation.

Keep HDMI before Bluetooth, then orientation/auto-rotate/suspend. Before removing
the host cable for HDMI, qualify a self-contained RAM root and detach Mac NBD/app
storage. Suspend is last, on a separate self-contained RAM candidate; use staged
pm_test checks and the guide's boot-ID/wake-IRQ/timekeeping evidence. Untested
boards can reboot or fail to wake. Keep automatic sleep disabled.

All internal-storage writes, including creating m1n1 boot entries, still need
Perry's explicit yes plus verified backup and a reviewed plan. Nothing here
authorizes those writes. No device was inspected or touched for this update.

## Next return to the iPad (7 November update)

No iPad actions were taken during this offline update. See [new J72 replication
material](research/A7-UPDATE-2026-11-07.md), [storage gates](research/A7-UPDATE-2026-11-06.md)
and [roadmap](ROADMAP.md). J72 speakers, battery, guarded charging and USB
reconnect are community Air 1 results, not new J86 qualifications. Do not copy
its charging current, auto-enable audio or unplug the Mac-backed root on that
evidence. Fresh-boot audio and charging under load remain open even on J72.

1. Connect the known-working USB-A-to-Lightning cable to the Mac. Keep it attached
   while the host inspects USB mode and the current kernel/boot identity.
2. If still in isolated audio or back in iOS, enter DFU: hold Home + Power for
   about 8 seconds, release Power and hold Home about 10 seconds, then release.
   The screen stays black; the host must verify DFU identity before upload.
   An Apple logo or cable icon means stop and report the mode, not repeat uploads.
3. From the prepared private workspace run `./ipad-linux --profile known-good start`.
   This uses current source tooling with the existing qualified RAM payload,
   not a newly qualified kernel or a public source-only download. Reconnect
   Lightning without pressing buttons only when the loader prompts for it.
   If already running a healthy compatible desktop, skip DFU and reuse it.
4. Confirm Home opens the menu, Terminal responds and brightness works. Keep the
   cable connected. Do not load isolated audio alongside touch/Wi-Fi. Then proceed
   to HDMI, Bluetooth/wired input, orientation, auto-rotation and suspend below.

Audio's audible output and changing volume are already confirmed. Remaining audio
integration tests stay queued; they do not force another isolated audio session
before restoring the desktop or preparing HDMI. Internal storage is a separate
future opt-in: backup first; explicit approval before snapshot deletion, resize,
partition edits, write tests, formatting or installation. No such step is included
in this physical sequence.

## Detailed physical checks, in order

1. **Finish audio.** The public a8c6a0e driver passed isolated prepare-close,
   drain/drop/restart,10s muted playback and another restart. Perry confirmed
   the subsequent2s tone; kernel result0 and7starts/7stops. Next qualify volume/
   mute, channel separation, volume keys and desktop/coexistence; no fresh boot
   is required while the current owner remains healthy. Inspect USB and the actual boot/session state on return before
   deciding how to recover. Do not reload SIO firmware, unload retained modules,
   clear a poisoned-session flag or force a transport handoff. The isolated
   [audio startup procedure](audio/sio/native-transport/README.md) uses
   `./ipad-linux --profile audio-candidate --isolated start`; ordinary desktop
   startup must not run alongside the isolated shared-controller experiment.
   Qualify muted prepare-close, normal drain, interrupted/drop playback, next-open
   playback, result/start/stop counters, reset and clock restoration. Then qualify
   low-volume left/right output, mute/volume, physical volume-key handoff and
   return to brightness mode, sustained playback and app audio. Restore desktop,
   touch and Wi-Fi coexistence only after shared ownership is resolved. Stop on
   heat, distortion, missing clock or DMA errors. Use only exact private J86
   firmware and speaker records; no other-board calibration defaults.
2. **HDMI external display — next after audio.** Prepare a bounded observation
   and a safe recovery path before swapping the Mac Lightning cable for Perry's
   Apple Lightning Digital AV adapter. Verify the exact LG 5K model and accepted
   inputs; some LG 5K models do not accept HDMI. Use a compatible monitor/TV if
   needed. Record detection and actual output, then qualify resolution and desktop
   usability. Detection alone does not prove video output. Coordinate cable swaps
   only when Perry is ready; never unplug an active Mac-backed root without prep.
3. **Bluetooth mouse, trackpad and keyboard — after HDMI.** Do not start Bluetooth
   bring-up until HDMI qualification is complete. Prefer native iPad Bluetooth:
   qualify controller/firmware/transport, pairing, pointer movement, left/right
   click, scrolling and supported gestures; test keyboard text, modifiers, layout
   and repeat. Check peripheral reconnect and combined HDMI/Wi-Fi use. If native
   BT needs a wired fallback, use an Apple Lightning-to-USB Camera Adapter
   (powered USB3 version and powered hub if needed) with USB-compatible inputs.
   Record the exact adapter chain and qualify wired input separately from BT.
4. **Four-orientation touch/resize cycle — after HDMI and Bluetooth.** Touchscreen
   feature work remains deferred until this point. Test portrait,90°,180°,270°,
   then portrait; verify taps, window dragging and outside-corner resize in each,
   and restore after desktop restart. Log failed transforms before another attempt.
   Recheck long-press right-click, minimized-window restore, scrolling and Home.
5. **Auto-rotation — after HDMI and Bluetooth.** Qualify UART4 clock/baud/power,
   Oscar/M7 transport, sensor subscription/report decoder and calibrated IIO
   acceleration before enabling policy. Verify identity, SI units and signed
   panel-axis mapping in stationary poses. Dry-run the policy; test flat/diagonal/
   shaking rejection and stale data. Apply only after mapping is confirmed, then
   verify touch/window alignment. Manual rotation remains the fallback.
6. **Suspend/power experiments — after HDMI and Bluetooth.** Use a separate,
   self-contained RAM root with NBD detached and app writes flushed. Never suspend
   a Mac-backed root. Inspect mem_sleep and wake IRQs; qualify freezer/device stages
   before real sleep. Test Home/Power wake, USB/serial, timekeeping, display, touch,
   wireless/audio and measured power. Do not expose suspend until repeated resume
   works. Existing screen-off/wake and held-Power menu are not true SoC suspend.

Existing app-storage and Wi-Fi checks remain prerequisites when their services are
used, not reasons to move rotation or suspend ahead of HDMI/Bluetooth. Keep the
installer hidden on unqualified profiles. Preserve signed package checks and the
read-only base root; apps write only to the separate qualified Mac-backed image.
Keep credentials, firmware, calibration and identifying traces private.

## Evidence at the pause

- Perry confirmed scale2 aligned taps, dragging, long-press menus, minimized-window
  restore, brightness, screen-off/wake and the held-Power menu. Landscape taps,
  Smaller window and corner resizing also passed. The full four-orientation cycle
  is incomplete; auto-rotation and SoC suspend are unqualified.
- Mac-backed storage passed bounded16MiB fsync/readback, detach, offline filesystem
  checks, remount persistence and signed Calculator reinstall. Perry confirmed
  Calculator, dragging and Firefox scrolling after cache/animation adjustments.
  Ordinary startup hides installs; this does not qualify every candidate profile.
- Native Wi-Fi association, DHCP, DNS and direct HTTPS passed on audio2, including
  owner-confirmed combined touch use. Long-duration/disable-recovery remains open.
- **Native speaker output is physically confirmed:** Perry clearly heard the
  two-second500Hz ALSA tone. Normal muted drains at1s and10s passed on the earlier
  private v2 driver. A drop test later failed stop handling and poisoned that boot.
- The subsequent fresh audio2 boot passed SIO resource preflight, firmware READY,
  all eight consolidated A7 setup ACKs, I2C2 enable and native PCM registration.
  Prepare-close passed. A muted stream failed at4096frames despite driver result0
  and matching1start/1stop. The next muted attempt stalled; serial and network
  commands stopped returning while ICMP remained responsive. Cause is unproven.
  Do not call this stable playback or a qualified stop fix.
- Shutdown was requested at the pause, but the unresponsive device command channels
  prevent verified clean iPad power-off. No firmware reload or storage change was
  attempted. Host services are being stopped; inspect actual device state on return.
- Oscar receive observation previously saw no bytes and restored power. Sensor
  streaming remains unqualified. The suspend diagnostic payload is build-only.
  HDMI and Bluetooth are unqualified and retain the priority above.

Latest audio follow-up: corrected ALSA open now transfers a complete 48,000-frame
muted stream. STOP cleanup still failed with -EPROTO; the stopped RX diagnostic
found no queued events. Handling of Orchard channel-idle notifications and STOP
packet diagnostics now builds and passes host regressions, but needs a fresh
RAM boot and live drain/drop/restart tests. Stable audio remains unqualified.

Follow-up on the next fresh boot: prepare-close and the full muted one-second
normal drain both passed with kernel result0. Interrupted playback exposed a
valid partial completion (80 bytes) rejected by STOP cleanup. The handler now
accepts bounded partial byte counts for owned descriptors, with exhaustive host
coverage of0..4096; overflow/unknown error codes still fail. This correction is
build-tested only; fresh-boot drop/restart and audible/volume tests remain.

Next isolated boot passed drain/drop/restart, but the10s drain hit completion
data0xffffffc0 during cleanup. Revised STOP request retirement now follows
Orchard opcode/tag semantics rather than interpreting response data as errno;
normal playback still validates full periods. This latest revision needs live
qualification; do not reuse the poisoned owner or call audio finished.

Latest isolated audio checkpoint: audible volume increase confirmed by Perry;
both amplifier volume registers independently observed changing. Left-only/right-
only playback passed mechanically,12starts/12stops; acoustic separation/mute
confirmation remains pending. The opt-in bounded physical-key helper is staged
and awaits owner interaction. Desktop/PipeWire coexistence remains unqualified.

Headless app-audio progress: read-only host root plus RAM runtime now runs the
opt-in PipeWire/WirePlumber profile in audio/pipewire. Both pw-play and paplay
completed2s silence with native clean stops,14starts/14stops. Desktop key code's
sink guard and5% volume command pass against it. Still qualify audible app
playback, physical keys, and shared-controller desktop/touch/Wi-Fi coexistence.

Autonomous audio follow-up (no reboot): both app APIs passed44.1k mono/48k stereo/
96k stereo silence, app interruption after active phase3, mixed clients, software
mute/volume readbacks and independent audio-service restart. session.sh provides
opt-in RAM-only control with identity/PID guards. A newly found queued-worker
stop race is fixed and regression-tested in source only; current live PCM remains
a8c6a0e. Add immediate-stop timing qualification to the next planned RAM boot,
not this no-reboot session. Audible app output and physical key checks remain.
