#!/bin/bash
# Compile only: no staging, module loading, UART opening or device interaction.
set -euo pipefail
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
limactl shell j86-build env "J86_TASK_ROOT=$root" bash -c '
set -euo pipefail
kernel="$HOME/j86-audio-kernel"
work="$HOME/j86-modules/oscar-rx"
out="$J86_TASK_ROOT/sensors/build"
mkdir -p "$work" "$out"
cp "$J86_TASK_ROOT/sensors/oscar/j86-oscar.c" "$J86_TASK_ROOT/sensors/oscar/j86-oscar-rx.h" "$J86_TASK_ROOT/sensors/oscar/Makefile" "$work/"
test -s "$kernel/Module.symvers"
make -C "$kernel" ARCH=arm64 M="$work" KCFLAGS=-Werror modules > "$out/transport.log" 2>&1
cp "$work/j86-oscar.ko" "$out/"
sha256sum "$out/j86-oscar.ko" > "$out/SHA256SUMS"
'
