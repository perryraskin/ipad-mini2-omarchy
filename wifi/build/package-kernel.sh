#!/bin/bash
# Run inside j86-build after the first pass. Produces candidate assets only.
set -euo pipefail
: "${J86_TASK_ROOT:?Set J86_TASK_ROOT to the shared workspace path}"
src="$HOME/j86-wifi-kernel"
stage="$HOME/j86-wifi-initramfs"
out="$J86_TASK_ROOT/wifi/build/candidate"
cd "$src"
release=$(make -s ARCH=arm64 kernelrelease)
test "$release" = 7.0.12-j86-wifi1
test -s Module.symvers
test -s arch/arm64/boot/Image
mkdir -p "$stage" "$out"
(
    cd "$stage"
    cpio -idu --quiet < "$J86_TASK_ROOT/wifi/build/original-initramfs.cpio"
)
# Only this isolated staging tree is changed; never the live device/module tree.
rm -rf "$stage/lib/modules"
make ARCH=arm64 INSTALL_MOD_PATH="$stage" INSTALL_MOD_STRIP=1 modules_install
depmod -b "$stage" "$release"
evdev=$(find "$stage/lib/modules/$release" -name evdev.ko -print -quit)
test -n "$evdev"
cp "$evdev" "$out/evdev.ko"
for name in usb_f_ncm usb_f_fs nbd cfg80211 brcmfmac snd-soc-core; do
    find "$stage/lib/modules/$release" -name "$name.ko*" -print -quit | grep -q .
done
find "$stage/lib/modules/$release" -type l -name build -delete
(
    cd "$stage"
    find . -print0 | sort -z | cpio --null -o -H newc --owner=0:0 --quiet
) > "$HOME/j86-wifi-initramfs.cpio"
scripts/config --set-str INITRAMFS_SOURCE "$HOME/j86-wifi-initramfs.cpio"
make ARCH=arm64 olddefconfig
make ARCH=arm64 -j4 Image
cp arch/arm64/boot/Image "$out/Image.initramfs"
cp .config "$out/kernel.config"
cp Module.symvers "$out/Module.symvers"
printf '%s\n' "$release" > "$out/kernel.release"
mod="$HOME/j86-modules/native-wifi1"
mkdir -p "$mod"
cp "$J86_TASK_ROOT/touch/native/Makefile" "$mod/"
python3 - "$J86_TASK_ROOT/touch/native/j86_touch.c" "$mod/j86_touch.c" <<'PY'
import pathlib,sys
s=pathlib.Path(sys.argv[1]).read_text()
old='7.0.12-gdfa4d4208131-dirty'
assert s.count(old)==2, 'Unexpected touch kernel guard; inspect before adapting'
pathlib.Path(sys.argv[2]).write_text(s.replace(old,'7.0.12-j86-wifi1'))
PY
make ARCH=arm64 M="$mod" KCFLAGS=-Werror modules
cp "$mod/j86_touch.ko" "$out/j86_touch.ko"
hsic="$HOME/j86-modules/hsic-range-candidate"
mkdir -p "$hsic"
cp "$J86_TASK_ROOT/wifi/hsic/j86_hsic_range.c" "$J86_TASK_ROOT/wifi/hsic/Makefile" "$hsic/"
make ARCH=arm64 M="$hsic" KCFLAGS=-Werror modules
cp "$hsic/j86_hsic_range.ko" "$out/"
sha256sum "$out/j86_hsic_range.ko" "$out/Image.initramfs" "$out/kernel.config" "$out/j86_touch.ko" > "$out/SHA256SUMS"
printf 'Candidate only: boot compatibility and HSIC bring-up still required.\n'
