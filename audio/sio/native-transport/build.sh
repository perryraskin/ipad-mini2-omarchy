#!/bin/bash
set -euo pipefail
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
limactl shell j86-build env "J86_TASK_ROOT=$root" bash -c '
set -euo pipefail
kernel="$HOME/j86-audio-kernel"
work="$HOME/j86-modules/sio-native-transport"
out="$J86_TASK_ROOT/audio/sio/build/native-transport"
mkdir -p "$work" "$out" "$HOME/j86-modules/session" "$HOME/j86-modules/transport"
rm -f "$out/j86_audio_session.ko" "$out/SHA256SUMS"
cp "$J86_TASK_ROOT/audio/sio/native-transport/"*.c "$J86_TASK_ROOT/audio/sio/native-transport/"*.h "$J86_TASK_ROOT/audio/sio/native-transport/Makefile" "$work/"
cp "$J86_TASK_ROOT/audio/sio/transport/j86-sio-transport.h" "$HOME/j86-modules/transport/"
cp "$J86_TASK_ROOT/audio/sio/session/j86-sio-session.h" "$HOME/j86-modules/session/"
cp "$J86_TASK_ROOT/audio/sio/build/session/Module.symvers" "$work/session.symvers"
dtc -@ -I dts -O dtb "$J86_TASK_ROOT/audio/amp-identify/i2c2-overlay.dts" -o "$work/overlay.dtbo"
xxd -i -n overlay_blob "$work/overlay.dtbo" > "$work/overlay.h"
sed -i "s/unsigned char overlay_blob\[\]/static const unsigned char overlay_blob[] __aligned(8)/" "$work/overlay.h"
make -C "$kernel" ARCH=arm64 M="$work" KBUILD_EXTRA_SYMBOLS="$work/session.symvers" KCFLAGS=-Werror modules > "$out/build.log" 2>&1
cp "$work/j86_audio_session.ko" "$work/Module.symvers" "$out/"
sha256sum "$out/j86_audio_session.ko" > "$out/SHA256SUMS"
'
