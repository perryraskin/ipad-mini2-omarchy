#!/bin/sh
# Run inside j86-build. Keep the verified running kernel tree untouched.
set -eu
: "${J86_TASK_ROOT:?Set J86_TASK_ROOT to the shared workspace path}"
src="$HOME/j86-wifi-kernel"
mkdir -p "$src"
if [ ! -f "$src/Makefile" ]; then
    tar -xzf "$J86_TASK_ROOT/research/linux-dfa4d420.tar.gz" --strip-components=1 -C "$src"
fi
cp "$J86_TASK_ROOT/research/kernel-4k.config" "$src/.config"
cd "$src"
for patchfile in "$J86_TASK_ROOT"/wifi/build/patches/*.patch; do
    if patch --dry-run -p1 < "$patchfile" >/dev/null 2>&1; then
        patch -p1 < "$patchfile"
    else
        patch --dry-run -R -p1 < "$patchfile" >/dev/null
    fi
done
scripts/config --set-str LOCALVERSION '-j86-wifi1' --disable LOCALVERSION_AUTO \
    --enable WIRELESS --enable WLAN --module CFG80211 \
    --enable WLAN_VENDOR_BROADCOM --module BRCMUTIL --module BRCMFMAC \
    --enable BRCMFMAC_USB --disable BRCMFMAC_SDIO --disable BRCMFMAC_PCIE \
    --enable SOUND --module SND --module SND_SOC --set-str INITRAMFS_SOURCE ''
make ARCH=arm64 olddefconfig
make ARCH=arm64 -j4 Image modules
# This first pass intentionally has no initramfs. It is NOT a bootable release:
# stage matching USB/NBD modules and rebuild with the recovered initramfs first.
