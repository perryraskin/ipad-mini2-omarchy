#!/bin/bash
# Run inside j86-build. Build artifacts only; never boot or access an iPad.
set -euo pipefail
: "${J86_TASK_ROOT:?Set the shared workspace path}"
src="$HOME/j86-suspend-source"
build="$HOME/j86-suspend-build"
stage="$HOME/j86-suspend-initramfs"
out="$J86_TASK_ROOT/power/build/candidate"
release=$(make -s -C "$src" O="$build" ARCH=arm64 kernelrelease)
test "$release" = 7.0.12-j86-suspend1
test -s "$build/Module.symvers"
mkdir -p "$stage" "$out"
(cd "$stage"; cpio -idu --quiet --no-absolute-filenames < "$J86_TASK_ROOT/wifi/build/original-initramfs.cpio")
# Replace inherited audio2 modules. Mixing release directories breaks USB recovery.
rm -rf "$stage/lib/modules"
make -C "$src" O="$build" ARCH=arm64 INSTALL_MOD_PATH="$stage" INSTALL_MOD_STRIP=1 modules_install >"$out/modules-install.log" 2>&1
while IFS= read -r -d '' module; do zstd -d --rm "$module"; done < <(find "$stage/lib/modules/$release" -name '*.ko.zst' -print0)
find "$stage/lib/modules/$release" -type l -name build -delete
depmod -b "$stage" "$release"
for name in usb_f_ncm usb_f_fs nbd; do
 module=$(find "$stage/lib/modules/$release" -name "$name.ko" -print -quit)
 test -n "$module"
 [[ "$(modinfo -F vermagic "$module")" = "$release "* ]]
done
mkdir -p "$stage/etc/modprobe.d"
cat >"$stage/etc/modprobe.d/j86-experimental.conf" <<'GATES'
options brcmfmac j86_allow_firmware=0
options apple-sio-core allow_j86_firmware_boot=0
options j86-mca allow_muted_bench=0
options j86-oscar allow_running_attach=0
GATES
# No proprietary firmware, host root mounts or suspend service is added.
(cd "$stage"; find . -print0 | sort -z | cpio --null -o -H newc --owner=0:0 --quiet) >"$HOME/j86-suspend-initramfs.cpio"
"$src/scripts/config" --file "$build/.config" --set-str INITRAMFS_SOURCE "$HOME/j86-suspend-initramfs.cpio"
make -C "$src" O="$build" ARCH=arm64 olddefconfig >"$out/package.log" 2>&1
make -C "$src" O="$build" ARCH=arm64 -j4 Image >>"$out/package.log" 2>&1
cp "$build/arch/arm64/boot/Image" "$out/Image.initramfs"
cp "$build/.config" "$out/kernel.config"
printf '%s\n' "$release" >"$out/kernel.release"
sha256sum "$out/Image.initramfs" "$out/kernel.config" >"$out/SHA256SUMS"
python3 "$J86_TASK_ROOT/wifi/build/make-ramboot.py" --profile suspend-candidate
echo 'Inactive RAM-only PM diagnostic. No controller profile, NBD mount or suspend action enabled.'
