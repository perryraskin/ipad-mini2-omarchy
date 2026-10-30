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
cp "$J86_TASK_ROOT/audio/mca/j86-mca.c" "$J86_TASK_ROOT/audio/mca/j86-mca-plan.h" sound/soc/apple/
if ! grep -q '^config SND_SOC_J86_MCA_BENCH$' sound/soc/apple/Kconfig; then
 cat >> sound/soc/apple/Kconfig <<'EOF'

config SND_SOC_J86_MCA_BENCH
 tristate "Experimental muted-bench J86 A7 MCA"
 depends on SND_SOC && COMMON_CLK && DMA_ENGINE
 depends on ARCH_APPLE || COMPILE_TEST
 select SND_SOC_GENERIC_DMAENGINE_PCM
 help
   Build-only exact J86 experiment; driver defaults off and no DT/card is supplied.
EOF
fi
grep -q 'j86-mca.o' sound/soc/apple/Makefile || printf 'obj-$(CONFIG_SND_SOC_J86_MCA_BENCH) += j86-mca.o\n' >> sound/soc/apple/Makefile
scripts/config --set-str LOCALVERSION '-j86-audio2' --disable LOCALVERSION_AUTO \
 --enable WIRELESS --enable WLAN --module CFG80211 --enable WLAN_VENDOR_BROADCOM \
 --module BRCMUTIL --module BRCMFMAC --enable BRCMFMAC_USB --disable BRCMFMAC_SDIO --disable BRCMFMAC_PCIE \
 --enable SOUND --module SND --module SND_SOC --module SND_SOC_J86_MCA_BENCH --enable DMADEVICES --module APPLE_SIO --module APPLE_SIO_DMA \
 --set-str INITRAMFS_SOURCE ''
make ARCH=arm64 olddefconfig
grep -q '^CONFIG_DMA_ENGINE=y' .config
grep -q '^CONFIG_DMA_VIRTUAL_CHANNELS=m' .config
make ARCH=arm64 -j4 Image modules
# Strict object compilation, then full-tree modpost. A selective .ko target
# overwrites Module.symvers with a subset and loses modular ALSA exports.
make ARCH=arm64 KCFLAGS=-Werror drivers/soc/apple/apple-sio-core.o drivers/dma/apple-sio-dma.o drivers/dma/virt-dma.o sound/soc/apple/j86-mca.o
make ARCH=arm64 -j4 modules
grep -q 'devm_snd_soc_register_component' Module.symvers
grep -q 'devm_snd_dmaengine_pcm_register' Module.symvers
cp .config "$out/kernel.config"
cp Module.symvers "$out/Module.symvers"
cp drivers/soc/apple/apple-sio-core.ko drivers/dma/apple-sio-dma.ko drivers/dma/virt-dma.ko sound/soc/apple/j86-mca.ko "$out/"
make -s ARCH=arm64 kernelrelease > "$out/kernel.release"
sha256sum "$out/"*.ko > "$out/SHA256SUMS"
echo 'Build-only audio kernel/modules ready; no initramfs, RAM payload, boot profile or device activation.'
