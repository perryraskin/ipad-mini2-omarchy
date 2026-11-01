# J86 diagnostic

Read-only shared DMA inventory. Claims each peripheral resource before reading its two controls; refuses driver-owned regions. Live 16/16 after isolated UART0 unbind, all 32 controls zero and power unchanged. Not proof of DMA idle or firmware cleanup.

Build with `bash build.sh` from this directory. Default off; never use BusyBox
insmod for these init-and-cleanup diagnostics. Use the single-finit_module loader.
No internal storage access. Build success is separate from the stated live result.
