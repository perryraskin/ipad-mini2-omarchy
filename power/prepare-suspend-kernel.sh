#!/bin/bash
# Build a separate suspend preparation output. No payload or device activation.
set -euo pipefail
: "${J86_TASK_ROOT:?Set the shared workspace path}"
src="$HOME/j86-audio-kernel"
build="$HOME/j86-suspend-build"
out="$J86_TASK_ROOT/power/build"
test -s "$src/Module.symvers"
mkdir -p "$build" "$out"
# The audio build is a configured in-tree source. A separate O= build requires
# a pristine copy; use a private work copy, never clean the qualified audio tree.
copy="$HOME/j86-suspend-source"
mkdir -p "$copy"
rsync -a --exclude='.git' --exclude='*.o' --exclude='*.ko' --exclude='*.a' \
 --exclude='*.cmd' --exclude='/vmlinux*' --exclude='System.map' \
 --exclude='Module.symvers' --exclude='modules.order' --exclude='include/generated' \
 --exclude='arch/arm64/include/generated' --exclude='arch/arm64/boot/Image*' "$src/" "$copy/"
make -C "$copy" ARCH=arm64 mrproper
cp "$src/.config" "$build/.config"
"$copy/scripts/config" --file "$build/.config" --set-str LOCALVERSION '-j86-suspend1' \
 --enable SUSPEND --disable HIBERNATION --disable PM_AUTOSLEEP --disable PM_WAKELOCKS \
 --enable PM_DEBUG --enable PM_SLEEP_DEBUG --enable PM_TEST_SUSPEND
make -C "$copy" O="$build" ARCH=arm64 olddefconfig
make -C "$copy" O="$build" ARCH=arm64 -j4 Image modules
cp "$build/.config" "$out/kernel.config"
make -s -C "$copy" O="$build" ARCH=arm64 kernelrelease > "$out/kernel.release"
cp "$build/Module.symvers" "$out/"
sha256sum "$build/arch/arm64/boot/Image" > "$out/Image.sha256"
echo 'Build only. No resume vector, wake IRQ, DT, boot profile or suspend service enabled.'
