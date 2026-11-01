# Ordered physical validation checklist

This is the single physical test queue for Perry's return. No action is needed
while he is offline. The Mac has a prepared, inactive audio2 RAM candidate;
source-only release updates are documented in updates/README.md. Do not restore, repartition, flash or install to iPad internal
storage. New Wi-Fi/audio/motion/suspend code is inactive by default. Candidate
builds are experiments, not a daily-use release. Stop a stage on unexpected
output and retain its logs before advancing.

Completed October31: known-good RAM desktop recovered; scale2 taps physically confirmed reliable with stock Labwc. New bottom window bar physically confirmed to restore minimized apps. Long-press compositor tap-frame fix passes handler tests; Perry confirmed reliable quick taps and title-bar hold menu together. Perry also confirmed short Power screen-off, wake, and held Power menu. True SoC suspend remains unqualified. Manual landscape applied; physical touch/resize check is pending after app-launch freezes. Restored portrait after inaccessible viewer controls; increased title buttons to48logical pixels and opened a smaller Terminal for drag/resize qualification. Signed swayimg installation and actual rendering succeeded, but install-load latency and browser responsiveness are not qualified; installer is hidden again.

1. **Reconnect and recover the known-good session.** Reconnect the qualified
   USB-A-to-Lightning cable through the Mac adapter. Inspect USB, network/serial,
   running kernel and current screen before changing anything. The last180/270°
   rotation test lost USB before acknowledgment; its cleanup is unknown. Restore
   portrait with `j86-rotate portrait` once reachable. If reboot is necessary,
   use DFU and the known-good RAM boot. Verify Mac Local Network permission and
   a real connection before repeating boot attempts.
2. **Confirm touch and session controls.** At scale2, tap Terminal and all four
   corners. Check short tap, scrolling, dragging and second finger. Hold still
   about0.6s in Firefox and on a window: a context menu should open without a
   preceding left-click. Resize using the enlarged outside edge/corner zones.
   Test Home menu, short Power screen-off/wake and held Power menu; ensure touch
   restarts. This is screen-off only. Check brightness slider and default volume
   keys still change brightness. Select audio key mode and verify a missing sink
   changes neither brightness nor volume; restore brightness key mode afterward.
3. **Finish manual rotation qualification.** Check portrait,90°,180°,270°, then
   portrait again. Verify touch alignment in each, window interaction, and restore
   after desktop restart. Log any output-transform failure before another attempt.
4. **Recheck Mac-backed apps and browser.** Verify root is read-only and the app
   store is the separate writable Mac image. Start relay, perform a signed package
   operation with the prepared write path, open the app and browse HTTPS in Firefox.
   Check app persistence across a clean detach/remount. Confirm installs stay hidden after ordinary startup; explicitly enable only after write-path qualification. Test a closed installer terminal, verify transaction completion, and ensure failed/uncertain transactions hide installs and refuse restart until reviewed. Never bypass signature
   checks or write through the read-only root path.
5. **RAM-boot the inactive candidate.** Prefer the latest prepared audio-candidate (7.0.12-j86-audio2) after verifying profile/module hashes and
   matching vermagic first. It adds disabled driver drafts and the explicit Wi-Fi firmware gate; it is not boot-qualified. The older Wi-Fi candidate remains available. Keep Wi-Fi host enable off initially. Recheck touch,
   backlight and USB before wireless experiments. The installer must remain hidden because app storage has not been qualified on audio2. If any regress, return to the
   known-good RAM profile; no internal restore.
6. **Qualify native Wi-Fi in stages.** With RF disabled, verify corrected HSIC
   enumeration0a5c:bd1c, chip4324 rev6 and private vendor-u calibration/NVRAM.
   Run bounded firmware version/revinfo/MAC checks on the calibrated blob before
   RF. The new private driver stage is only a host artifact; do not treat it as
   an approved scan/association image. The updated brcmfmac module also requires explicit j86_allow_firmware opt-in; verify its default-off gate before enabling. Then qualify brcmfmac firmware acceptance,
   regulatory state and scan before using Perry's chosen network credentials.
   Test association, DHCP, DNS, HTTPS, signed package download, clean disable and
   touch/USB recovery. Keep credentials and identifying logs private.
7. **Audio: do not start with speakers.** Requires reviewed exact A7 clock/route,
   IRQ/stop, SIO and amp drivers; the register-plan backend is not a playback
   driver. First boot the separate audio2 experiment with SIO off, inventory and
   verify power restoration. Qualify explicit SIO boot and muted cyclic DMA,
   clocks and FIFO behavior before releasing amp mute/reset. Use both exact private
   speaker records; no A5/A9 defaults. Only then try a quiet bounded tone, mixer,
   mute, explicit volume-key mode, and switch back to brightness. Stop on heat,
   distortion, missing clock or DMA errors.
8. **Auto-rotation: qualify the sensor before enabling policy.** Requires qualified UART4 baud/power state, explicit receive-only Oscar attach, sensor subscription/report decoder and calibrated IIO acceleration. Verify sensor identity,
   SI units and signed panel-axis mapping in stationary poses. Run policy dry-run,
   check flat/diagonal/shaking rejection and stale-stream behavior. Explicitly apply
   only after mapping is confirmed; check touch and window alignment in every pose.
   Manual Rotate screen remains the fallback.
9. **Suspend: isolated recovery experiment only.** Requires a prepared self-contained
   RAM root with all NBD mounts detached and app writes flushed. Do not suspend the
   current Mac-backed root. Inspect candidate state/mem_sleep and wake IRQ handling;
   test freezer/device stages before a real sleep attempt. Qualify Home/Power wake,
   serial/USB, timekeeping, display, touch, wireless/audio and measured power use.
   Do not expose suspend in the menu until repeated resume works. Deep A7 suspend
   needs platform resume support beyond the experimental kernel config.
10. **HDMI last.** With touch stable, start a bounded adapter observation, swap Mac
    Lightning for the Apple HDMI adapter and ready monitor, then reconnect the Mac
    cable without button presses. Record monitor output/detection. The LG5K is a
    suitable HDMI sink; the adapter determines output resolution. Video output is
    unimplemented/unverified and must not be promised from detection alone.

Record dated results and exact profile/commit next to each step when run. Do not
mark a stage passed based solely on host models, synthetic events or compilation.


After a source update, explicitly restart/deploy the reviewed services only during
this live session. Confirm the new package gate and volume mode after deployment;
source apply alone does not reload the iPad or switch its RAM boot. The updater
must never be used as an iPad filesystem/package updater.


Recovery checkpoint, 2026-10-31: known-good RAM boot restored; live native touch
reports state2, the Omarchy shell has a ready receipt, root NBD2 is read-only,
and the app service is ready with installs hidden. Mac root serving holds an
idle-sleep assertion while connected. Physical tap/button confirmation remains
pending. Both loader USB handoffs may need separate cable reconnects; the Pongo
logo can lag its upload, so do not infer iOS boot from the Apple logo alone.

October31 touch recovery: physical drags produced no evdev contacts after a
firmware restart associated with screen wake. Another deliberate restart
restored continuous motion and Perry confirmed the drag worked. Screen blanking
now gates exact-device Labwc sendEventsMode while retaining touch scanning.
The configuration helper preserves touch calibration and other devices in
tests. Physical off/wake/drag retest of this change remains pending; this is
not platform suspend or reduced touch-controller power.
