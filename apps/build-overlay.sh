#!/bin/bash
# Build/copy only the exact audio2 OverlayFS sidecar; never loads it.
set -euo pipefail
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
limactl shell j86-build env "J86_TASK_ROOT=$root" bash -c '
set -euo pipefail
kernel="$HOME/j86-audio-kernel"
test "$(make -s -C "$kernel" ARCH=arm64 kernelrelease)" = 7.0.12-j86-audio2
grep -q "^CONFIG_OVERLAY_FS=m" "$kernel/.config"
make -C "$kernel" ARCH=arm64 -j2 modules >/tmp/j86-overlay-build.log 2>&1
mkdir -p "$J86_TASK_ROOT/apps/kernel"
cp "$kernel/fs/overlayfs/overlay.ko" "$J86_TASK_ROOT/apps/kernel/j86_overlay_audio2.ko"
sha256sum "$J86_TASK_ROOT/apps/kernel/j86_overlay_audio2.ko"
modinfo -F vermagic "$kernel/fs/overlayfs/overlay.ko"
'
