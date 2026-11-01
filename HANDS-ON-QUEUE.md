# Ordered physical validation checklist

This is the single physical test queue for Perry's return. No action is needed
until a listed physical check is requested. The audio2 RAM candidate is currently running;
source-only release updates are documented in updates/README.md. Do not restore, repartition, flash or install to iPad internal
storage. New Wi-Fi/audio/motion/suspend code is inactive by default. Candidate
builds are experiments, not a daily-use release. Stop a stage on unexpected
output and retain its logs before advancing.

Earlier October31 checks (current results below supersede pending status): known-good RAM desktop recovered; scale2 taps physically confirmed reliable with stock Labwc. New bottom window bar physically confirmed to restore minimized apps. Long-press compositor tap-frame fix passes handler tests; Perry confirmed reliable quick taps and title-bar hold menu together. Perry also confirmed short Power screen-off, wake, and held Power menu. True SoC suspend remains unqualified. Manual landscape applied; physical touch/resize check is pending after app-launch freezes. Restored portrait after inaccessible viewer controls; increased title buttons to48logical pixels and opened a smaller Terminal for drag/resize qualification. Signed swayimg installation and actual rendering succeeded, but install-load latency and browser responsiveness are not qualified; installer is hidden again.

1. **Reconnect and recover the known-good session.** Reconnect the qualified
   USB-A-to-Lightning cable through the Mac adapter. Inspect USB, network/serial,
   running kernel and current screen before changing anything. The last180/270°
   rotation test lost USB before acknowledgment; its cleanup is unknown. Restore
   portrait with `j86-rotate portrait` once reachable. If reboot is necessary,
   use DFU and the known-good RAM boot. This recovery step has been completed for the current audio2 session. Verify Mac Local Network permission and
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
   matching vermagic first. It adds disabled driver drafts and the explicit Wi-Fi firmware gate; its RAM boot and initial touch are now physically confirmed. The older Wi-Fi candidate remains available. Keep Wi-Fi host enable off initially. Recheck touch,
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
9. **Suspend: isolated recovery experiment only.** The separate suspend1 RAM diagnostic payload is now built with matching USB modules, but unbooted and without a controller profile. Requires a self-contained
   RAM root with all NBD mounts detached and app writes flushed. Do not suspend the
   current Mac-backed root. Inspect candidate state/mem_sleep and wake IRQ handling;
   test freezer/device stages before a real sleep attempt. Qualify Home/Power wake,
   serial/USB, timekeeping, display, touch, wireless/audio and measured power use.
   Do not expose suspend in the menu until repeated resume works. Deep A7 suspend
   needs platform resume support beyond the experimental kernel config.
10. **Qualify HDMI external display.** With touch stable, start a bounded adapter observation, swap Mac
    Lightning for the Apple HDMI adapter and ready monitor, then reconnect the Mac
    cable without button presses. Record monitor output/detection. Verify the exact LG 5K model and its accepted inputs before testing; some LG 5K displays do not accept HDMI. Use a compatible HDMI monitor/TV if needed. Video output is
    unimplemented/unverified and must not be promised from detection alone.


11. **Bluetooth and directly connected input peripherals — only after HDMI is qualified.**
    Do not start Bluetooth bring-up before step10 is complete. Prefer native
    iPad Bluetooth for a mouse, trackpad and keyboard. Qualify the controller
    and required firmware/transport, then pair and test each peripheral:
    pointer movement, left/right click, scrolling and supported trackpad
    gestures; keyboard text, modifiers, layout and key repeat. Test reconnect
    after peripheral power-off/on and the qualified screen-off/wake path,
    then combined use with HDMI, Wi-Fi and touch. Record unsupported features
    separately from successful basic input.
    If native BT needs a wired fallback during bring-up, note the exact
    USB/Lightning adapter chain: an Apple Lightning to USB Camera Adapter
    (powered USB3 version if needed), powered hub where required, and a
    USB-compatible mouse/trackpad/keyboard. Test direct wired input separately
    from native Bluetooth. Cable/adapter swaps must preserve a recovery path
    for the Mac-backed RAM session; queue those physical swaps rather than
    unplugging its active root connection without preparation.


## Current results and remaining physical checks (October 31)

- Steps 1–2: audio2 RAM desktop, aligned taps, dragging, long-press context menu,
  minimized-window restore, brightness and screen-off/wake passed Perry's tests.
  Screen-off is not SoC suspend. Multi-touch and repeated stress remain unqualified.
- Step 3: finish the full four-orientation touch/resize cycle; restore portrait.
- Step 4: bounded 16MiB write/fsync/readback, clean detach, offline filesystem
  checks, remount persistence and signed Calculator reinstall passed. Perry
  confirmed Calculator and dragging, then Firefox scrolling after restart with
  smaller caches and reduced animation work. Installs were explicitly enabled
  for this qualified session; ordinary startup still hides the installer.
- Steps 5–6: audio2 boot, native Wi-Fi association/DHCP/DNS/direct HTTPS and
  NetworkManager full connectivity passed. Perry confirmed combined touch use.
  Long-duration stress and clean wireless-disable/recovery remain to qualify.
- Step 7: bounded MCA1 inventory restored power. Route/NCO models and builds are
  host results only; no speaker playback, SIO DMA or amp programming is qualified.
- Step 8: bounded UART4 control inventory restored power (0x200 to 0x200).
  Clock parent, baud, live M7 transport and acceleration reports remain unknown.
- Step 9: suspend diagnostic RAM payload built, not booted. Never suspend NBD root.
- Steps 10–11: HDMI remains pending; Bluetooth work starts only after HDMI.

Follow the numbered order for remaining hands-on checks. Do not repeat completed
DFU or firmware steps solely because an earlier paragraph described them as pending.
Source updates do not reload the running iPad or change its RAM-boot profile.
