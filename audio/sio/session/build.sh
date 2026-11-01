#!/bin/bash
# Host build only; never loads the module or connects to the iPad.
set -euo pipefail
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
limactl shell j86-build env "J86_TASK_ROOT=$root" bash -c '
set -euo pipefail
kernel="$HOME/j86-audio-kernel"
work="$HOME/j86-modules/sio-session"
out="$J86_TASK_ROOT/audio/sio/build/session"
mkdir -p "$work" "$out"
rm -f "$out/j86_sio_session.ko" "$out/SHA256SUMS"
cp "$J86_TASK_ROOT/audio/sio/session/j86_sio_session.c" "$J86_TASK_ROOT/audio/sio/session/Makefile" "$J86_TASK_ROOT/audio/sio/session/j86-sio-session.h" "$work/"
test -s "$kernel/Module.symvers"
make -C "$kernel" ARCH=arm64 M="$work" KCFLAGS=-Werror modules > "$out/build.log" 2>&1
cp "$work/j86_sio_session.ko" "$work/Module.symvers" "$out/"
sha256sum "$out/j86_sio_session.ko" > "$out/SHA256SUMS"
'
