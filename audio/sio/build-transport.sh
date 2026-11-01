#!/bin/bash
# Host compile only. No firmware, DT activation, staging or module loading.
set -euo pipefail
root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
limactl shell j86-build env "J86_TASK_ROOT=$root" bash -c '
set -euo pipefail
kernel="$HOME/j86-audio-kernel"
work="$HOME/j86-modules/sio-audio2-transport"
out="$J86_TASK_ROOT/audio/sio/build/audio2-transport"
test "$(make -s -C "$kernel" ARCH=arm64 kernelrelease)" = 7.0.12-j86-audio2
test -s "$kernel/Module.symvers"
grep -q "^CONFIG_DMA_VIRTUAL_CHANNELS=m" "$kernel/.config"
mkdir -p "$work/include/linux/soc/apple" "$out"
cp "$J86_TASK_ROOT/audio/sio/source/drivers/soc/apple/apple-sio-core.c" "$work/"
cp "$J86_TASK_ROOT/audio/sio/source/drivers/dma/apple-sio-dma.c" "$work/"
cp "$J86_TASK_ROOT/audio/sio/source/include/linux/soc/apple/sio.h" "$work/include/linux/soc/apple/"
cp "$kernel/drivers/dma/virt-dma.h" "$kernel/drivers/dma/dmaengine.h" "$work/"
printf "obj-m += apple-sio-core.o apple-sio-dma.o\nccflags-y += -I\$(src)/include\n" > "$work/Makefile"
make -C "$kernel" ARCH=arm64 M="$work" KCFLAGS=-Werror modules > "$out/build.log" 2>&1
cp "$work/apple-sio-core.ko" "$work/apple-sio-dma.ko" "$out/"
# Dependency is compiled from the exact kernel tree, not substituted from another boot.
make -C "$kernel" ARCH=arm64 drivers/dma/virt-dma.ko >> "$out/build.log" 2>&1
cp "$kernel/drivers/dma/virt-dma.ko" "$out/"
for name in apple-sio-core apple-sio-dma virt-dma; do
 test "$(modinfo -F vermagic "$out/$name.ko" | cut -d" " -f1)" = 7.0.12-j86-audio2
done
sha256sum "$out/"*.ko > "$out/SHA256SUMS"
echo "Built SIO core, DMA and exact virt-dma dependency for audio2; no device activation."
'
