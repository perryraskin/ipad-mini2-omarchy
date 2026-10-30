#!/bin/bash
# Build on the existing ARM64 Linux VM against the read-only verified root.
set -euo pipefail
TASK_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
limactl shell j86-build env "J86_TASK_ROOT=$TASK_ROOT" bash -c '
set -euo pipefail
src="$HOME/j86-labwc-repro"
revision=97f28877a343e062f3178d201f0248cd9c2610cf
if [ ! -d "$src/.git" ]; then
 git clone https://github.com/labwc/labwc.git "$src"
 git -C "$src" checkout --detach "$revision"
fi
test "$(git -C "$src" rev-parse HEAD)" = "$revision"
cd "$src"
patchfile="$J86_TASK_ROOT/desktop/patches/labwc-0.20.2-touch-long-press.patch"
if git apply --check "$patchfile"; then git apply "$patchfile"; else git apply --reverse --check "$patchfile"; fi
mountpoint -q /mnt/j86-sysroot || { echo "Mount the verified root image read-only as /mnt/j86-sysroot first"; exit 1; }
findmnt -n -o OPTIONS /mnt/j86-sysroot | grep -Eq "(^|,)ro(,|$)"
if [ ! -f build-j86/build.ninja ]; then
 meson setup build-j86 --cross-file "$J86_TASK_ROOT/desktop/build/j86-sysroot.ini" --buildtype release -Dman-pages=disabled -Dnls=disabled -Dxwayland=disabled -Dsystemd-session=disabled
fi
ninja -C build-j86 -j4
export PKG_CONFIG_SYSROOT_DIR=/mnt/j86-sysroot
export PKG_CONFIG_LIBDIR=/mnt/j86-sysroot/usr/lib/pkgconfig:/mnt/j86-sysroot/usr/share/pkgconfig
gcc --sysroot=/mnt/j86-sysroot -B/mnt/j86-sysroot/usr/lib/ -DWLR_USE_UNSTABLE -g \
 -I"$src" -I"$src/include" -I"$src/build-j86/include" \
 $(pkg-config --cflags wlroots-0.20 wayland-server libxml-2.0 cairo pangocairo glib-2.0) \
 "$J86_TASK_ROOT/desktop/tests/touch-long-press.c" -o "$HOME/j86-touch-test-repro" \
 -Wl,-rpath-link,/mnt/j86-sysroot/usr/lib \
 $(pkg-config --libs wlroots-0.20 wayland-server libxml-2.0 cairo pangocairo glib-2.0)
/mnt/j86-sysroot/usr/lib/ld-linux-aarch64.so.1 --library-path /mnt/j86-sysroot/usr/lib "$HOME/j86-touch-test-repro"
cp build-j86/labwc "$J86_TASK_ROOT/desktop/build/labwc-rebuilt"
echo "Built desktop/build/labwc-rebuilt. Existing active binary was not replaced."
'
