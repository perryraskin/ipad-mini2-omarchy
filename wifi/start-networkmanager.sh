#!/bin/sh
# Explicit live experiment: state/profiles stay in RAM; never manage USB root link.
set -eu
[ "$(tr -d '\000' </proc/device-tree/model)" = 'Apple iPad mini 2 (Cellular)' ]
[ "$(uname -r)" = 7.0.12-j86-audio2 ]
grep -q ' /mnt/omarchy ext4 ro,' /proc/mounts
[ -d /sys/class/net/wlan0 ]
[ "$(cat /sys/module/brcmfmac/parameters/j86_allow_firmware)" = Y ]
R=/mnt/omarchy
[ ! -e "$R/run/NetworkManager/NetworkManager.pid" ]
mkdir -p "$R/run/NetworkManager"
for target in var/lib/NetworkManager etc/NetworkManager/system-connections; do
 grep -q " $R/$target " /proc/mounts || mount -t tmpfs -o size=4m,mode=700 tmpfs "$R/$target"
done
cat >"$R/run/NetworkManager/j86.conf" <<'CONF'
[main]
plugins=keyfile
dhcp=internal
dns=none
rc-manager=unmanaged
no-auto-default=*
[keyfile]
unmanaged-devices=interface-name:usb0;interface-name:lo;interface-name:sit0
[device-j86-usb]
match-device=interface-name:usb0
managed=0
[device-j86-wifi]
match-device=interface-name:wlan0
managed=1
wifi.backend=wpa_supplicant
CONF
busybox chroot "$R" /usr/bin/NetworkManager --no-daemon --config=/run/NetworkManager/j86.conf >"$R/run/NetworkManager/j86.log" 2>&1 </dev/null &
echo NETWORK_MANAGER_REQUESTED
