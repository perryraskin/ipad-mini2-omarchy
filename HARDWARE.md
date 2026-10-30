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
mapping is compiled but unbooted. RAM firmware/NVRAM transport is qualified by the bounded probes below.
Per-device RF calibration, scan and association still require qualification. Stock firmware is seyval
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

The offline `audio/derive-amplifier.py` model also traces the exact stock
CS35L19 revision/boost/power/status routines using private owner speaker records.
The modeled amplifier revision and every fake board/I2C/GPIO callback are
reported. It neither powers hardware nor supplies SIO playback.

## Firmware and private NVRAM qualification

Bounded RAM firmware tests now pass: the stock seyval image reaches postboot
0xa123 and answers BCDC version/revision queries. Its unconfigured board ID is
ffff and is not used as hardware identity. Exact-stock RDHW16 OTP reads recover
the module vendor tag; this device reports `u`, selecting the matching stock
seyval-u-kk variant. A private TRX with that NVRAM and the live Wi-Fi MAC boots,
reports expected board ID `0x67e` / revision `0x1303` and passes an owner-MAC comparison without
logging the address. Each probe removes its temporary host and restores power.

Per-device RF calibration overrides, scan and association are still unqualified.
The private preparation receipt explicitly says `rf_qualified=false`. No interface
up, scan or TX command is used by these probes. All firmware, NVRAM, OTP and
calibration artifacts stay private. The optional OTP snapshot module exposes
its temporary RAM cache only to root and provides a clear control; it does not
write OTP or device storage.

## Reversible host and manual rotation checkpoint

The exact-board Wi-Fi host module starts disabled. Its root-only `enabled`
parameter adds/removes the reviewed EHCI1 overlay, holds a module reference
while active, and checks power restoration on stop. Baseline enable/disable
qualified enumeration of `0a5c:bd1c` and unchanged touch state. Matching candidate
modules compile; the candidate remains unbooted and firmware autostart is off.

Manual `j86-rotate` coordinates the output transform and the native touchscreen
calibration matrix. A 90-degree synthetic native-name touch reached the expected
Wayland surface coordinates. Setup → Rotate screen toggles portrait/landscape;
the session restores display and input orientation together before launching
its shell. The 180/270-degree and compositor-restart live checks were interrupted
when the USB device disappeared; they are not qualified. Physical alignment and
motion-sensor automatic rotation remain pending.

The root NBD server rejects writes and holds a Mac idle-sleep assertion only
while a client is connected. An isolated real-protocol test verifies reads,
EROFS on writes and an unchanged backing file. The existing mounted session
uses the older server process; this source change takes effect on its next start.

## Offline RF calibration mapping

The exact-stock structure builder and NVRAM-selection body now produce the same
31 overrides as a portable signed conversion/permutation. Comparison passes for
owner live calibration and five full-range synthetic seeds. The 24 PA fields
replace stock defaults; seven RSSI gain-delta groups are added. All values remain
private. An opt-in preparation path builds a private TRX with those overrides,
unchanged firmware bytes and valid CRC. No live test has used this image.
Clock metadata lookup and final stock buffer compaction are omitted by the
model; board mode is explicitly modeled as zero. RF qualification, firmware
acceptance, scan and association remain development/physical-test work.

## Offline SIO DMA transport model

`audio/derive-sio.py` executes the exact stock SmartIO DMA configuration and
setParam routines using synthetic data. Configuration opcode5 references shared
configuration storage; parameter opcode3 carries parameter10 and a modeled frame
size128. The model checks field placement and successful reply0x65, plus command
and shared-slot cleanup after modeled allocation/submission failures. It has
passed success, no-slot and submit-error cases. Command pools, shared-slot
allocation, firmware replies and transport success are explicit fakes.

No SIO firmware boot, shared-memory DMA mapping, interrupts, cyclic PCM transport
or hardware audio is implemented by this model. The existing Linux ADMAC driver
is not this A7 SmartIO transport. The owner ADT identifies SIO at0x20ae00000,
size0x2000, interrupts133/132/135/134 and IOP version1. Do not read mailbox data
registers speculatively: those can consume messages.

## Offline Oscar command framing

The pure `sensors/oscar/packet.py` helper reproduces the matching stock outgoing
command encoder: bounded14-byte header, at most114payload bytes and independent
little-endian16-bit checksum spans. Its strict decoder accepts this outgoing
command form only, not arbitrary sensor reports. The emulator comparison passes
24 synthetic frame cases plus four span-checksum cases and stops before the
stock transport callback. No UART, firmware boot, accelerometer report decoding
or automatic rotation is implemented. These sources do not transmit anything.


## Experimental A7 SIO core adaptation

Orchard hardware commit4f15a70b9c59687fe8cd72b6ea2fbb2823c54d92 supplies
reusable S8000/T8010 SIO core and cyclic DMA sources. A7 IOP-v1 uses different
register offsets: CPU control0x28, AP firmware remap words0x08/0x0c,
IOP mapping0x10/0x14, size0x18/0x1c, enable0x20; mailbox windows0x1000..
and time counter0x810/0x818. `audio/derive-iop.py` verifies remap, run-bit,
time-sync and64-bit mailbox operations against exact stock code in emulator
RAM. A7 stock ready opcode0x6d requires protocol parameter3, matching the
upstream handshake. Shared-region setup still requires live qualification.

The opt-in adaptation patch translates offsets for an experimental exact J86
compatible and exposes only ADT MCA1 endpoints0x2a/0x2b. It compiles with
-Werror and a complete export table against7.0.12-j86-wifi1. Firmware boot is
disabled by default, with board/page/firmware-size guards; it refuses to reset
an already-running A7 IOP. No DT overlay, module or firmware has been activated.
The baseline build has no complete export table and is not load-qualified.

The exact stock SmartIO constructor references a464208-byte firmware section.
A private extractor verifies the cache hash, module identity, pointer, section
mapping and length. Firmware remains private and unbooted. No SIO firmware,
DMA-engine or PCM support is enabled by publishing these experimental sources.
