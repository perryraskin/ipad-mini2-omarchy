# Suspend preparation, disabled

The existing power-button daemon implements screen-off/wake and a hold menu.
Perry physically confirmed short-press screen-off, a second press waking the
display, and the held-button power menu on October31. It does not suspend the SoC. Its volume-key mode is RAM-only and defaults to
brightness; Setup can explicitly select audio and later restore brightness.
Audio mode uses the tablet user's PipeWire default sink and caps volume at100%.
Missing sinks fail without changing backlight settings.

`prepare-suspend-kernel.sh` creates a separate `7.0.12-j86-suspend1` build from
the prepared audio kernel. It enables SUSPEND and PM debug/test infrastructure,
keeps hibernation/autosleep/wakelocks off, and does not package a bootable payload
or activate a profile. Build output stays local. This is preparation, not a
working platform suspend implementation.

The verified J86 base DT already has `wakeup-source` on Home (PMIC GPIO2) and
Power (PMIC GPIO3), active low, input codes172 and116. No additional wake overlay
is needed for those declarations. Their parent PMIC/GPIO/AIC suspend handling
still needs qualification. A DT flag alone does not prove a usable wake IRQ.
The verified DT uses spin-table CPU enable methods and has no PSCI node. No invented PSCI CPU_SUSPEND call, CPU idle state or resume vector is added.

`suspend-preflight.py` is read-only and always reports disabled/unready until
A7 resume is qualified. It identifies NBD mounts/cmdline references and absent
kernel state support. It never writes `/sys/power/state` or changes the menu.

## Future controlled experiment

Use a self-contained RAM root with no NBD mounts; flush/detach the writable app
layer and stop package/proxy jobs first. Never suspend this USB/NBD session.
Keep the known-good RAM boot available. Inspect the actual candidate's state
and mem_sleep files: `freeze`/s2idle only freezes tasks and idles CPUs; it is not
proof of deep A7 suspend or useful battery savings. `mem` chooses mem_sleep's
selected mode, so do not assume it means deep sleep.

First test PM freezer/device checkpoints with serial and a physical recovery
path, then qualify GPIO wake, timekeeping, PMIC/AIC, USB re-enumeration, NBD
recovery (after wake, not during suspend), display, touch, Wi-Fi and audio
ordering. A7 deep sleep additionally needs exact SoC/bootloader resume support;
CONFIG_ARM_PSCI_FW does not establish that support on this RAM boot chain.
Only after repeated recovery and measured power reduction should short Power
press request suspend. Preserve the existing screen-only fallback and hold menu.

All physical steps live in [HANDS-ON-QUEUE.md](../HANDS-ON-QUEUE.md).

## Host build result

The separate ARM64 Image and all configured modules built successfully as `7.0.12-j86-suspend1`. [build-receipt.json](build-receipt.json) records artifact/config hashes and the unchanged DT wake audit. No RAM payload was generated and no device boot or suspend test occurred.

The new Oscar attach draft rejects system suspend while attached because UART/M7 wake is unqualified. The MCA bench draft rejects system suspend while its clock/power lease is active. Neither adds stream resume support or a new suspend menu entry. These compile-time guards do not establish deep A7 resume.
