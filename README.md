# iPad mini 2 J86 Linux bring-up

Experimental source companion for a tethered Omarchy A RAM desktop on
**iPad4,5 / J86AP (A7), 4 KiB pages**. This is not a standalone installer or a
complete daily-use port. It does not install to iPad internal storage.

Verified in a running Hoolock 7.0.12/Pomme session:

- Native N1 touch: owner-confirmed aligned app taps; reversible stop/restart.
- Brightness and 2× desktop scaling.
- Firefox browsing through a USB-only Mac SOCKS proxy.
- Signed Arch Linux ARM app installation in a separate Mac-backed ext4 overlay;
  clean detach, offline fsck, remount and retained app launch.
- Opt-in Labwc long-press right-click: synthetic native-touch tests open Firefox
  and window menus without a preceding left-click, including a mouse-free seat.
  Synthetic outside-corner drag resizes a window. Physical gesture QA is pending.
- Manual landscape display and touch transform agree in a synthetic test;
  physical rotation and session-restart QA remain pending.
- Internal Wi-Fi chip enumerates at high speed as 0a5c:bd1c; read-only boot-ROM
  query identifies chip 0x4324/revision6. Stock and vendor-matched NVRAM RAM
  firmware boot/command tests pass. Association is not working yet.

Audio, native Wi-Fi networking, automatic rotation, GPU acceleration, charging,
battery reporting and true system suspend remain unfinished. Power handling is
screen-off/wake and a hold menu; it does not suspend the SoC. HDMI is unverified.

The verified base root remains read-only on the Mac. Installed app binaries
persist on a second Mac disk; the shared home is still RAM-backed. A USB cable,
Mac and running storage/proxy services remain necessary.

## Source layout

`touch/native/` is the exact-board module. `touch/tools/prepare-assets.py`
prepares private owner-extracted firmware/calibration; these inputs are not
included. `start-touch.py` verifies the selected module/kernel profile.

`desktop/` contains the Labwc 0.20.2 patch, actual-handler tests, ARM64 build recipe,
RAM configuration and local app client. `apps/` contains the separate writable
app-root service and tests. `serve-apps-disk.py` uses a standard nbdkit backend.

`wifi/hsic/` contains the current exact-range PHY and temporary overlay source.
`wifi/enumeration-probe/` is a bounded observation, not a persistent Wi-Fi service.
`wifi/build/patches/` includes an experimental brcmfmac chip/USB-ID mapping.
`audio/` contains bounded inventory, exact-stock offline models, private SIO
firmware preparation and an experimental core adaptation that is disabled by
default. There is no qualified playback driver. `sensors/` contains offline
Oscar command framing and disabled rotation policy/IIO-reader drafts; no motion-sensor transport is active. `power/` contains a build-only suspend profile and read-only readiness report.

Read [BUILDING.md](BUILDING.md) and [HARDWARE.md](HARDWARE.md) before using these
sources. None of the scripts should be treated as a generic Apple-device port.

## References

- [Orchard Omarchy A](https://github.com/OrchardLinux/omarchy-a)
- [Pomme RAM boot](https://github.com/xenoaitham/pomme/releases/tag/v0.1.0)
- [Hoolock Linux](https://github.com/HoolockLinux/linux), commit
  `dfa4d42081312dd34ec33ee8d23174309f683188`
- [Cam's A7 J72 work](https://github.com/thisiscamk/ipad-air-j72-linux)
- [Omarchy hardware map](https://github.com/theChristopher16/omarchy-hardware-map)
- [Labwc](https://github.com/labwc/labwc),0.20.2 commit
  `97f28877a343e062f3178d201f0248cd9c2610cf`

Touch protocol/SPI references: Cascadia commit
`e8f3e045a5e38bde5a5a79e1cc72ae22020d63ac`, modpunk Omarchy-iPhone6s commit
`ed2a4584caa8bcf908d1958d791242932da8e26c`, and Hoolock SPI tests commit
`001939843409a0b27d5fd81a2d020d6779be2770`. Original file notices are retained.

Host-only A7 MCA register adaptation is documented in [audio/mca/README.md](audio/mca/README.md). The single ordered physical validation queue is [HANDS-ON-QUEUE.md](HANDS-ON-QUEUE.md). New experiments remain disabled; host checks do not qualify hardware.
