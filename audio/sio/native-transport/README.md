# Fresh isolated A7 transport candidate

This replaces the discovery sequence of a partially failed newer setup followed
by a companion recovery module. It uses the retained `j86_sio_session` ownership
API and exactly eight A7 setup commands: general0x0f/0x10, EP3 0x0d/0x0e,
descriptor0 1/2, descriptor1 0x0b/0x0c. No unsupported0x1a/0x1b is sent. All
firmware-visible allocations remain retained through every failure until RAM reboot.

After all eight ACKs, it enables the exact J86 I2C2 overlay and retains the adapter.
It refuses a previously enabled bus rather than borrowing an unknown owner's bus.
Only successful setup exposes the one-shot `j86_audio_session_claim` handoff to
`audio/pcm-native`. It does not raise amplifier reset, play sound or start a desktop.

The commands and overlay individually worked in the discovery session. **This
consolidated fresh-start sequence is build/host-tested, not live-qualified.**
The running poisoned session must not be reused, and its handoff must not be forced.

## Build and fresh-session qualification order

1. Build `bash audio/sio/session/build.sh`, then
   `bash audio/sio/native-transport/build.sh`, then
   `bash audio/pcm-native/build.sh`. Use the matching prepared audio2 kernel.
2. Recover a fresh isolated RAM boot; verify exact kernel, J86 identity and new boot
   ID. Keep desktop, touch, Wi-Fi and NBD stopped. Inventory shared SPI/UART/MCA
   ownership before releasing any existing driver; do not blindly unbind consoles.
3. Stage exact owner firmware and speaker records only in RAM. The session checks
   the expected SIO firmware size/hash. Native PCM requires a caller-supplied hash
   of the exact 40-byte speaker records. Do not distribute those inputs.
4. Use the single-`finit_module` loader, never retrying BusyBox `insmod`. First run
   `j86_sio_session` with `allow_session=1 preflight_only=1`; its deliberate
   `-ECANCELED` plus `PREFLIGHT_PASS` means all resource checks passed without SIO
   writes and leases were released. Inspect logs; any other result stops the flow.
5. Only after that result, load the session with `allow_session=1 preflight_only=0`.
   Require `ready=Y,result=0`. From this point do not unload or reload firmware.
6. Load `j86_audio_session` with `allow_setup=1`. Require `setup_complete=Y`,
   `acknowledged=8,result=0`. Any failure stops; retain resources and recover via
   a fresh RAM boot. No private bench or partial-recovery modules are needed.
7. Load ALSA dependencies and `j86_pcm_native` with explicit allow and calibration
   hash. Require module result0 and registered card before playback tests.
8. Test muted prepare-close, normal drain, drop, and subsequent normal playback.
   The updated helper reads kernel cleanup status after close and fails on errors.
   Check start/stop counters too. Only after these pass do low-volume listening,
   volume and desktop coexistence qualification. See HANDS-ON-QUEUE.md.

No command here writes iPad internal storage. No startup service is enabled.
A firmware session owns all16 shared peripheral ranges and four IRQs until RAM
reboot; desktop coexistence requires a separately qualified ownership design.
