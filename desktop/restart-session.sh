#!/bin/sh
# Run inside the Omarchy RAM chroot only; no disk/boot operations.
set -eu
compositor=${1:-/usr/bin/labwc}
case "$compositor" in /usr/bin/labwc|/run/j86-desktop/build/labwc-j86-long-press) ;; *) exit 2;; esac
[ -x "$compositor" ]
exec /usr/bin/setpriv --reuid=1000 --regid=1000 --init-groups /usr/bin/env HOME=/home/tablet USER=tablet PATH=/home/tablet/.local/bin:/usr/local/bin:/usr/bin LANG=C.UTF-8 XDG_RUNTIME_DIR=/run/user/1000 XDG_SESSION_TYPE=wayland XDG_CURRENT_DESKTOP=labwc OMARCHY_PATH=/home/tablet/.local/share/omarchy-ipad WLR_BACKENDS=drm,libinput WLR_RENDERER=pixman WLR_LIBINPUT_NO_DEVICES=1 LIBSEAT_BACKEND=seatd LIBGL_ALWAYS_SOFTWARE=1 QT_QUICK_BACKEND=software QT_QPA_PLATFORM=wayland LABWC_UPDATE_ACTIVATION_ENV=0 LABWC_TOUCH_LONG_PRESS_MS=600 /usr/bin/dbus-run-session "$compositor"
