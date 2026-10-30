set -eu
R=/mnt/omarchy
if ! ps | grep '[b]in/wayvnc -R' >/dev/null; then
 mkdir -p "$R/tmp/vnc/root"
 if [ ! -f "$R/tmp/vnc/wayvnc-0.10.2-1-aarch64.pkg.tar.xz" ]; then cp /tmp/omarchy-support/vnc/* "$R/tmp/vnc/"; fi
 busybox chroot "$R" /usr/bin/gpg --batch --yes --dearmor --output /tmp/vnc/keyring.gpg /usr/share/pacman/keyrings/archlinuxarm.gpg
 for f in "$R"/tmp/vnc/*.pkg.tar.xz; do
  b=${f##*/}
  busybox chroot "$R" /usr/bin/gpgv --keyring /tmp/vnc/keyring.gpg "/tmp/vnc/$b.sig" "/tmp/vnc/$b"
  busybox chroot "$R" /usr/bin/tar -xf "/tmp/vnc/$b" -C /tmp/vnc/root
 done
 IP=$(ip -4 addr show dev usb0 | sed -n 's/.*inet \(169\.254\.[0-9.]*\)\/.*/\1/p' | head -n 1)
 [ -n "$IP" ]
 busybox chroot "$R" /usr/bin/setpriv --reuid=1000 --regid=1000 --init-groups /usr/bin/env HOME=/home/tablet XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0 LD_LIBRARY_PATH=/tmp/vnc/root/usr/lib /tmp/vnc/root/usr/bin/wayvnc -R -f 8 -r -n 'Perry iPad Mini 2 - Omarchy' "$IP" >"$R/run/wayvnc.log" 2>&1 </dev/null &
fi
echo 'USB desktop control ready.'
