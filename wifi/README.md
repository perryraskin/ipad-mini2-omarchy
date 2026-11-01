# J86 Wi-Fi bring-up

The verified running kernel disables WIRELESS and WLAN. Wireless modules built
with a changed configuration must not be loaded into it: networking structure
layouts may differ. Build a separate, uniquely named kernel and matching module
closure; retain the working boot image and touch driver as a fallback.

`build/prepare-kernel.sh` records the first-pass build in the case-sensitive
`j86-build` VM. The resulting Image does not yet contain an initramfs and must
not replace a boot asset. `build/recover-initramfs.py` recovers the original
hash-pinned initramfs. Its `/init` selects modules by `uname -r`, so a new
matching `/lib/modules/<release>` is required before packaging.

The exact J86 ADT places Wi-Fi behind EHCI1 at 0x20c400000, IRQ165. The bounded
host probe verified EHCI 1.00 and restored its power reference. Host-ready is
SoC GPIO163, device-ready GPIO164, device reset PMIC GPIO3. The HSIC2 PHY power
domain is PMGR offset0x20128. USB gadget and its PHY remain in use by the desktop.
The exact HSIC2 MMIO is0x20c000060, resolved through ADT ranges.
The separate0x20c900000 range belongs to the DMA remapper. Earlier shared-PHY
candidates targeting0x20c900060 are obsolete; use hsic/j86_hsic_range.c.
Bounded enumeration tests preserve the Lightning gadget and restore state.

Firmware and board NVRAM must be identified from the matching IPSW. Firmware,
raw ADT, calibration and device identifiers remain private local inputs.

The exact ADT identifies module-instance `seyval`. The matching 16H88 IPSW
supplies `wifi/4324b5/seyval.trx` and two NVRAM variants, rather than the A5
reference's 4334 firmware. `firmware-provenance.json` records public stock file
hashes and USB IDs. Variant selection and actual enumeration remain pending.
Stock USB IDs are0x0a5c:0xbd1c (running) and0x0a5c:0x4324 (CPU-less).

`build/package-kernel.sh` stages a fresh matching module tree, repacks the
initramfs and rebuilds touch with exact guards for the candidate release.
It writes only `build/candidate` assets; it does not activate or boot them.

## October31 live audio2 candidate checkpoint

The7.0.12-j86-audio2 RAM kernel booted; Perry confirmed aligned native touch.
Exact HSIC/host sidecars loaded, and internal USB enumerated0a5c:bd1c. The
matching stripped brcmfmac module and private staged J86 firmware hashes were
verified. Explicit `j86_allow_firmware=1` accepted BCM4324rev6 firmware6.46.79
and created wlan0. No credentials or firmware are published.

The stock root regulatory database/signature were copied to RAM firmware
storage. `start-networkmanager.sh` is an explicit experiment, never autorun:
NetworkManager profiles and state are tmpfs, USB root networking is strictly
unmanaged. A native rescan returned 27 network rows. Perry connected through
the touch UI; association and DHCP succeeded. The read-only root originally
had an empty resolver file, causing the Limited access status. A RAM resolver
bind populated from DHCP DNS fixed this: HTTPS to archlinux.org returned 200
with curl explicitly bound to wlan0 and all proxies bypassed; NetworkManager's
connectivity check returned full. Setup refreshes numeric DHCP DNS addresses
in RAM every three seconds, including after network changes; teardown removes
the resolver bind before detaching the root. Browser native-path qualification
and long-duration Wi-Fi/touch coexistence remain pending.
The driver reports missing optional CLM/txcap blobs, so available channels
may be limited. Do not replace board data or guess regulatory limits.

The controller stops the native host after its userspace processes exit and
unmounts NetworkManager tmpfs mounts before detaching the base root. Physical
clean-disable/re-enable and connectivity checks remain in HANDS-ON-QUEUE.md.

Combined-session follow-up: touch stopped and disabling Wi-Fi alone did not
restore it. A deliberate touch restart with Wi-Fi off restored taps. A later
staged host/radio test captured an entire32second finger gesture and release
while native Wi-Fi was enabled. Rejected touch packets were also counted;
the intermittent stall cause is not established. A slower-clock diagnostic
module built locally but was not loaded. Stable coexistence is not yet claimed.
EHCI disable restored its power register exactly in the live test.

The Quickshell shell initially selected no networking backend because it
started before NetworkManager. Restarting only that shell process after
NetworkManager became available cleared the backend error and the network
panel IPC opened successfully; existing app/compositor processes were kept.

Connection UI initially failed with NetworkManager
“Not authorized to control networking.” The RAM chroot has no active local
PAM/logind session, so the image's active-session rules did not authorize
the tablet user. Explicit setup now preserves existing rules and adds a
RAM-only rule for user tablet: network control, Wi-Fi enable/disable and
scan, and own/system connection-profile modification. Connection profiles
remain RAM-backed and USB remains strictly unmanaged. The tablet user's
five required permissions were verified as yes live. The controller unmounts
the policy bind during teardown. No wildcard or general administrator grant.

The source Wi-Fi inline failure label now uses the supplied failure reason
rather than categorizing every failure as a wrong password. Immediate D-Bus
authorization failures in the upstream backend may still appear only in its
log until the existing action timeout; use explicit permission checks when
diagnosing them. No password was read or logged in this investigation.
