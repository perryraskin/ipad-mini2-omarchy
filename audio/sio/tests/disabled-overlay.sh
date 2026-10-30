#!/bin/bash
# Host-only DT resolution check; never applies an overlay to a live kernel.
set -euo pipefail
base=${1:?Pass the pinned public s5l8960x-j86.dtb}
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
expected=8e08d68be5a48dc98d9974b8333ba0d5cc9448426eda89852e7c80be3caf37b2
actual=$(sha256sum "$base")
[ "${actual%% *}" = "$expected" ]
[ "$(fdtget -tx "$base" /soc/interrupt-controller@20e100000 phandle)" = 1 ]
if fdtget "$base" /soc/power-management@20e000000/power-controller@20108 phandle >/dev/null 2>&1; then
 echo 'Pinned SIO domain unexpectedly has a phandle' >&2; exit 1
fi
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
# Numeric external AIC phandle1 cannot be resolved by dtc against the overlay
# alone. Validate it against the pinned base and the merged tree instead.
dtc -Wno-interrupts_property -@ -I dts -O dtb -o "$work/sio.dtbo" "$root/j86-sio-overlay.dts"
fdtput -r "$work/sio.dtbo" /__symbols__
fdtoverlay -i "$base" -o "$work/merged.dtb" "$work/sio.dtbo"
node=/soc/sio@20ae00000
[ "$(fdtget "$work/merged.dtb" "$node" status)" = disabled ]
[ "$(fdtget -tx "$work/merged.dtb" "$node" reg)" = '2 ae00000 0 2000' ]
[ "$(fdtget -tx "$work/merged.dtb" "$node" interrupt-parent)" = 1 ]
[ "$(fdtget -tx "$work/merged.dtb" /soc/interrupt-controller@20e100000 phandle)" = 1 ]
[ "$(fdtget -tx "$work/merged.dtb" "$node" power-domains)" = "$(fdtget -tx "$work/merged.dtb" /soc/power-management@20e000000/power-controller@20108 phandle)" ]
after=$(sha256sum "$base")
[ "$after" = "$actual" ]
echo 'PASS: pinned host-only overlay remains disabled; power reference and AIC resolve; base DT unchanged'
