#!/bin/sh
set -eu
R=/mnt/omarchy
S=/tmp/omarchy-support
[ "$(tr -d '\000' </proc/device-tree/model)" = 'Apple iPad mini 2 (Cellular)' ]
grep -q " /mnt/omarchy ext4 ro," /proc/mounts
if [ -f "$R/run/user/1000/omarchy-desktop-ready.json" ]; then
 echo 'Desktop already has a ready receipt; inspect status instead of launching another.'
 exit 0
fi
if [ ! -d /sys/module/evdev ]; then busybox insmod "$S/evdev.ko"; fi
busybox mdev -s
for name in dev proc sys; do
 grep -q " $R/$name " /proc/mounts || mount -o bind /$name "$R/$name"
done
grep -q " $R/dev/pts " /proc/mounts || mount -o bind /dev/pts "$R/dev/pts"
mkdir -p /dev/shm
grep -q ' /dev/shm ' /proc/mounts || mount -t tmpfs -o mode=1777,size=64m tmpfs /dev/shm
grep -q " $R/dev/shm " /proc/mounts || mount -o bind /dev/shm "$R/dev/shm"
[ -e /dev/fd ] || ln -s /proc/self/fd /dev/fd
chmod 666 /dev/null /dev/zero /dev/random /dev/urandom /dev/ptmx /dev/pts/ptmx
for name in run tmp; do
 grep -q " $R/$name " /proc/mounts || mount -t tmpfs -o mode=755,size=96m tmpfs "$R/$name"
 [ "$name" != tmp ] || chmod 1777 "$R/tmp"
done
mkdir -p /ram-home
grep -q ' /ram-home ' /proc/mounts || mount -t tmpfs -o mode=755,size=240m tmpfs /ram-home
if [ ! -d /ram-home/tablet ]; then
 mkdir -p /ram-home/tablet
 # Share immutable wallpaper/theme assets instead of using158MiB of RAM twice.
 busybox tar -c -C "$R/home/tablet" --exclude='./.local/share/omarchy-ipad/themes' . | busybox tar -x -C /ram-home/tablet
 mkdir -p /ram-home/tablet/.local/share/omarchy-ipad/themes
 mount -o bind "$R/home/tablet/.local/share/omarchy-ipad/themes" /ram-home/tablet/.local/share/omarchy-ipad/themes
fi
grep -q " $R/home " /proc/mounts || mount -o bind /ram-home "$R/home"
# Plain bind mounts do not include child mounts. Expose the shared themes in
# the chroot explicitly as well as through the RAM-home path.
if ! grep -q " $R/home/tablet/.local/share/omarchy-ipad/themes " /proc/mounts; then
 mount -o bind /ram-home/tablet/.local/share/omarchy-ipad/themes "$R/home/tablet/.local/share/omarchy-ipad/themes"
fi
mkdir -p "$R/run/user/1000" "$R/run/dbus"
chown 1000:1000 "$R/run/user/1000"; chmod 700 "$R/run/user/1000"
chown 0:983 /dev/dri/card0; chmod 660 /dev/dri/card0
# Exact J86 native backlight: permit only the desktop user's group to write.
B=/sys/class/backlight/20a110000.i2c:pmic@3c:backlight@600
[ "$(cat "$B/max_brightness")" = 2047 ]
chown 0:1000 "$B/brightness"; chmod 664 "$B/brightness"
for p in /dev/input/event*; do chown 0:992 "$p"; chmod 660 "$p"; done
[ -S "$R/run/seatd.sock" ] || busybox chroot "$R" /usr/bin/seatd -g seat >"$R/run/seatd.log" 2>&1 </dev/null &
if [ ! -S "$R/run/dbus/system_bus_socket" ]; then busybox chroot "$R" /usr/bin/dbus-daemon --system --fork --nopidfile; fi
# libinput needs udev input classification and hotplug events.
if ! ps | grep '[s]ystemd-udevd' >/dev/null; then
 busybox chroot "$R" /usr/lib/systemd/systemd-udevd --daemon
