#!/bin/bash
set -euo pipefail
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
limactl shell j86-build env "J86_TASK_ROOT=$root" bash -c '
set -euo pipefail
kernel="$HOME/j86-audio-kernel"
work="$HOME/j86-modules/amp-identify"
out="$J86_TASK_ROOT/audio/amp-identify/build"
mkdir -p "$work" "$out"
cp "$J86_TASK_ROOT/audio/amp-identify/j86_amp_identify.c" "$work/"
dtc -@ -I dts -O dtb "$J86_TASK_ROOT/audio/amp-identify/i2c2-overlay.dts" -o "$work/overlay.dtbo"
xxd -i -n overlay_blob "$work/overlay.dtbo" > "$work/overlay.h"
sed -i "s/unsigned char overlay_blob\[\]/static const unsigned char overlay_blob[] __aligned(8)/" "$work/overlay.h"
printf "obj-m += j86_amp_identify.o\n" > "$work/Makefile"
make -C "$kernel" ARCH=arm64 M="$work" KCFLAGS=-Werror modules > "$out/build.log" 2>&1
cp "$work/j86_amp_identify.ko" "$out/"
sha256sum "$out/j86_amp_identify.ko" > "$out/SHA256SUMS"
'
