#!/bin/bash
# Host build only; never loads the module or connects to the iPad.
set -euo pipefail
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
limactl shell j86-build env "J86_TASK_ROOT=$root" bash -c '
set -euo pipefail
kernel="$HOME/j86-audio-kernel"
work="$HOME/j86-modules/uart-observe"
out="$J86_TASK_ROOT/sensors/build/uart-observe"
mkdir -p "$work" "$out"
cp "$J86_TASK_ROOT/sensors/uart-observe/j86_oscar_uart_observe.c" "$J86_TASK_ROOT/sensors/uart-observe/Makefile" "$work/"
cp "$J86_TASK_ROOT/sensors/oscar/j86-oscar-rx.h" "$work/"
test -s "$kernel/Module.symvers"
make -C "$kernel" ARCH=arm64 M="$work" KCFLAGS=-Werror modules > "$out/build.log" 2>&1
cp "$work/j86_oscar_uart_observe.ko" "$out/"
sha256sum "$out/j86_oscar_uart_observe.ko" > "$out/SHA256SUMS"
'
