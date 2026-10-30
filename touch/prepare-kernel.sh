#!/bin/sh
set -eu
TASK=${J86_TASK_ROOT:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}
KDIR="$HOME/j86-kernel"
mkdir -p "$KDIR"
if [ ! -f "$KDIR/Makefile" ]; then
 tar -xzf "$TASK/research/linux-dfa4d420.tar.gz" -C "$KDIR" --strip-components=1
fi
cp "$TASK/research/kernel-4k.config" "$KDIR/.config"
cd "$KDIR"
scripts/config --set-str LOCALVERSION '-gdfa4d4208131-dirty' --disable LOCALVERSION_AUTO --set-str INITRAMFS_SOURCE ''
make ARCH=arm64 olddefconfig > "$TASK/touch/kernel-prepare.log" 2>&1
make ARCH=arm64 -j4 modules_prepare >> "$TASK/touch/kernel-prepare.log" 2>&1
make ARCH=arm64 kernelrelease
cp .config "$TASK/touch/build-config"
