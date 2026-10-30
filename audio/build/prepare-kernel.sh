#!/bin/bash
# Build-only audio-capable kernel. No initramfs, payload activation or device I/O.
set -euo pipefail
: "${J86_TASK_ROOT:?Set J86_TASK_ROOT to the shared workspace path}"
src="$HOME/j86-audio-kernel"
out="$J86_TASK_ROOT/audio/build/candidate"
mkdir -p "$src" "$out"
if [ ! -f "$src/Makefile" ]; then
 tar -xzf "$J86_TASK_ROOT/research/linux-dfa4d420.tar.gz" --strip-components=1 -C "$src"
fi
cp "$J86_TASK_ROOT/research/kernel-4k.config" "$src/.config"
cd "$src"
for patchfile in "$J86_TASK_ROOT"/wifi/build/patches/*.patch; do
 if patch --dry-run -p1 < "$patchfile" >/dev/null 2>&1; then patch -p1 < "$patchfile"; else patch --dry-run -R -p1 < "$patchfile" >/dev/null; fi
done
source="$J86_TASK_ROOT/audio/sio/source"
test -s "$source/drivers/soc/apple/apple-sio-core.c"
cp "$source/drivers/soc/apple/apple-sio-core.c" drivers/soc/apple/
cp "$source/drivers/dma/apple-sio-dma.c" drivers/dma/
mkdir -p include/linux/soc/apple
cp "$source/include/linux/soc/apple/sio.h" include/linux/soc/apple/
if ! grep -q '^config APPLE_SIO$' drivers/soc/apple/Kconfig; then
 cat >> drivers/soc/apple/Kconfig <<'EOF'

config APPLE_SIO
 tristate "Experimental pinned Apple SmartIO core"
 depends on ARM64 && PM
 depends on ARCH_APPLE || COMPILE_TEST
EOF
fi
if ! grep -q '^config APPLE_SIO_DMA$' drivers/dma/Kconfig; then
 cat >> drivers/dma/Kconfig <<'EOF'

config APPLE_SIO_DMA
 tristate "Experimental pinned Apple SmartIO DMA"
 depends on APPLE_SIO
 select DMA_ENGINE
 select DMA_VIRTUAL_CHANNELS
EOF
fi
grep -q 'apple-sio-core.o' drivers/soc/apple/Makefile || printf 'obj-$(CONFIG_APPLE_SIO) += apple-sio-core.o\n' >> drivers/soc/apple/Makefile
grep -q 'apple-sio-dma.o' drivers/dma/Makefile || printf 'obj-$(CONFIG_APPLE_SIO_DMA) += apple-sio-dma.o\n' >> drivers/dma/Makefile
scripts/config --set-str LOCALVERSION '-j86-audio1' --disable LOCALVERSION_AUTO \
 --enable WIRELESS --enable WLAN --module CFG80211 --enable WLAN_VENDOR_BROADCOM \
 --module BRCMUTIL --module BRCMFMAC --enable BRCMFMAC_USB --disable BRCMFMAC_SDIO --disable BRCMFMAC_PCIE \
 --enable SOUND --module SND --module SND_SOC --enable DMADEVICES --module APPLE_SIO --module APPLE_SIO_DMA \
 --set-str INITRAMFS_SOURCE ''
make ARCH=arm64 olddefconfig
grep -q '^CONFIG_DMA_ENGINE=y' .config
grep -q '^CONFIG_DMA_VIRTUAL_CHANNELS=m' .config
make ARCH=arm64 -j4 Image modules
# Recompile our transport modules with warnings treated as errors.
make ARCH=arm64 KCFLAGS=-Werror drivers/soc/apple/apple-sio-core.ko drivers/dma/apple-sio-dma.ko drivers/dma/virt-dma.ko
cp .config "$out/kernel.config"
cp Module.symvers "$out/Module.symvers"
cp drivers/soc/apple/apple-sio-core.ko drivers/dma/apple-sio-dma.ko drivers/dma/virt-dma.ko "$out/"
make -s ARCH=arm64 kernelrelease > "$out/kernel.release"
sha256sum "$out/"*.ko > "$out/SHA256SUMS"
echo 'Build-only audio kernel/modules ready; no initramfs, RAM payload, boot profile or device activation.'
