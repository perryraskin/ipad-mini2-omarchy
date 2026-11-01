# J86 diagnostic

Read-only four-pin baseline for I2C2, speaker reset and keepalive. Live stable PASS; no codec configuration.

Build with `bash build.sh` from this directory. Default off; never use BusyBox
insmod for these init-and-cleanup diagnostics. Use the single-finit_module loader.
No internal storage access. Build success is separate from the stated live result.
