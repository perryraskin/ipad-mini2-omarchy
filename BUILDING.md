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

## Offline calibration mapping

`wifi/tools/derive-calibration.py KERNELCACHE LIVE_ADT` needs Unicorn and the
exact owner-extracted 16H88 cache. It executes the stock DT structure builder
and NVRAM override-selection body with modeled type/property, append and
snprintf callbacks. Clock-symbol lookup and final buffer compaction are omitted;
board mode is modeled as zero. It compares all 31 overrides against the portable
`wifi/tools/calibration.py` mapping without printing private values. Use
`--synthetic --synthetic-seed N` for full-range signed test data. An optional
`--private-output` writes the structure and override JSON as mode0600 files.

`prepare-ram-firmware.py --include-calibration` optionally applies this mapping
before rebuilding the private TRX. Use a new private output directory. This
option is off by default and **does not qualify RF**: its output has not been
booted or used to scan/associate. Unported optional DT formats are rejected.
The firmware body remains byte-identical. Run `python3 wifi/tests/calibration.py`
and `python3 wifi/tests/prepare-ram-firmware.py` without proprietary inputs.

`python3 apps/tests/root-readonly.py` exercises actual NBD reads and rejected
writes against an isolated ephemeral-port server and confirms the image hash.


Run `audio/derive-sio.py KERNELCACHE --scenario success` with Unicorn and the
matching owner cache. Repeat with `no-slot` and `submit-error` to verify modeled
cleanup. It uses only synthetic DMA configuration and never accesses a device.


## Inactive candidate packaging

The candidate scripts keep the known-good payload and kernel tree separate.
After supplying verified base assets and their local hash manifests, recover the
pinned initramfs with `python3 wifi/build/recover-initramfs.py`. In the ARM64 VM,
set `J86_TASK_ROOT` to the shared project path and run `wifi/build/prepare-kernel.sh`
then `wifi/build/package-kernel.sh`. These compile cfg80211/brcmfmacUSB and ALSA,
package matching modules into the isolated initramfs and build matching touch/PHY
sidecars. They do not boot or install anything.

Back on the host, run `python3 wifi/build/make-ramboot.py` to preserve the verified
loader/DT/bootargs and replace only the kernel gzip stream. Build candidate Wi-Fi
probe/host modules with `bash wifi/build-probes.sh candidate`, copy the resulting
`wifi/build/probes/candidate/j86_wifi_host.ko` into `wifi/build/candidate/`, then
run `python3 wifi/build/prepare-profile.py`. The profile remains unbooted with
host disabled and no firmware autostart. A physical DFU test with the known-good
fallback available is still required; this source companion omits boot assets.


Oscar framing fixture tests: `python3 sensors/tests/oscar-packet.py` needs no
private data. With Unicorn and the matching owner cache,
`python3 sensors/oscar/derive-packet.py KERNELCACHE` compares the portable encoder
to stock code in emulator RAM and stops before transport. It never opens UART.


`python3 tests/network-deadline.py` checks fragmented shell acknowledgment,
a total response deadline under trickling data, send-failure socket cleanup and
no command replay. A lost acknowledgment does not establish command failure;
inspect live state before retrying any device mutation.


## Experimental A7 SIO build

`python3 audio/sio/prepare-upstream.py --output audio/sio/source` downloads
hash-pinned public Orchard patches using authenticated `gh`, assembles only the
core/DMA/header files and applies the J86 patch. Existing output is refused.
`bash audio/sio/build-core.sh candidate` builds only the experimental core in
Lima against the matching full candidate export table. It never loads or stages
anything. Missing export tables are refused rather than allowing unresolved
symbols. The assembled DMA source still needs a kernel with DMA_ENGINE and
DMA_VIRTUAL_CHANNELS; those are absent from the current Wi-Fi candidate.

With Unicorn and the owner cache, run `audio/derive-iop.py KERNELCACHE` for the
A7 register model. `python3 audio/tools/prepare-sio-firmware.py KERNELCACHE`
extracts the exact firmware into mode0600 private files. The firmware is not
boot-qualified. `allow_j86_firmware_boot` is off by default; no live test or
live activation workflow is provided by this source checkpoint.


`audio/build/prepare-kernel.sh` runs in the ARM64 VM with `J86_TASK_ROOT` set.
It uses the separately assembled SIO sources and an isolated j86-audio-kernel
tree, enables DMA_ENGINE/virtual DMA and compiles Image/modules. Transport modules
are rebuilt with -Werror. Output is **build-only**: no initramfs or RAM payload
is prepared, and no candidate/default boot selection changes.

`bash audio/sio/tests/disabled-overlay.sh PINNED_J86_DTB` validates the disabled
DT overlay entirely on the host using dtc/fdtget/fdtoverlay. The required DT SHA
is checked before work, including the previously unassigned SIO-domain phandle
and AIC phandle 1. The standalone-overlay warning about that numeric external
AIC reference is suppressed only because the merged reference is checked against
the pinned base. No overlay is applied to a live kernel by this test.


## Host-only preparation checkpoint

Compile the A7 register-plan backend without device access:

```sh
cc -std=c11 -Wall -Wextra -Werror audio/mca/tests/plan.c -o /tmp/j86-mca-plan
/tmp/j86-mca-plan
python3 desktop/tests/session-keys.py
python3 sensors/tests/rotation-policy.py
python3 sensors/tests/iio-source.py
python3 wifi/tests/stage-driver-firmware.py
python3 power/tests/preflight.py
```

`wifi/tools/stage-driver-firmware.py --prepared-dir PRIVATE_PREPARED_DIR --output NEW_PRIVATE_DIR`
creates a new host directory with the driver filename and a disabled receipt.
It does not stage firmware into a device/rootfs. Inputs remain private.

After preparing the audio kernel, run `power/prepare-suspend-kernel.sh` inside
the same Linux ARM64 build environment with J86_TASK_ROOT set. It creates a
separate source/output tree and leaves the audio and Wi-Fi build assets alone.
No boot payload/profile or suspend activation is generated. Budget several GB
of additional build space. See power/README.md for the NBD-root restriction.
