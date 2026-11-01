#!/bin/sh
# Opt-in headless audio only. Requires the already-mounted read-only host root.
set -eu
R=/mnt/omarchy
S=$R/run/j86-audio
SRC=$(CDPATH= cd -- "$(busybox dirname -- "$0")" && pwd)
fail() { echo "$*" >&2; exit 1; }
run() { busybox chroot "$R" /usr/bin/setpriv --reuid=1000 --regid=1000 --init-groups /usr/bin/env HOME=/run/j86-audio/home XDG_RUNTIME_DIR=/run/user/1000 ALSA_CONFIG_PATH=/run/j86-audio/alsa.conf "$@"; }
healthy_idle() {
 [ "$(cat /sys/module/j86_pcm_native/parameters/result)" = 0 ] || fail 'Native driver unhealthy; leave its ownership intact.'
 [ "$(cat /sys/module/j86_pcm_native/parameters/phase)" = 5 ] || fail 'Audio is not idle; finish the current stream first.'
}
check_owner() {
 name=$1; expected=$2
 [ -f "$S/$name.pid" ] || return 0
 p=$(cat "$S/$name.pid")
 case "$p" in ''|*[!0-9]*) fail 'Invalid PID receipt';; esac
 [ -d "/proc/$p" ] || return 0
 [ "$(busybox awk '{print $22}' /proc/$p/stat)" = "$(cat "$S/$name.start-time")" ] || fail 'PID start time mismatch; no signal sent.'
 [ "$(busybox readlink /proc/$p/root)" = "$R" ] || fail 'PID root mismatch; no signal sent.'
 [ "$(busybox readlink /proc/$p/exe)" = "$R/usr/bin/$expected" ] || fail 'PID executable mismatch; no signal sent.'
}
stop_owned() {
 [ "$(cat "$S/boot-id")" = "$(cat /proc/sys/kernel/random/boot_id)" ] || fail 'Boot receipt mismatch.'
 healthy_idle
 check_owner pulse pipewire
 check_owner wireplumber wireplumber
 check_owner pipewire pipewire
 for name in pulse wireplumber pipewire; do
  [ -f "$S/$name.pid" ] || continue
  p=$(cat "$S/$name.pid")
  if [ -d "/proc/$p" ]; then
   kill -TERM "$p"
   n=0
   while [ -d "/proc/$p" ] && [ "$n" -lt 50 ]; do sleep .1; n=$((n+1)); done
   [ ! -d "/proc/$p" ] || fail 'Process did not exit; no force kill or driver unload.'
  fi
  rm "$S/$name.pid" "$S/$name.start-time"
 done
 healthy_idle
 echo 'Headless audio daemons stopped; native modules and firmware retained.'
}
[ "$(busybox tr -d '\000' </proc/device-tree/model)" = 'Apple iPad mini 2 (Cellular)' ] || fail 'Expected J86.'
[ "$(uname -r)" = '7.0.12-j86-audio2' ] || fail 'Expected qualified audio2 kernel.'
# Require host NBD read-only root and RAM runtime. No internal storage setup.
busybox grep -q '^/dev/nbd2 /mnt/omarchy ext4 ro,' /proc/mounts || fail 'Read-only host root is not mounted.'
busybox grep -q '^tmpfs /mnt/omarchy/run tmpfs ' /proc/mounts || fail '/run must be RAM-backed.'
case "${1:-}" in
 status)
  cat /sys/module/j86_pcm_native/parameters/result /sys/module/j86_pcm_native/parameters/starts /sys/module/j86_pcm_native/parameters/stops
  run /usr/bin/wpctl status
  ;;
 stop) stop_owned ;;
 start)
  [ "${2:-}" = --allow-isolated-audio ] || fail 'Default off: start requires --allow-isolated-audio.'
  healthy_idle
  [ ! -d /sys/module/j86_touch ] && [ ! -d /sys/module/j86_wifi_host ] || fail 'Shared-controller coexistence is not qualified.'
  [ ! -f "$R/run/user/1000/omarchy-desktop-ready.json" ] || fail 'Desktop session already present.'
  for name in pulse wireplumber pipewire; do [ ! -f "$S/$name.pid" ] || fail 'Existing PID receipt; inspect or stop that session first.'; done
  [ ! -S "$R/run/user/1000/pipewire-0" ] && [ ! -S "$R/run/user/1000/pulse/native" ] || fail 'Existing audio socket; refusing a second session.'
  mkdir -p "$S/home/.config/wireplumber/wireplumber.conf.d" "$R/run/user/1000"
  chown 0:0 "$S"; chmod 755 "$S"
  cp "$SRC/pipewire.conf" "$SRC/alsa.conf" "$S/"
  cp "$SRC/wireplumber-profile.conf" "$S/home/.config/wireplumber/wireplumber.conf.d/99-j86.conf"
  chown -R 1000:1000 "$S/home" "$R/run/user/1000"
  chmod 700 "$R/run/user/1000"
  chown 0:1000 /dev/snd/controlC0 /dev/snd/pcmC0D0p /dev/snd/timer
  cat /proc/sys/kernel/random/boot_id > "$S/boot-id"
  # run() backgrounds would record the shell PID; exec the entire wrapper instead.
  for name in pipewire wireplumber pulse; do
   case "$name" in
    pipewire) set -- /usr/bin/pipewire -c /run/j86-audio/pipewire.conf;;
    wireplumber) set -- /usr/bin/wireplumber --profile j86-audio;;
    pulse) set -- /usr/bin/pipewire-pulse;;
   esac
   busybox chroot "$R" /usr/bin/setpriv --reuid=1000 --regid=1000 --init-groups /usr/bin/env HOME=/run/j86-audio/home XDG_RUNTIME_DIR=/run/user/1000 ALSA_CONFIG_PATH=/run/j86-audio/alsa.conf "$@" </dev/null >"$S/$name.log" 2>&1 &
   echo $! > "$S/$name.pid"
   busybox awk '{print $22}' /proc/$(cat "$S/$name.pid")/stat > "$S/$name.start-time"
   sleep 1
   kill -0 "$(cat "$S/$name.pid")" || fail "Failed $name; inspect logs and use stop after verifying driver idle."
  done
  run /usr/bin/wpctl inspect @DEFAULT_AUDIO_SINK@
  echo 'Headless audio ready; hardware mute unchanged. No autostart installed.'
  ;;
 *) fail 'Usage: session.sh status|stop|start --allow-isolated-audio';;
esac
