# A7 SIO handoff checkpoint

## What is established

The exact stock-code model now executes A7 mailbox reset, TX/RX start/stop,
RX enable read-modify-write, and both empty-status methods. TX and RX share
0x1000/0x1004. Patch 0003 skips the newer second bank on A7 while preserving
other SoCs. The core, DMA and matching virt-dma dependency compile with Werror
for audio2. This build result does not establish playback.

The expanded passive inventory confirmed a stopped CPU, stable inherited mapping,
and empty disabled mailboxes. A separate private, explicitly enabled polling
experiment received the expected `0x036d0000` READY message from the exact owner
firmware. It sent no setup/DMA messages and made no amplifier writes.

## Failed cleanup: recovery required

That experiment did **not** pass restoration. The SIO power domain changed from
fully on to a transitional state, and a subsequent inventory correctly refused
access. CPU-stop readback did not report failure, but that alone is insufficient
for a clean handoff. Do not call the experiment qualified, integrate it into the
normal boot, or repeat it in the same session. Its draft stays private and is not
part of this published source checkpoint. Internal storage was not accessed.

BusyBox insmod also made a fallback initialization attempt after the first init
returned an error. The fallback refused before writes. Use the dedicated
single-finit_module loader, including its explicit parameter support, for all
future experiments; never BusyBox insmod for an init-that-cleans-up probe.

## Next audio work

1. Recover the isolated audio2 RAM boot and re-inventory the initial power state.
2. Trace firmware boot-time PMGR writes and define a real power-domain ownership
   and stop protocol. A passive power lease is insufficient for firmware boot.
3. Rework the private probe cleanup and verify failure paths before another run.
4. Qualify shared regions, IRQ handling, muted cyclic DMA, NCO and Switch3.
5. Only then qualify the two exact CS35L19 configurations and a quiet tone.

No ALSA playback card, speaker output, or volume-key audio mode is qualified.
The inherited-remap guard in patch 0002 remains in place and boot defaults off.
