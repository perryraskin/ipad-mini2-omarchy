# Inactive Mac-side checkpoint updates

There is no autonomous OTA service and no on-device installer. The explicit CLI
checks only `perryraskin/ipad-mini2-omarchy` GitHub source-checkpoint releases.
Downloads remain inactive. Updates change Mac workspace source files only;
no code executes, no services restart, no default RAM profile changes, and no
internal iPad storage is accessed. This is the notify-and-update fallback while
native networking, persistence and hardware drivers remain experimental.

## Check, download, review and apply

Run on the Mac, from the existing private RAM-boot workspace:

```sh
python3 updates/j86-update.py check
python3 updates/j86-update.py download --directory private-data/source-update-downloads
python3 updates/j86-update.py plan --workspace . --stage private-data/source-update-downloads/SOURCE_TAG
python3 updates/j86-update.py apply --workspace . --stage private-data/source-update-downloads/SOURCE_TAG
```

Replace SOURCE_TAG with the exact tag printed by check/download. Nothing is
scheduled or enabled by default. `check --tag SOURCE_TAG` and `download --tag
SOURCE_TAG` allow pinning an older checkpoint. Checkpoint releases are labeled
prerelease/source-only; they are not a claim of working hardware.

The first apply uses `source-release/SOURCE-MANIFEST.json` as its trusted local
baseline; alternatively supply `--baseline PATH_TO_INSTALLED_MANIFEST`. Subsequent
applies retain their own baseline under private-data. Every changed existing
file must match that baseline, or already match the new release. Local edits
and untracked conflicting files stop the entire plan before any writes. Public
README/BUILDING/HARDWARE files map to publication-docs in the private workspace;
LICENSE maps to the retained upstream license. Old source removals are not
automatic. Resolve local edits deliberately; never force around this check.

The source update serializes with `ipad-linux`'s controller lock. Do not apply
while builds or manual source edits are running. Existing root/app servers keep
their loaded code until explicitly restarted; update does not disturb their
connections. Live deployment/restarts belong to the physical checklist.

## Roll back source changes

```sh
python3 updates/j86-update.py rollback --workspace . --tag SOURCE_TAG
```

Changed files are backed up first under private-data/source-update-backups.
Rollback validates current and backup hashes, restores prior source/modes and
removes newly added sources. Later local edits block rollback. A process crash
leaves a prepared transaction that can be rolled back; the same tag cannot be
silently reapplied over its existing backup. This rollback does not recover a
running device or undo package transactions/firmware experiments.

## Release contents and integrity

The archive contains exactly the reviewed UTF-8 source manifest, plus that
manifest. It excludes firmware, NVRAM, calibration, disk images, payloads,
modules, credentials and device logs. HTTPS origins and redirect hosts are
restricted; downloads have size/time bounds. Archive and individual file hashes,
paths, types, duplicate names and expanded size are validated. No tar extraction
is delegated to a shell. Checksums establish integrity from this GitHub release;
they are not independent code-signing or hardware qualification.

Maintainers build from a clean committed source checkout:

```sh
python3 updates/build-release.py --tag SOURCE_TAG --output NEW_ASSET_DIRECTORY
```

Publish its checkpoint.json and source-checkpoint.tar.gz only after that commit's
CI passes. No automatic publish workflow or hardware activation is installed.

Private `7.0.12-j86-audio2` RAM payload/sidecars must still be built locally from
owner assets and qualified via DFU. Source updates do not rebuild or select them.
See [HANDS-ON-QUEUE.md](../HANDS-ON-QUEUE.md) for that handoff.
