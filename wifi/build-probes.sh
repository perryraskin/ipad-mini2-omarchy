#!/bin/bash
# Build only; never loads modules, boots, or stages proprietary firmware.
set -euo pipefail
TASK_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
profile=${1:-known-good}
case "$profile" in known-good|candidate|audio-candidate) ;; *) echo 'usage: wifi/build-probes.sh [known-good|candidate|audio-candidate]' >&2; exit 2;; esac
limactl shell j86-build env "J86_TASK_ROOT=$TASK_ROOT" "J86_PROFILE=$profile" bash -c '
set -euo pipefail
kernel="$HOME/j86-kernel"; release=7.0.12-gdfa4d4208131-dirty
if [ "$J86_PROFILE" = candidate ]; then kernel="$HOME/j86-wifi-kernel"; release=7.0.12-j86-wifi1; fi
test "$(make -s -C "$kernel" ARCH=arm64 kernelrelease)" = "$release"
if [ "$J86_PROFILE" = audio-candidate ]; then kernel="$HOME/j86-audio-kernel"; release=7.0.12-j86-audio2; fi
test -s "$kernel/Module.symvers" || { echo "Complete matching exports required" >&2; exit 1; }
work="$HOME/j86-modules/repro-wifi-$J86_PROFILE"
out="$J86_TASK_ROOT/wifi/build/probes/$J86_PROFILE"
mkdir -p "$work" "$out"
dtc -@ -I dts -O dtb -o "$work/overlay.dtbo" "$J86_TASK_ROOT/wifi/hsic/j86-ehci-overlay.dts"
fdtput -r "$work/overlay.dtbo" /__symbols__
python3 - "$work/overlay.dtbo" "$work/j86_overlay_blob.h" <<PY
from pathlib import Path
import sys
b=Path(sys.argv[1]).read_bytes()
lines=[",".join("0x%02x"%v for v in b[i:i+12])+"," for i in range(0,len(b),12)]
Path(sys.argv[2]).write_text("static const unsigned char j86_overlay_blob[] __aligned(8) = {\n"+"\n".join(lines)+"\n};\n")
PY
for kind in hsic phy enumeration firmware otp host; do
 mod="$work/$kind"; mkdir -p "$mod"
 case "$kind" in
 hsic) cp "$J86_TASK_ROOT/wifi/hsic/j86_hsic_range.c" "$J86_TASK_ROOT/wifi/hsic/Makefile" "$mod/"; names=j86_hsic_range;;
 phy) cp "$J86_TASK_ROOT/wifi/phy-probe/"*.c "$J86_TASK_ROOT/wifi/phy-probe/Makefile" "$mod/"; names=j86_wifi_phy_probe;;
 enumeration) cp "$J86_TASK_ROOT/wifi/enumeration-probe/"*.c "$J86_TASK_ROOT/wifi/enumeration-probe/Makefile" "$mod/"; cp "$work/j86_overlay_blob.h" "$mod/"; names=j86_wifi_enumeration_probe;;
 firmware) cp "$J86_TASK_ROOT/wifi/firmware-probe/"*.c "$J86_TASK_ROOT/wifi/firmware-probe/"*.h "$J86_TASK_ROOT/wifi/firmware-probe/Makefile" "$mod/"; cp "$J86_TASK_ROOT/wifi/enumeration-probe/j86_wifi_enumeration_probe.c" "$mod/j86_wifi_enumeration_base.h"; cp "$work/j86_overlay_blob.h" "$mod/"; names="j86_wifi_firmware_probe j86_wifi_nvram_probe"; printf "obj-m += j86_wifi_firmware_probe.o j86_wifi_nvram_probe.o\n" >"$mod/Makefile";;
 otp) cp "$J86_TASK_ROOT/wifi/otp-probe/"*.c "$J86_TASK_ROOT/wifi/otp-probe/"*.h "$mod/"; cp "$J86_TASK_ROOT/wifi/enumeration-probe/j86_wifi_enumeration_probe.c" "$mod/j86_wifi_enumeration_base.h"; cp "$work/j86_overlay_blob.h" "$mod/"; names="j86_wifi_otp_probe j86_wifi_otp_snapshot"; printf "obj-m += j86_wifi_otp_probe.o j86_wifi_otp_snapshot.o\n" >"$mod/Makefile";;
 host) cp "$J86_TASK_ROOT/wifi/host/"*.c "$J86_TASK_ROOT/wifi/host/Makefile" "$mod/"; cp "$work/j86_overlay_blob.h" "$mod/"; names=j86_wifi_host;;
 esac
 if [ "$J86_PROFILE" != known-good ]; then
  for source in "$mod/"*.c "$mod/"*.h; do
   [ -f "$source" ] || continue
   sed -i "s/7.0.12-gdfa4d4208131-dirty/$release/g" "$source"
  done
 fi
 make -C "$kernel" ARCH=arm64 M="$mod" KCFLAGS=-Werror modules >"$out/$kind.build.log" 2>&1
 for name in $names; do cp "$mod/$name.ko" "$out/"; done
done
sha256sum "$out/"*.ko >"$out/SHA256SUMS"
echo "Built $J86_PROFILE Wi-Fi modules only. Nothing loaded or booted."
'
