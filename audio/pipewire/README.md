# Isolated native app-audio checkpoint

These configurations are opt-in test artifacts, not desktop autostart defaults.
The J86 native PCM and its retained SIO owners must already be healthy. Do not
start touch/Wi-Fi or reload/unload firmware to use this checkpoint.

Live on kernel7.0.12-j86-audio2 with PCM source a8c6a0e:

- PipeWire1.6.10 created the real `j86-speakers` ALSA sink, fixed48k stereo S16,
  1024-frame periods and four periods per buffer.
- WirePlumber's `j86-audio` profile supplied routing policy with hardware audio,
  Bluetooth and camera discovery disabled. It uses the explicitly created sink.
- `pw-play` completed a2s silent WAV with exit0 and a matching clean driver stop.
- `pipewire-pulse` exposed `j86-speakers` as the default PulseAudio sink; `paplay`
  completed the same file with exit0 and another clean driver stop. Combined
  session counters were14starts/14stops, result0.
- The existing home-menu native-sink guard accepted `wpctl inspect` output.
  Its5% volume-up command changed the sink from0.50 to0.55; it was restored to1.0.

These are real userspace-to-native-device transfer tests, but the WAV was silence
and the hardware playback switch remained muted. They do not claim audible app
output, physical volume keys, browser playback, thermal endurance, or coexistence
with the desktop/touch/Wi-Fi. Those checks remain in HANDS-ON-QUEUE.md.

The test mounted the existing host image via read-only NBD and ext4 `ro,noload`.
`/run` and `/tmp` inside that chroot are tmpfs; `/dev`, `/proc`, `/sys` are bind
mounts. No iPad internal storage is mounted. The test account is UID/GID1000,
with access to the native sound-device nodes. Runtime HOME is `/run/j86-audio/home`
and XDG_RUNTIME_DIR is `/run/user/1000`, mode0700, owned by that account.

Place pipewire.conf and alsa.conf under `/run/j86-audio`; place the WirePlumber
profile in `$HOME/.config/wireplumber/wireplumber.conf.d/99-j86.conf`. Run as1000:

```
ALSA_CONFIG_PATH=/run/j86-audio/alsa.conf pipewire -c /run/j86-audio/pipewire.conf
ALSA_CONFIG_PATH=/run/j86-audio/alsa.conf wireplumber --profile j86-audio
pipewire-pulse
```

Use separate processes with captured PIDs/logs. Do not run a second daemon against
an existing runtime socket. Missing D-Bus/realtime privilege warnings were present
in the isolated test; no realtime or desktop scheduling qualification is claimed.

`../pcm-native/mixer-control.c` builds with `cc -Wall -Wextra -Werror -O2 ...
-lasound`. It checks card ID J86Native and readbacks. Commands: `status`, `mute`,
`enable N` where N=0..60 corresponds to-60..0dB. Enabling is explicit, and does not
start PCM playback. Use bounded low-amplitude files and mute after testing. Its
status path is live-tested; audible app enable/mute qualification is pending.
