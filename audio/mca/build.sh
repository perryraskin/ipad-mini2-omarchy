#!/bin/bash
# Build-only disabled CPU DAI; no card, overlay or module activation.
set -euo pipefail
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
limactl shell j86-build env "J86_TASK_ROOT=$root" bash -c '
set -euo pipefail
kernel="$HOME/j86-audio-kernel"
work="$HOME/j86-modules/mca-bench"
out="$J86_TASK_ROOT/audio/mca/build"
mkdir -p "$work" "$out"
test "$(make -s -C "$kernel" ARCH=arm64 kernelrelease)" = 7.0.12-j86-audio2
grep -q "^CONFIG_SND_SOC_GENERIC_DMAENGINE_PCM=y" "$kernel/.config"
test -s "$kernel/Module.symvers"
cp "$J86_TASK_ROOT/audio/mca/j86-mca.c" "$J86_TASK_ROOT/audio/mca/j86-mca-plan.h" "$J86_TASK_ROOT/audio/mca/Makefile" "$work/"
make -C "$kernel" ARCH=arm64 M="$work" KCFLAGS=-Werror modules > "$out/module.log" 2>&1
cp "$work/j86-mca.ko" "$out/"
sha256sum "$out/j86-mca.ko" > "$out/SHA256SUMS"
'
