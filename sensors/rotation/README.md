# Disabled rotation path

Manual `desktop/j86-rotate` remains the usable fallback. It changes the display
and touch matrix together with rollback. No auto-rotation service is installed.

`policy.py` replays synthetic panel-axis acceleration and is dry-run by default.
`iio-source.py` can read a future, explicitly selected IIO device. It requires
an exact sensor name and a signed axis mapping; no board mapping is invented.
It reads only and exits on I/O, scale or helper errors. `--apply` explicitly
invokes the same manual helper. Stable gravity must persist for0.8s; flat,
diagonal, moving or stale readings reset the dwell. Only successful rotations
are acknowledged. There is currently no J86 IIO accelerometer to attach.

## Native A7/M7 bring-up draft

The J86 stock ADT locates Oscar/M7 under UART4, not an I2C accelerometer visible
to the application processor. UART4: `0x20a0b0000`, size0x4000, IRQ144,
clock gate84, clock IDs281/4, Samsung UART-v1, no flow control. Its DMA record
must be resolved independently; do not reuse the speaker DMA endpoints.
Oscar reset is GPIO66; time-sync GPIO160. Power functions refer to PMIC
rails0x212/0x214 and sensor rail0x202. These are opaque platform-function
arguments, not Linux regulator IDs or instructions to write PMIC registers.

A future kernel driver should use a bounded serdev transport and an IIO
accelerometer interface. Required stages:

1. Resolve UART clock parent/dividers, pinmux and exact Oscar power/reset
   ordering from the owner cache. Preserve existing firmware state; do not
   reset or upload guessed firmware. Determine whether a cold RAM boot requires
   private Oscar firmware or can attach to a running M7.
2. Model stock startup commands, channel handshake, timeouts and error cleanup.
   `oscar/packet.py` establishes outgoing IPC framing. `oscar/receive.py` and
   `j86-oscar-rx.h` now implement the independently stock-validated incoming
   checksum/length layer, including zero meaning256 bytes. They do not decode
   accelerometer reports. Corrupt packets are dropped; stock queues them with
   diagnostic channel0xba.
3. Derive incoming packet boundaries, sequence handling, sensor subscription,
   sampling rate, timestamps, units and loss recovery before exposing IIO data.
   Fuzz truncation, unknown channels, bad lengths, checksum and reconnect cases.
4. Consume this device's private live calibration properties, including
   sensitivity, orientation, interrupt calibration and temperature offsets.
   The stock ADT's syscfg placeholders are not valid calibration. Keep all
   identifying/calibration bytes private.
5. Register raw/scale/offset or calibrated SI acceleration with a verified mount
   matrix. Compare stationary poses before enabling `iio-source.py --apply`.

No new UART node is enabled and no PMIC/GPIO writes are supplied. Direct
accelerometer access behind Oscar is not a supported fallback. Physical pose
and touch alignment tests are in the consolidated hands-on checklist.


## Receive transport checkpoint

`sensors/build-transport.sh` builds `j86-oscar.ko` against the prepared audio
kernel, with `-Werror` and full matching exports. No module is loaded. The
serdev client refuses probe by default (`allow_running_attach=false`), requires
exact J86/4KiB, UART4 address/size, an explicit qualified baud and an explicit
attach-running-firmware property. No DT node, baud guess, power/reset, firmware
upload, subscriptions or automatic IIO device is supplied. Opening the UART
is itself unqualified and possible only after explicit opt-in and DT work.

`derive-receive.py` executes stock receive state8 at0x8401c00 and stops before
queue/consumer callbacks:20 length/checksum cases passed. Python tests cover all
split points; the exact C kernel parser matches500 mixed frame/noise cases.
The parser retains at most256 bytes and never interprets unknown payloads as
acceleration. Kernel logs expose only channel/command/length, not raw payloads.
