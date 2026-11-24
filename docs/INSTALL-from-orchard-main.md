# Test installation from Orchard main: iPad mini 2 Cellular

> **WARNING — J86 / iPad4,5 is untested upstream.** All implemented features are untested on this board; other features, including GPU desktop, are missing. Boot is tethered on every cold start. This is a proposed test procedure for [Henrik's request](https://github.com/OrchardLinux/orchard/pull/66#issuecomment-7138279929), **not a qualified installation** or approval to run it. See [status](STATUS.md) and the [J86 profile](https://github.com/OrchardLinux/orchard/blob/53a24f1ef46e1bce8ec9539a2100fa6abfe44424/devices/j86/device.toml). No device operations were performed while preparing this document.

Verified 2026-11-24 against Orchard main `53a24f1`, Omarchy A main `ebe8f05`, and Resize APFS `d1301cd`. Commands below are for review and later, separately authorized execution. Our existing known-good RAM profile remains unchanged.

## 1. Back up iOS first

On the Mac Studio, open **Finder > iPad > General**, select **Back up all of the data on your iPad to this Mac**, enable **Encrypt local backup**, and choose **Back Up Now**. Store the encryption password safely; it is needed to restore the backup. After completion, open **Manage Backups**, confirm the new backup's date/time and lock icon. Record those details before proposing a storage change. See Apple's [Mac backup guide](https://support.apple.com/en-us/108796) and [encrypted backup guide](https://support.apple.com/en-us/108353).

Charge the battery before starting. [ipsw.me for iPad4,5](https://ipsw.me/iPad4,5) currently reports iOS **12.5.8 (16H88)** signed (checked via its API on 2026-11-24). Recheck ipsw.me and Apple's TSS acceptance before any restore; signing can change. A listing is not a completed restore test.

## 2. Host prerequisites and main builds

The [Omarchy A README](https://github.com/OrchardLinux/omarchy-a/blob/ebe8f05c4d30c9953ee4fc3c2356f1dcf78feb46/README.md) names [palera1n 3.0 beta 3](https://github.com/palera1n/palera1n/releases/tag/v3.0.0-beta.3) and this Mac environment setting:

```sh
export RA1N_CLI=1 PALERA1N=/Applications/palera1n.app/Contents/MacOS/palera1n
```

That README's generic install requirements say iOS 15 or later; **they do not establish this iOS 12 J86 procedure**. Current [Resize APFS requirements](https://github.com/OrchardLinux/resize-apfs/blob/d1301cda3dc402fe3fda037b2c460f275f90ca94/README.md) instead document checkra1n 0.12.4 for iOS 12–14, downloaded by its launcher, with Rosetta required on Apple Silicon. Its iOS 15+ route now uses palera1n beta 4. Do not assume beta 3 is the iOS 12 boot tool. Download the [Resize APFS v0.3.3 release](https://github.com/OrchardLinux/resize-apfs/releases/tag/v0.3.3); confirm the selected release includes the documented iOS 12 payload before use (the main README alone does not prove asset contents).

Use fresh directories outside our working RAM setup. The [Orchard setup and development instructions](https://github.com/OrchardLinux/orchard/blob/53a24f1ef46e1bce8ec9539a2100fa6abfe44424/README.md) document:

```sh
git clone https://github.com/OrchardLinux/orchard
cd orchard
./setup
orchard doctor
```

`./setup` proposes and installs host dependencies; rerun until Ready. `orchard doctor` reports requirements without changing them. These commands are included for review, not run here.

The setup launcher uses the newest Orchard nightly; `ORCHARD_VERSION` can pin a nightly, but this guide supplies no invented version value. A checkout's `bin/orchard` uses that checkout instead. Latest tagged [Omarchy A v0.3.4](https://github.com/OrchardLinux/omarchy-a/releases/tag/v0.3.4) (2026-11-23) predates Mini 2 support. The repository [install.sh](https://github.com/OrchardLinux/omarchy-a/blob/ebe8f05c4d30c9953ee4fc3c2356f1dcf78feb46/install.sh) forwards to the latest tagged release, so fetching it from main does **not** select current main hardware support.

The documented main-checkout path is to clone Omarchy A beside Orchard, then use the Orchard checkout launcher, as described by [Omarchy A development](https://github.com/OrchardLinux/omarchy-a/blob/ebe8f05c4d30c9953ee4fc3c2356f1dcf78feb46/README.md) and [Orchard tooling](https://github.com/OrchardLinux/orchard/blob/53a24f1ef46e1bce8ec9539a2100fa6abfe44424/docs/tooling.md):

```sh
# From the parent directory containing orchard/
git clone https://github.com/OrchardLinux/omarchy-a
cd omarchy-a
../orchard/bin/orchard build --device j86
```

The distribution build creates `out/releases/dev-DATE-TIME`; installation uses the last build. `--device j86` selects the documented board without device discovery during the build. Verify both checkout revisions before a later execution; main and nightly move. No rolling installer URL or `install.sh --cli` recipe is asserted here: the checkout build/install path is what the fetched docs establish. Successful build and J86 installation remain unverified.

## 3. Resize APFS — separate approval gate

**STORAGE CHANGE: requires Perry's explicit yes AFTER the encrypted backup is verified.** Stop here until that approval exists.

The [upstream procedure](https://github.com/OrchardLinux/resize-apfs/blob/d1301cda3dc402fe3fda037b2c460f275f90ca94/README.md) is:

1. Download and unzip the release ZIP; open Terminal in its extracted folder.
2. Run the following only after authorization, answering **iOS 12** when asked and following the launcher's DFU prompts:

   ```sh
   ./resize-apfs boot
   ```

3. Wait for iOS to start, unlock it, and open Resize APFS if it does not open itself.
4. Choose **Adjust size**, enter the target, review and confirm. Leave **at least 9 GB** for Linux, per the [Omarchy A README](https://github.com/OrchardLinux/omarchy-a/blob/ebe8f05c4d30c9953ee4fc3c2356f1dcf78feb46/README.md).
5. Wait for **Completed and verified** before restarting. Do not restart or run another storage tool while an operation is working. Missing status alone is not permission to retry.
6. On iOS 12–14, press Enter in the host terminal when finished so the launcher removes the temporary app.

Upstream explicitly supports A7–A11 on iOS 12–14, and can remove the `orig-fs` snapshot if it limits shrinking. Its listed iOS 12 hardware test is an iPod touch 6; **J86 is not in the tested list**. Loading the utility does not itself resize storage; confirming the app's plan does.

## 4. DFU and installation from main — separate approval gate

**WRITES INTERNAL STORAGE: requires Perry's explicit yes.** Verify backup, the completed resize, the board identity, exact build revisions and proposed target layout before approving installation.

For Home-button hardware, Apple's historical [iOS Security guide, page 5](https://www.apple.com/hk/en/privacy/docs/iOS_Security_Guide.pdf) describes DFU with Power and Home held together, releasing Power after **8 seconds** while continuing to hold Home. Follow the boot tool's timed prompts; DFU has a black screen. An Apple logo or recovery graphic means the expected DFU state was not reached. The Omarchy README's Apple link currently resolves to a **Mac firmware** article, not an iPad DFU guide. Apple's [iPad recovery guide](https://support.apple.com/en-us/108925) concerns recovery mode, which is distinct from black-screen DFU. No J86-specific timing qualification was performed here.

After the authorized DFU entry, from the Omarchy A checkout with the completed build:

```sh
../orchard/bin/orchard install
```

This is the [documented install-last-build command](https://github.com/OrchardLinux/omarchy-a/blob/ebe8f05c4d30c9953ee4fc3c2356f1dcf78feb46/README.md), using the current Orchard checkout. Do not substitute the latest-release curl installer for this main test.

The [installation lifecycle](https://github.com/OrchardLinux/omarchy-a/blob/ebe8f05c4d30c9953ee4fc3c2356f1dcf78feb46/docs/how-it-works.md) provisions a host SSH key through serial and pins the recovery host key. It asks for the system password and six-digit Linux lock-screen PIN, offers targets and a partition plan, and asks for confirmation before writing. These are installed-system credentials, not a request to disclose secrets in chat. The installer also offers to authorize this computer's SSH key for later access ([Orchard README](https://github.com/OrchardLinux/orchard/blob/53a24f1ef46e1bce8ec9539a2100fa6abfe44424/README.md)).

It writes a FAT32 boot partition and ext4 root beside iOS, never resizes APFS or touches partitions outside the plan. **Replacing an earlier Linux installation deletes it.** Stop if the target or free-space plan is unexpected. Linux storage is unencrypted.

## 5. Every cold boot

The [boot lifecycle](https://github.com/OrchardLinux/omarchy-a/blob/ebe8f05c4d30c9953ee4fc3c2356f1dcf78feb46/docs/how-it-works.md) is tethered: checkm8 from DFU → PongoOS → m1n1. Each cold start requires the Mac and DFU, followed by the [documented launcher commands](https://github.com/OrchardLinux/orchard/blob/53a24f1ef46e1bce8ec9539a2100fa6abfe44424/README.md):

```sh
orchard launch
# Alternative: select an entry interactively
orchard launch --list
# Alternative: boot one entry once; replace ID with an actual listed entry
orchard launch --entry ID
```

Normal power-on without the computer is expected to follow Apple's original iOS boot chain, but the fetched Orchard/Omarchy docs do **not explicitly confirm that return-to-iOS procedure for J86**. Treat that as an item to confirm before installation, not a verified rollback promise.

## 6. Test checklist

Use one-line observations, including failures. Shared J85 hardware results do not qualify J86. Test sleep/wake last, after recording the other results and saving work; do not run a storage workload during this first check. The [J85 profile](https://github.com/OrchardLinux/orchard/blob/53a24f1ef46e1bce8ec9539a2100fa6abfe44424/devices/j85/device.toml) records Home wake; the shared [power design](https://github.com/OrchardLinux/omarchy-a/blob/ebe8f05c4d30c9953ee4fc3c2356f1dcf78feb46/docs/power-and-lock.md) is not a J86 test.

| Item | How to observe | One-line result |
| --- | --- | --- |
| Touch | Tap controls and drag across the screen | Pending |
| Wi-Fi | Connect through NetworkManager; load a page | Pending |
| Speakers | Play a familiar clip at low volume; check both speakers | Pending |
| Charging | Connect a power source; observe charge state and percentage trend | Pending |
| Sleep/wake | Use the available sleep control; try Home/Power wake and recheck touch/network | Pending |
| Display | Check desktop visibility, clipping and software-rendered responsiveness | Pending |
| Battery | Observe percentage in the bar; record whether it updates plausibly | Pending |
| Backlight (optional) | Change brightness and observe the panel | Pending |
| Buttons (optional) | Check Home and Power responses | Pending |

Perry can copy and fill this reply himself:

```text
J86 / iPad4,5; Orchard revision: ___; Omarchy A revision: ___
Touch: ___
Wi-Fi: ___
Speakers: ___
Charging: ___
Sleep/wake: ___
Display: ___
Battery: ___
Backlight/buttons (optional): ___
```

## 7. Rollback

First distinguish returning to iOS from removing Linux. Normal iOS boot is expected, but remains unconfirmed in these upstream J86 instructions as noted above.

For a full reset, Apple's [Finder restore procedure](https://support.apple.com/en-us/118107) erases the device and reinstalls signed iOS. Recheck iPad4,5 signing first; iOS 12.5.8 (16H88) is today's reported signed target, not a permanent guarantee. Then restore the verified encrypted backup through Finder and supply its saved password. This is another destructive action requiring explicit approval.

Upstream **does document partition removal**: [Resize APFS](https://github.com/OrchardLinux/resize-apfs/blob/d1301cda3dc402fe3fda037b2c460f275f90ca94/README.md) can erase Linux partitions after APFS and reclaim their space. That is a storage change, with backup and approval required; no J86 test is listed. The fetched Orchard docs do not provide a complete end-user uninstall procedure covering both partitions and boot entries. Do not improvise partition commands or boot-entry deletion. Finder restore is the full-reset route; the exact fate of Orchard entries on J86 was not independently tested here.

## 8. Troubleshooting

Use the pinned [Omarchy A troubleshooting guide](https://github.com/OrchardLinux/omarchy-a/blob/ebe8f05c4d30c9953ee4fc3c2356f1dcf78feb46/docs/troubleshooting.md). Read its symptom-specific guidance before a later authorized retry. Do not run cleanup, boot or storage commands merely because they appear in that page. Record the exact revision and failure stage for Perry's own maintainer reply.
