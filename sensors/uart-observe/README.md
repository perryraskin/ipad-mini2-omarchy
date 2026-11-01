# Bounded passive Oscar UART observation

Build only: `bash sensors/uart-observe/build.sh`. This standalone diagnostic has
no DT binding or automatic loader. Exact J86/4KiB/matching release and an initially
off UART4 domain are required. It takes one balanced power reference and requires
the exact previously observed line controls and divisors before reading RX.

It polls RX-ready at 0x10 and consumes receive words at 0x24 for at most two
seconds or 512 bytes, using the existing bounded Oscar frame parser. Register
semantics are cross-checked against Linux's Apple S5L Samsung UART implementation.
It sends no commands, writes no UART/FIFO registers, changes no baud/flow settings,
and performs no GPIO/reset/firmware operation. Counts only are logged; unknown
payloads are not acceleration. Successful init cleans up then returns ECANCELED.

Live audio2 observation: zero bytes/frames in the two-second window, UART4 power
0x200 before/after. This does not prove that M7 is dead, or that streaming would
not work after a qualified boot/subscription. It establishes that no unsolicited
reports were observed at these inherited settings. Boot ADT declares a 24MHz
primary parent; the observed divisor12/fraction0 is consistent with roughly
115384 baud. The selected clock/nominal baud and running firmware still need
stock initialization evidence; no subscription or auto-rotation service is enabled.
