# Bounded J86 UART4 control inventory

This diagnostic is not a serial driver or an Oscar/M7 boot procedure. It has no
DT binding or automatic loader. Build only with `./sensors/uart-inventory/build.sh`.

The module requires exact `apple,j86`, 4KiB pages, matching kernel release, and
an initially powered-off UART4 domain. It takes a balanced generic power-domain
reference and reads only ULCON, UCON, UFCON, UMCON, UBRDIV and UDIVSLOT. It does
not read FIFOs, interrupt/error status, or send/reset/configure anything. Generic
power-domain acquisition/release necessarily changes domain power transiently.
It verifies the original complete PMGR word after cleanup. Successful init
returns ECANCELED deliberately so the diagnostic cannot remain resident on a
kernel without module unloading. An insmod error alone is not a pass: require
J86_UART4_INVENTORY_PASS and the matching restored power words.

October 31, running 7.0.12-j86-audio2: control values were 3, 0x405, 1, 1,
0x0c, 0 respectively; power was 0x200 before and after. This is a live bounded
observation, not evidence of running M7 firmware or a qualified baud rate. The
boot console's fixed 24MHz clock does not establish UART4's parent frequency.
No receive experiment should guess baud from this divisor. Next dependencies:
resolve stock UART clock selection, establish firmware ownership/liveness, then
review a bounded receive-only attachment before any sensor subscription.

No compiled module, firmware, identifying logs or device calibration is published.
