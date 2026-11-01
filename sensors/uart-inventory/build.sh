#!/bin/bash
# Host build only; never loads the module or connects to the iPad.
set -euo pipefail
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
limactl shell j86-build env "J86_TASK_ROOT=$root" bash -c '
set -euo pipefail
kernel="$HOME/j86-audio-kernel"
work="$HOME/j86-modules/uart-inventory"
out="$J86_TASK_ROOT/sensors/build/uart-inventory"
mkdir -p "$work" "$out"
cp "$J86_TASK_ROOT/sensors/uart-inventory/j86_oscar_uart_inventory.c" "$J86_TASK_ROOT/sensors/uart-inventory/Makefile" "$work/"
test -s "$kernel/Module.symvers"
make -C "$kernel" ARCH=arm64 M="$work" KCFLAGS=-Werror modules > "$out/build.log" 2>&1
cp "$work/j86_oscar_uart_inventory.ko" "$out/"
sha256sum "$out/j86_oscar_uart_inventory.ko" > "$out/SHA256SUMS"
'
