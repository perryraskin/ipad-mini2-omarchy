# Mini 2 roadmap

Updated 11 November 2026. [Orchard/Omarchy v0.3.0 review](research/A7-UPDATE-2026-11-11.md). [New replication/source review](research/A7-UPDATE-2026-11-07.md)
and [ASP/UUID analysis](research/A7-UPDATE-2026-11-06.md). Physical order is unchanged.

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
   start the isolated audio owner inside the working desktop. Compare the newly
   published J72 MCA-v1/SmartIO and guarded runtime source before proposing a
   native J86 integration; six-command J72 setup is not our eight-command path.
5. **Internal-root research, disabled by default.** J72 internal-root reports make
   A7 storage plausible. Review the now-published J72 writable-ASP/recovery
   snapshots and independently establish the UUID-link fix; audit
   J86 firmware/DT/geometry and early-root resolution. Host-only identity checks
   are available now. A read-only hardware observer needs a separately reviewed
   candidate and recovery plan; it is not bundled into default boot.
6. **Internal installation only with explicit approval.** Verified backup and
   exact shrink minimum/layout first, then a reviewable plan for every write.
   Snapshot deletion/APFS resize/GPT edits/format/install are not authorized by
   this roadmap. Internal-root boot, charging and host-free startup are separate
   milestones. No Mini 2 installer or qualified GPU acceleration is claimed.

Community battery, guarded charging and USB reconnect code is now available for
review. J86 behavior remains unqualified; no charging profile, current limit or
autostart is copied. The J72 browser-load watchdog failure and stale readings
must inform future tests. These references do not reorder the physical queue.

Orchard v0.3.0 adds an exact-J86 experimental catalog/kernel target and a
preferred checkra1n entry, not a qualified RAM payload. A future port must pin
the checkout/catalog, preserve 4 KiB pages and private-input gates, build from
clean sources and qualify USB/desktop/touch before replacing known-good.
J85m/J86m/J87m are Mini 3. Generic suspend is source-level only on A7; audit
power domains, cpuidle and freezable pollers in a separate RAM candidate, last
in the hands-on order. Do not adopt Omarchy's idle-suspend policy. Installed
m1n1 boot entries do not solve A7 storage and require separately authorized
internal writes to create. No boot profile changes are warranted by this review.
