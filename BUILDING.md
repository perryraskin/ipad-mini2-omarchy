# Build prerequisites

This source snapshot assumes an already prepared, matching J86 RAM-boot session.
It deliberately omits boot binaries, disk images, proprietary firmware, calibration
and private manifests. It cannot cold-boot a device from a clean clone by itself.
Use the referenced Pomme/Hoolock/Orchard projects for those base components.

## Native touch and HSIC

Use an ARM64 Linux build host with a case-sensitive filesystem. The local recipes
use a Lima VM named j86-build and a shared workspace; kernel sources/build output
must live inside the VM filesystem. Match Hoolock commit dfa4d42081312dd34ec33ee8d23174309f683188,
the provided research/kernel-4k.config and the exact running kernel release.
The baseline touch guard is 7.0.12-gdfa4d4208131-dirty. Do not remove its guard to
load a module into a different ABI.

Prepare the kernel configuration and modules, then build touch/native/ with the
kernel's external-module workflow. Build touch/tools/load-once.c with the ARM64
userspace compiler. It performs finit_module exactly once; the BusyBox insmod
fallback may retry a failed init and is unsuitable for bounded probes.

Provide your own matching J86.mtprops, live ADT, locally built j86_touch.ko and
load-once to `touch/tools/prepare-assets.py --help`. That tool refuses another
board or placeholder calibration and creates a private integrity manifest.
Never commit the resulting firmware, calibration or manifest.

`start-touch.py` verifies the live kernel, selected module vermagic and asset
hashes before transfer. `touch/tools/push-probe.py MODULE --check-only` validates every undefined
symbol against the live kernel without loading. Full loading is for reviewed
exact-board modules only. Stop native touch before any bounded touch probe.

The corrected HSIC source isj86_hsic_range.c. Build the overlay with dtc -@, remove
its generated __symbols__ node for the qualified symbol-less base DT, and generate
an 8-byte-aligned byte array named j86_overlay_blob for the enumeration probe.
Numeric phandles are checked against exact live node paths before application.
Do not publish an unreviewed overlay as a generic board support package.

## Desktop

`desktop/build.sh` clones the pinned Labwc commit, applies the patch, builds
against the read-only base root mounted at /mnt/j86-sysroot in the ARM64 VM, and
runs the actual patched handler tests. It produces desktop/build/labwc-rebuilt
without activating it. Dependencies are Meson, Ninja, GCC, pkg-config,
wayland-scanner and the sysroot's development headers/libraries.

Xwayland is disabled because the tested base has no Xwayland runtime. Opt in
with LABWC_TOUCH_LONG_PRESS_MS=600. The original compositor remains a rollback.
The build cross file is under desktop/build/j86-sysroot.ini.

## Host app storage tests

Run `python3 apps/tests/relay-duplex.py` and
`python3 apps/tests/client-disconnect.py` on the host. The first exercises the
production relay with both TCP windows saturated; the second verifies the real
subprocess-draining helper after its client disappears. Package signatures must
remain required. Never use iPad internal storage as the writable app layer.

Run `python3 touch/tests/start-profile.py` to verify candidate manifests select
their own touch module and wrong vermagic refuses before any upload.

## Bounded Wi-Fi builds

Run `wifi/build-probes.sh known-good` or `wifi/build-probes.sh candidate` with
the corresponding prepared kernel tree. It compiles the corrected PHY and
bounded enumeration/firmware/OTP probes, generates the aligned overlay header,
and writes modules only to the host build directory. It never loads or boots.

`wifi/tools/prepare-ram-firmware.py` takes owner stock firmware/NVRAM, live ADT
and private OTP inputs. It selects the OTP vendor-matched stock variant, inserts
the live MAC, preserves the firmware body and rebuilds the TRX length/CRC. Its
output is private and only qualified for an RF-disabled RAM probe. Read the
module's exact-board/kernel guards and cleanup path before loading anything.
The optional snapshot sysfs cache must be cleared after private extraction.

Host fixture tests: `python3 wifi/tests/prepare-ram-firmware.py`. These check
ambiguous vendor rejection, immutable firmware body, CRC/length consistency,
MAC replacement and malformed-input rejection without proprietary assets.
