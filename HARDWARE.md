# Qualified scope and remaining hardware work

Only iPad4,5/J86AP is tested. The mini2 Wi-Fi J85, mini3, Air J72, A5 and later
Apple chips are not interchangeable device profiles.

## Touch

SPI1 at 0x20a084000, IRQ137; CS71/reset23/attention15/display-sync119.
PWM channel2 and exact PMIC rail enable handling come from the matching 16H88
board data and stock driver. Display-sync requires the stock alternate input
operation, not driving the pin high. Owner firmware and 1024-byte live panel
calibration remain private inputs. The native module restores owned controls
on stop; MODULE_UNLOAD is disabled in the qualified kernel.

## Wi-Fi

EHCI1 is0x20c400000, IRQ165. HSIC2 PHY is **0x20c000060**, resolved through
ADT ranges. The separate0x20c900000 block is the USB DMA remapper; mapping its
0x60 subwindow as the PHY was an earlier error and is not the current driver.
HSIC2 baseline words are 04,0c,153,08000000. Host-ready 163, device-ready 164,
PMIC GPIO3 reset. The Lightning PHY0x20c000020..3f is separate and stays active.

The reviewed stock wake/reset sequence enumerates0a5c:bd1c, interfaceff/02/ff,
4endpoints. Read-only DL_GETVER identifies0x4324/revision6, RAM 589824 bytes.
Boot-ROM boardtype/rev are 0 and cannot choose an NVRAM vendor variant.

The running kernel lacks wireless support. An inactive candidate adds cfg80211,
brcmfmacUSB and matching touch/HSIC modules. The experimental USB-ID/firmware
mapping is compiled but unbooted. Firmware download, exact NVRAM/calibration,
RF scan and association still require qualification. Stock firmware is seyval
from 4324b5; do not substitute Mini1's BCM4334 firmware.

## Audio

Two CS35L19 amplifiers at I2C2 addresses 40/41, shared reset 114/keepalive 161.
MCA1 is0x20a0c4000, IRQ148; NCO1 supplies its clock. Exact ADT resolves DMA to
**SIO**, not the A5 CDMA controller. A5 speaker defaults must not be transplanted.
The two 20-byte board speaker records are distinct private inputs.

A bounded inventory confirmed MCA version 1 and 128-word TX/RX FIFOs, restoring
power. The offline model traces exact-stock MCA/NCO routines with explicitly
fake platform callbacks. It is not hardware playback evidence. No speaker
power/clock programming or audible playback is qualified.

## Rotation and power

Oscar/M7 supplies motion data over UART4; no accelerometer IIO device is exposed.
Automatic rotation needs that transport and coordinated display/input transforms.
The running kernel lacks CONFIG_SUSPEND and a qualified A7 platform suspend
path. Screen blanking does not provide SoC sleep. Physical power/touch/HDMI tests
remain queued; no internal installation is attempted by this work.
