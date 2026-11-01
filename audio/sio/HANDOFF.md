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

## Cleanup remains unqualified; power diagnosis corrected

The private experiment did **not** pass its exact-word restoration check. The
initial description of the observed PMGR value as a stuck/transitional power
state was too strong. The Linux Apple PMGR provider explicitly recognizes
AUTO_ENABLE with target ACTIVE even when hardware has clock-gated the block.
`power-state.py` distinguishes controls from PS_AUTO, PS_ACTUAL and historical
status bits. The observed change is consistent with automatic clock gating and
unchanged control fields. It is not proof of a firmware PMGR write or damage.

This correction does not retroactively qualify cleanup: individual mailbox,
remap, timer and peripheral restoration was not captured sufficiently to establish
it. CPU-stop readback alone is insufficient. The private boot probe stays blocked.
Internal storage was not accessed. Changing the host USB port restored Pongo enumeration. A fresh isolated audio2
RAM boot now has a working USB shell; no NBD disks or desktop clients are active.

## Firmware startup affects shared peripherals

`audio/derive-firmware-start.py` executes the exact private firmware from its
reset vector through its READY mailbox write in Unicorn. Under explicitly
zero-filled MMIO, it records 121 MMIO writes, including three writes (0,0,1) to
each of 32 DMA control registers across sixteen peripheral bases. The owner ADT
maps affected bases to SPI, UART and MCA devices, including SPI1, UART4 and MCA1.
Thus sending no DMA commands does not mean firmware startup makes no DMA-register
writes. This makes an audio-only ownership lease insufficient.

The model observes no PMGR writes before READY. It stops there and does not
model post-READY behavior, hardware automatic gating, interrupts or DMA effects.
Do not infer a cause for the live power change from this result. Firmware stays
private; the published model requires its exact hash and contains no firmware.

`derive-iop.py` also executes the stock inherited stop method with exact A7
virtual overrides. It clears RX enable, disables two modeled interrupt sources,
clears CPU_RUN, and calls the provider callbacks; the remap-disable override is a
no-op, leaving the inherited mapping enabled. IRQ/provider callbacks are fakes,
so this is sequencing evidence, not proof of live quiescence or buffer lifetime.

BusyBox insmod also made a fallback initialization attempt after the first init
returned an error. The fallback refused before writes. Use the dedicated
single-finit_module loader, including its explicit parameter support, for all
future experiments; never BusyBox insmod for an init-that-cleans-up probe.

## Next audio work

1. Completed: isolated audio2 RAM boot with SIO off and working USB shell.
2. Completed: read-only inventory of all 32 DMA control words across 16 blocks.
   All were stable at zero; each power word was unchanged at 0x200. UART0 first
   refused the resource claim while samsung-uart owned it. After confirming it
   was not a console and had no open users, it was unbound. Rebinding failed
   with EINVAL; UART0 remains unbound in this isolated session, USB unaffected.
   Zero controls do not establish ownership, quiescence or safe restore. The
   shared startup blocks at 0x20a001000 and 0x20a100000 remain unresolved.
3. Implement ownership and cleanup for the complete startup footprint, with
   per-component receipts and status/control-aware power checks. Never free a
   DMA-visible buffer until its producer and all relevant DMA engines quiesce.
4. Qualify shared regions, IRQ handling, muted cyclic DMA, NCO and Switch3.
5. Only then qualify the two exact CS35L19 configurations and a quiet tone.

No ALSA playback card, speaker output, or volume-key audio mode is qualified.
The inherited-remap guard in patch 0002 remains in place. Patch 0004 blocks A7
probe before power/MMIO access even with the experimental parameter enabled,
until shared-peripheral handoff exists. Other SoCs are unchanged.

## Shared-block research boundary

The startup model now emits the eight writes outside SIO and peripheral DMA
controls, including their instruction PCs, addresses, sizes and values. The
owner ADT does not advertise a `reg` range covering either shared block (using
arm-io physical base 0x200000000). Their restore semantics remain unknown;
reading a word and writing it back is not a validated cleanup operation for a
potential write-one-to-clear, command or interrupt register. No live access to
these unresolved blocks was added.

UART0's serial0 alias selects the same static driver port on reprobe. In the
current samsung_tty source, removal leaves port.mapbase nonzero, the default
initializer does not clear it, and init_port rejects a nonzero mapbase with
EINVAL. This is a source-supported explanation for the observed failed rebind,
not a reason to patch kernel memory in the live diagnostic session. A future
handoff must account for UART lifecycle, not merely release its MMIO claim.

## Persistent isolated session: live progress

A private experimental session owner now holds all sixteen affected peripheral
MMIO ranges and power-domain references, four shared register ranges, four
host interrupts requested disabled, both speaker GPIOs low, and the exact
hash-checked firmware allocation until RAM reboot. This avoids pretending to
restore undocumented shared registers. Firmware READY passed with USB alive.
This is exclusive diagnostic ownership; ordinary touch/desktop clients cannot
be started against these leased controllers.

The current Orchard ten-command region initializer is not A7-compatible:
EP0 general buffer parameters 0x0f/0x10 acknowledged, but 0x1a was rejected.
`derive-firmware-setup.py` executes all 256 parameter values for both relevant
firmware endpoints (512 cases). With mapping helpers explicitly mocked, EP0
accepts 1/2, 3/4, 0x0b/0x0c and 0x0f/0x10; EP3 accepts 0x0d/0x0e. It rejects
EP0 0x1a/0x1b. An explicit continuation preserved the accepted general buffer
and completed the remaining six supported region commands. All shared memory
remains allocated. No unsupported command was retried.

A bounded clock/route experiment started from the exact disconnected Switch3
defaults and NCO1 0x80308000 plus zero parameters. Programming/readback and exact
restoration passed. NCO control bits21:20 stayed 3 on readback; this is an
observation, not a complete interpretation of these bits or a measured clock.

A subsequent actual 4096-byte silence transfer on MCA1 endpoint42 passed:
configure ACK, submit ACK, tagged completion with 4096 bytes, and stop ACK.
MCA TX was stopped/flushed and the clock/route registers restored. Both speaker
amplifiers remained in reset, and USB remained responsive. This establishes a
basic muted DMA path, not audible playback, cyclic reliability, ALSA integration,
physical sample-rate accuracy, or coexistence with touch. Temporary live session
and recovery modules are still private development code pending consolidation.
The generic core's A7 activation block remains in place.
