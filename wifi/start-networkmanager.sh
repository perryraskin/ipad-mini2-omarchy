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
# The root is read-only: keep libc DNS in RAM and refresh DHCP DNS on changes.
[ -f "$R/etc/resolv.conf" ] && [ ! -L "$R/etc/resolv.conf" ]
if ! grep -q " $R/etc/resolv.conf " /proc/mounts; then
 : >"$R/run/NetworkManager/j86-resolv.conf"
 chmod 644 "$R/run/NetworkManager/j86-resolv.conf"
 mount -o bind "$R/run/NetworkManager/j86-resolv.conf" "$R/etc/resolv.conf"
fi
cat >"$R/run/NetworkManager/j86-dns.sh" <<'DNS'
#!/bin/sh
set -eu
while :; do
 if /usr/bin/nmcli -g IP4.DNS,IP6.DNS device show wlan0 > /run/NetworkManager/j86-dns.next 2>/dev/null; then
  # Accept numeric resolver addresses only; never put network text into commands.
  awk 'length($0) && $0 ~ /^[0-9a-fA-F:.%]+$/ {print "nameserver " $0}' /run/NetworkManager/j86-dns.next > /run/NetworkManager/j86-resolv.next
  if ! cmp -s /run/NetworkManager/j86-resolv.next /run/NetworkManager/j86-resolv.conf; then
   # Preserve the inode used by the bind mount.
   cat /run/NetworkManager/j86-resolv.next > /run/NetworkManager/j86-resolv.conf
  fi
 fi
 sleep 3
done
DNS
busybox chroot "$R" /bin/sh /run/NetworkManager/j86-dns.sh >"$R/run/NetworkManager/j86-dns.log" 2>&1 </dev/null &
# Preserve existing policy files, then add only this RAM-session desktop grant.
mkdir -p "$R/run/j86-polkit-rules"
cp -a "$R/etc/polkit-1/rules.d/." "$R/run/j86-polkit-rules/"
cat >"$R/run/j86-polkit-rules/30-j86-network.rules" <<'POLICY'
// J86 RAM-session desktop only: no PAM/logind session exists in this chroot.
// Profiles/state are RAM-backed; USB root networking remains unmanaged.
polkit.addRule(function(action, subject) {
  var allowed = [
    "org.freedesktop.NetworkManager.network-control",
    "org.freedesktop.NetworkManager.enable-disable-wifi",
    "org.freedesktop.NetworkManager.wifi.scan",
    "org.freedesktop.NetworkManager.settings.modify.own",
    "org.freedesktop.NetworkManager.settings.modify.system"
  ];
  if (subject.user === "tablet" && allowed.indexOf(action.id) !== -1)
    return polkit.Result.YES;
});
POLICY
chmod 644 "$R/run/j86-polkit-rules/30-j86-network.rules"
grep -q " $R/etc/polkit-1/rules.d " /proc/mounts || mount -o bind "$R/run/j86-polkit-rules" "$R/etc/polkit-1/rules.d"
# Refresh the chroot's policy daemon so its directory monitor uses the RAM mount.
for p in /proc/[0-9]*; do
 [ "$(busybox readlink "$p/root" 2>/dev/null)" != "$R" ] ||
  [ "$(cat "$p/comm" 2>/dev/null)" != polkitd ] || kill -TERM "${p##*/}"
done
sleep 1
busybox chroot "$R" /usr/lib/polkit-1/polkitd --no-debug >"$R/run/j86-polkit.log" 2>&1 </dev/null &
busybox chroot "$R" /usr/bin/NetworkManager --no-daemon --config=/run/NetworkManager/j86.conf >"$R/run/NetworkManager/j86.log" 2>&1 </dev/null &
echo NETWORK_MANAGER_REQUESTED
