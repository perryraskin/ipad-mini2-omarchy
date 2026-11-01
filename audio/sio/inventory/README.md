# Bounded SIO state inventory

Build-only: `bash audio/sio/inventory/build.sh`. No automatic module loader or DT
binding is provided. Exact J86, matching kernel release and 4KiB pages are required.

Only remap-enable (0x20) and CPU-control (0x28) are read. No mailbox, FIFO,
interrupt status, timestamp or DMA-address reads; no SIO writes. A fully-on
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
