# Mac-backed J86 apps

The verified root disk remains read-only on NBD2. A separate2GiB ext4 disk on
the Mac backs NBD3 and the OverlayFS application root. Apps run as `tablet`,
sharing the existing Wayland session and RAM home. This never accesses iPad
internal storage. App binaries/packages persist on the Mac; user settings in
RAM home do not survive reboot yet.

`python3 apps/start.py` checks exact board/kernel and module hashes, starts the
standard nbdkit backend in the existing local LimaVM, exposes a USB-peer-only
relay, mounts the overlay and starts a credential-checked local app service.
Official Arch Linux ARM package signatures remain required. Installs perform
`pacman -Syu --needed` in the isolated application root, avoiding partial Arch
upgrades. The base desktop root is not upgraded.

`python3 apps/stop.py` refuses to detach an active pacman transaction, terminates
only processes rooted in the application overlay, unmounts shared submounts and
disconnects only NBD3. The desktop remains running. `ipad-linux ios/detach` calls
this before tearing down the base desktop.

## Qualified in the running session

- Bidirectional relay stress: simultaneous16MiB each way with4KiB TCP send buffers.
- Official keyring initialized and populated; signed Galculator2.1.4-12 installed
  with required repository updates. Exit0. The actual calculator window rendered.
- More than1GiB of NBD writes completed. The application layer detached normally;
  offline `e2fsck -fn` passed all five passes with no errors.
- Remounted app layer retained the installed Galculator package and launched it.
- Native touch remainedstate2; original root stayed read-only.

The default10second request timeout was insufficient. Current120second timeout,
64KiB maximum requests, queue depth4 and bounded dirty writeback completed the
workload. The1GiB board reserves64MiB minimum free memory, with2MiB background
and8MiB foreground dirty limits. USB shell connections may time out briefly
during heavy writes; USB serial is the recovery channel. This is not yet a
claim that sustained interactive latency is good under installation load.

The relay drains request/reply directions independently. A single blocking
select/sendall loop is invalid when both TCP windows fill. Request timing logs
remain private. The experimental custom NBD server is not a production backend.

No installer menu should be enabled unless startup succeeds and the app service
socket exists. Failed overlay test disks are preserved privately; never reuse
one after an aborted package transaction as a known-good app filesystem.

If the installer terminal disconnects, the daemon keeps draining command output
and waits for the package process to finish. Delivery is bounded to2seconds
per socket write. The disconnected-client regression test verifies a child can
write1MiB and produce its completion receipt without a reader. Service requests
remain serialized; an abandoned terminal does not start a second transaction.


## Installer exposure and bounded transactions

Startup now leaves installs disabled. `apps/start.py --enable-installer` is the
explicit opt-in after write-path qualification; the menu additionally requires
its enable marker, the service socket and current health receipt. Launching
already installed apps does not require enabling installs. No updated service
has been deployed while USB is unavailable.

Each package request hides readiness before starting. A RAM transaction marker
survives failure; failed commands revoke installer enablement, and a new daemon
refuses an uncertain prior transaction. Never automatically remove that marker,
a pacman database lock or retry a failed transaction. Inspect processes and
qualify the separate app filesystem first. The physical queue includes this.

Requests have a5second total deadline. Output drains in8KiB chunks (including
newline-free output), with2second delivery bounds after a terminal disconnects.
A30minute userspace watchdog terminates/reaps the entire process group, preserving
uncertain state for review. Kernel uninterruptible I/O cannot be made safe by a
userspace timeout: the finite NBD timeout, bounded dirty writeback, separate Mac
disk and fail-closed installer gate remain necessary. No claim of zero stalls.
Linux integration tests exercise the real UNIX daemon request loop with synthetic
package/storage operations, including partial requests and uncertain restart.

Explicit installer enablement now requires a fresh5second daemon health handshake with storage fsync/readback; stale socket/readiness files alone cannot expose installs. Old daemons that lack the health command refuse enablement until deliberately deployed/restarted.

October31 live retest: signed swayimg5.7-1 installed with25 packages/upgrades
(about101MiB downloaded); pacman and the daemon returned exit0 and the
transaction marker cleared. The installed viewer rendered a PNG in the current
Wayland session. HTTPS via the Mac SOCKS proxy returned200. A USB-shell request
timed out during the large update, and Perry reported app-launch freezes with
two Firefox main processes and high memory/I/O pressure. Closing Firefox
restored available memory from126MiB to roughly350MiB. Installer exposure was
revoked again; sustained interactive install latency is not qualified.

The browser launcher now queues concurrent cold starts for30seconds before
allowing another Firefox invocation, retaining URL arguments for normal remote
forwarding. The profile disables speculative processes and first-run/new-tab
pages while retaining browser sandboxing and site isolation. Host and Linux
concurrency tests pass; live single-browser responsiveness remains to be checked.

## Audio2 diagnostic boundary (October 31)

A matching OverlayFS sidecar built for audio2 and its 221 live symbol exports
validated. It loaded and the Mac-backed app root mounted; startup health passed.
A larger fsync/readback test then failed with NBD3 receive errors and an ext4
journal abort. USB transfer settings were subsequently verified, but the bulk
write failure reproduced. This is not a qualified app-storage profile.
The app layer was detached; the failed Mac image was preserved separately.
A working copy's journal was repaired offline and all five e2fsck passes passed
before the second diagnostic. Neither image is a known-good qualification.
No internal iPad storage was accessed. Installer enablement is refused on audio2
even when explicitly requested. Diagnostic mounts require the separate
`--experimental-audio2-storage` flag. `build-overlay.sh` only builds the sidecar.
A raw USB TCP test passed simultaneous 16MiB each direction with matching hashes;
this does not qualify the kernel NBD write path or Lima forwarding.

## Current bounded audio2 write qualification

Subsequent isolation tests passed raw USB TCP (16MiB simultaneously each way),
a direct Mac RAM NBD server, and an independent OpenSSH tunnel to VM RAM NBD.
The tunnel alone did not fix larger-request writes to the app filesystem.
With 4KiB requests, queue depth2, no read-ahead, 512KiB background dirty and
2MiB foreground dirty bounds, the real app layer passed 16MiB fsync/readback
in 2.93s. Clean detach and all five read-only offline e2fsck passes passed;
after remount, the file hash matched. Native-wlan0 HTTPS returned200 and a
signature-checked Calculator reinstall completed exit0. A subsequent clean
detach and filesystem check passed after that package operation.

These are bounded qualifications, not a guarantee against all stalls. Earlier
failed images remain preserved privately. The initializer defaults to a hidden
installer; audio2 additionally requires `--experimental-audio2-storage`. Explicit
installer enablement now requires a private qualification receipt matching the
kernel and exact storage/service source hashes, plus the fresh daemon fsync
health handshake. This session's tested profile was explicitly enabled.
The public source release does not include a qualification receipt or disk.

The daemon refuses an install before creating any transaction marker when
MemAvailable is below192MiB. It asks the user to close Firefox/other apps and
retry. A live low-memory rejection and the Linux daemon integration test both
confirmed that no package transaction started. This does not weaken signatures,
remove site isolation, or alter the read-only base root. Firefox's 1GiB-board
scroll performance remains limited; Perry reports Calculator/window interaction
working but browser scrolling lagging.
