# Mini 2 roadmap

Updated 6 November 2026. [Community evidence and ASP/UUID analysis](research/A7-UPDATE-2026-11-06.md).

1. **Restore the known-good RAM desktop.** Inspect actual USB state first. If the
   isolated audio owner remains loaded, a fresh RAM boot is needed before touch
   startup. Use the latest source tooling with the qualified J86 payload, not an
   unqualified Orchard nightly. No new audio candidate is required for desktop.
2. **HDMI, then Bluetooth/wired inputs.** Follow [HANDS-ON-QUEUE.md](HANDS-ON-QUEUE.md).
   Prepare a self-contained RAM session before disconnecting a Mac-backed root.
   Confirm actual video and input behavior; USB detection alone is insufficient.
3. **Orientation, auto-rotation, then suspend.** Preserve that order. Sensor
   transport, shared hardware ownership and reliable wake still need qualification.
4. **Audio integration.** Speaker output and volume change are owner-confirmed;
   29 muted app/cleanup cycles passed. The subsequent queued-stop source fix is
   host-tested only. Physical keys, acoustic mute/channel separation and combined
   desktop/touch/Wi-Fi ownership remain separate checks, not reasons to silently
   start the isolated audio owner inside the working desktop.
5. **Internal-root research, disabled by default.** J72 internal-root reports make
   A7 storage plausible. Obtain the actual UUID-link/writable-ASP source; audit
   J86 firmware/DT/geometry and early-root resolution. Host-only identity checks
   are available now. A read-only hardware observer needs a separately reviewed
   candidate and recovery plan; it is not bundled into default boot.
6. **Internal installation only with explicit approval.** Verified backup and
   exact shrink minimum/layout first, then a reviewable plan for every write.
   Snapshot deletion/APFS resize/GPT edits/format/install are not authorized by
   this roadmap. Internal-root boot, charging and host-free startup are separate
   milestones. No Mini 2 installer or qualified GPU acceleration is claimed.
