#!/bin/bash
set -euo pipefail
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
limactl shell j86-build env "J86_TASK_ROOT=$root" bash -c '
set -euo pipefail
kernel="$HOME/j86-audio-kernel"
work="$HOME/j86-modules/pcm-native"
out="$J86_TASK_ROOT/audio/pcm-native/build"
mkdir -p "$work" "$out" "$HOME/j86-modules/sio/transport" "$HOME/j86-modules/sio/session"
rm -f "$out/j86_pcm_native.ko"
cp "$J86_TASK_ROOT/audio/pcm-native/"*.c "$J86_TASK_ROOT/audio/pcm-native/"*.h "$J86_TASK_ROOT/audio/pcm-native/Makefile" "$work/"
for part in transport session; do cp "$J86_TASK_ROOT/audio/sio/$part/"*.h "$HOME/j86-modules/sio/$part/"; done
for part in nco switch mca; do mkdir -p "$HOME/j86-modules/$part"; cp "$J86_TASK_ROOT/audio/$part/"*-plan.h "$HOME/j86-modules/$part/"; done
make -C "$kernel" ARCH=arm64 M="$work" KCFLAGS=-Werror modules > "$out/build.log" 2>&1
cp "$work/j86_pcm_native.ko" "$work/Module.symvers" "$out/"
sha256sum "$out/j86_pcm_native.ko" > "$out/SHA256SUMS"
'
