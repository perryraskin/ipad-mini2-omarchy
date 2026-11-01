# Bounded SIO state inventory

Build-only: `bash audio/sio/inventory/build.sh`. No automatic module loader or DT
binding is provided. Exact J86, matching kernel release and 4KiB pages are required.

Reads the six remap address/size words, remap-enable (0x20), CPU-control
(0x28), and non-consuming TX/RX status (0x1008/0x1020). Two consecutive
snapshots must agree. Never reads the message FIFO, interrupt status or
timestamp; no SIO writes. Keep address-bearing captures private. A fully-on
power domain is observed passively without acquiring/releasing a power reference.
A fully-off domain uses one balanced generic power reference. Transitional domain
states are refused. The full PMGR word must match on exit. Successful init returns
ECANCELED deliberately; require the explicit pass receipt, not insmod's exit alone.

Live October 31 audio2: domain 0x1f0000ff was already on, remap-enable was 1,
CPU-control was 0, and domain state was unchanged. The original off-only probe
refused ownership first. The revised passive diagnostic performed no power writes.
This is not firmware boot or DMA qualification. CPU_RUN clear does not grant
ownership of an enabled remap. Patch 0002 prevents the draft SIO driver from
replacing such a mapping. A reviewed mapping/queue/IRQ lease and complete cleanup
are needed before testing firmware boot; a reboot alone is not that proof.

The expanded live inventory found both mailboxes empty and disabled, with a
stable inherited mapping. A subsequent separate private READY-only experiment
received the expected firmware READY message, but failed power restoration.
The inventory then refused a transitional power-domain state. Do not retry boot
in that session. See `audio/sio/HANDOFF.md`; this does not qualify playback.
