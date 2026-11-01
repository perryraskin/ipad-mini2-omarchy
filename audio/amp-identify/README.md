# J86 diagnostic

Opt-in CS35L19 identity-only diagnostic. Separate byte reads are required; the chip does not auto-increment registers. Live PASS: both amps ID 35a190/B0 and exact four-pin/power restoration. The temporary OF status overlay emits a kernel removal leak warning; do not repeatedly toggle it as a runtime driver.

Build with `bash build.sh` from this directory. Default off; never use BusyBox
insmod for these init-and-cleanup diagnostics. Use the single-finit_module loader.
No internal storage access. Build success is separate from the stated live result.
