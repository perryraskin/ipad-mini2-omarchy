#!/bin/bash
# Compile only the experimental core; never enables, stages, loads or boots it.
set -euo pipefail
TASK_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
profile=${1:-candidate}
case "$profile" in known-good|candidate) ;; *) exit 2;; esac
limactl shell j86-build env "J86_TASK_ROOT=$TASK_ROOT" "J86_PROFILE=$profile" bash -c '
set -euo pipefail
kernel="$HOME/j86-wifi-kernel"; release=7.0.12-j86-wifi1
if [ "$J86_PROFILE" = known-good ]; then kernel="$HOME/j86-kernel"; release=7.0.12-gdfa4d4208131-dirty; fi
test "$(make -s -C "$kernel" ARCH=arm64 kernelrelease)" = "$release"
test -s "$kernel/Module.symvers" || { echo "Full matching kernel export table required; refusing an unchecked module" >&2; exit 1; }
source="$J86_TASK_ROOT/audio/sio/source"
work="$HOME/j86-modules/sio-core-$J86_PROFILE"
out="$J86_TASK_ROOT/audio/sio/build/$J86_PROFILE"
mkdir -p "$work/include/linux/soc/apple" "$out"
cp "$source/drivers/soc/apple/apple-sio-core.c" "$work/"
cp "$source/include/linux/soc/apple/sio.h" "$work/include/linux/soc/apple/"
printf "obj-m += apple-sio-core.o\nccflags-y += -I\$(src)/include\n" > "$work/Makefile"
make -C "$kernel" ARCH=arm64 M="$work" KCFLAGS=-Werror modules > "$out/core.log" 2>&1
cp "$work/apple-sio-core.ko" "$out/"
sha256sum "$out/apple-sio-core.ko" > "$out/SHA256SUMS"
echo "Built disabled experimental SIO core for $release. Nothing loaded."
'