fi
busybox chroot "$R" /usr/bin/env SYSTEMD_IN_CHROOT=0 /usr/bin/udevadm trigger --action=add --subsystem-match=input
busybox chroot "$R" /usr/bin/env SYSTEMD_IN_CHROOT=0 /usr/bin/udevadm trigger --action=add --subsystem-match=drm
busybox chroot "$R" /usr/bin/env SYSTEMD_IN_CHROOT=0 /usr/bin/udevadm settle --timeout=10
cp "$S/home-menu.py" "$R/run/home-menu.py"
if [ -d "$S/desktop" ]; then
 cp -a "$S/desktop" "$R/run/j86-desktop"
 busybox chroot "$R" /usr/bin/python /run/j86-desktop/configure-session.py "$(cat "$S/usb-web-host")"
fi
# Bounded compressed RAM swap; no swap writes to iPad or Mac storage.
if [ -e /sys/block/zram0/disksize ] && [ "$(cat /sys/block/zram0/disksize)" = 0 ]; then
 echo 536870912 > /sys/block/zram0/disksize
 echo 201326592 > /sys/block/zram0/mem_limit
 busybox mkswap /dev/zram0
 busybox swapon -p 100 /dev/zram0
fi
# The physical Home key is handled by the J86 key service. Once libinput is
# enabled, remove the stock release binding so one press cannot toggle twice.
busybox chroot "$R" /usr/bin/python - <<'J86_KEYS'
import pathlib,xml.etree.ElementTree as ET
p=pathlib.Path('/home/tablet/.config/labwc/rc.xml')
tree=ET.parse(p)
for parent in tree.iter():
 for child in list(parent):
  if child.tag=='keybind' and child.get('key')=='XF86HomePage':parent.remove(child)
tree.write(p,encoding='unicode')
J86_KEYS
cat >"$R/home/tablet/.config/labwc/autostart" <<'EOF'
#!/bin/bash
export OMARCHY_PATH=/home/tablet/.local/share/omarchy-ipad
# Native panel stays1536x2048; 2x scaling gives touch-friendly768x1024.
wlr-randr --output Unknown-1 --scale 2
# Restore touch calibration and display orientation together before the shell.
if [ -x /home/tablet/.local/bin/j86-rotate ]; then
 /home/tablet/.local/bin/j86-rotate restore || exit 1
fi
qs -p /run/j86-desktop/window-bar.qml >"$XDG_RUNTIME_DIR/j86-window-bar.log" 2>&1 &
qs -p "$OMARCHY_PATH/shell/shell.qml" >"$XDG_RUNTIME_DIR/omarchy-shell.log" 2>&1 &
EOF
J86_COMPOSITOR=/usr/bin/labwc
J86_LONG_PRESS=0
if [ -s "$R/run/j86-desktop/build/active.sha256" ]; then
 expected=$(cat "$R/run/j86-desktop/build/active.sha256")
 actual=$(busybox sha256sum "$R/run/j86-desktop/build/labwc-j86-long-press")
 [ "${actual%% *}" = "$expected" ] || { echo 'Tablet compositor checksum mismatch'; exit 1; }
 J86_COMPOSITOR=/run/j86-desktop/build/labwc-j86-long-press
 J86_LONG_PRESS=600
fi
busybox chroot "$R" /usr/bin/setpriv --reuid=1000 --regid=1000 --init-groups /usr/bin/env HOME=/home/tablet USER=tablet PATH=/usr/local/bin:/usr/bin LANG=C.UTF-8 XDG_RUNTIME_DIR=/run/user/1000 XDG_SESSION_TYPE=wayland XDG_CURRENT_DESKTOP=labwc OMARCHY_PATH=/home/tablet/.local/share/omarchy-ipad WLR_BACKENDS=drm,libinput WLR_RENDERER=pixman WLR_LIBINPUT_NO_DEVICES=1 LIBSEAT_BACKEND=seatd LIBGL_ALWAYS_SOFTWARE=1 QT_QUICK_BACKEND=software QT_QPA_PLATFORM=wayland LABWC_UPDATE_ACTIVATION_ENV=0 J86_COMPOSITOR="$J86_COMPOSITOR" LABWC_TOUCH_LONG_PRESS_MS="$J86_LONG_PRESS" /usr/bin/dbus-run-session /usr/bin/bash -c '/usr/local/libexec/arch-ipad-first-theme; exec "$J86_COMPOSITOR"' >"$R/run/labwc.log" 2>&1 </dev/null &
busybox chroot "$R" /usr/bin/python /run/home-menu.py >"$R/run/home-menu.log" 2>&1 </dev/null &
echo 'Desktop launch requested; check status for the ready receipt.'
