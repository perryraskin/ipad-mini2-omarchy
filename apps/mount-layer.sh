#!/bin/sh
set -eu
[ "$(tr -d '\000' </proc/device-tree/model)" = 'Apple iPad mini 2 (Cellular)' ]
case "$(uname -r)" in
 7.0.12-gdfa4d4208131-dirty|7.0.12-j86-audio2) ;;
 *) echo 'No qualified module profile for kernel';exit 1 ;;
esac
grep -q ' /mnt/omarchy ext4 ro,' /proc/mounts
[ -d /sys/module/overlay ]
# This Mac-hosted app layer is separate from the verified read-only root.
[ ! -s /sys/block/nbd3/pid ] || { echo 'nbd3 already connected; inspect existing layer'; exit 1; }
busybox nbd-client -b 4096 -t 120 "$1" 10812 /dev/nbd3
for n in 1 2 3 4 5; do [ "$(cat /sys/block/nbd3/size)" = 4194304 ] && break; sleep 1; done
[ "$(cat /sys/block/nbd3/size)" = 4194304 ]
# Bound writes before mounting. Multi-megabyte writeback stalled the USB path
# in the first test. Allow slow filesystem commits under RAM pressure,
# while retaining a finite timeout and an independently accessible serial shell.
echo 4 > /sys/block/nbd3/queue/max_sectors_kb
# Network-backed storage must retain memory for the USB receive path. Bound
# dirty writeback on this 1GiB board rather than allowing the default20% burst.
mkdir -p /mnt/omarchy/run
if [ ! -f /mnt/omarchy/run/j86-apps-vm-before ]; then
 for key in min_free_kbytes dirty_bytes dirty_background_bytes dirty_ratio dirty_background_ratio; do
  echo "$key $(cat /proc/sys/vm/$key)"
 done > /mnt/omarchy/run/j86-apps-vm-before
fi
echo 65536 > /proc/sys/vm/min_free_kbytes
echo 524288 > /proc/sys/vm/dirty_background_bytes
echo 2097152 > /proc/sys/vm/dirty_bytes
echo 2 > /sys/block/nbd3/queue/nr_requests
echo 0 > /sys/block/nbd3/queue/read_ahead_kb
busybox blkid /dev/nbd3 | busybox grep 'LABEL="J86_APPS"'
mkdir -p /mnt/j86-apps-store /mnt/j86-apps /mnt/omarchy-base
if ! grep -q ' /mnt/omarchy-base ext4 ro,' /proc/mounts; then mount -t ext4 -o ro,noload /dev/nbd2 /mnt/omarchy-base; fi
mount -t ext4 -o noatime /dev/nbd3 /mnt/j86-apps-store
mkdir -p /mnt/j86-apps-store/upper /mnt/j86-apps-store/work
mount -t overlay overlay -o lowerdir=/mnt/omarchy-base,upperdir=/mnt/j86-apps-store/upper,workdir=/mnt/j86-apps-store/work /mnt/j86-apps
for name in dev proc sys; do mount -o bind "/$name" "/mnt/j86-apps/$name"; done
for name in run home tmp; do mount -o bind "/mnt/omarchy/$name" "/mnt/j86-apps/$name"; done
# Share the base session's RAM DNS resolver without modifying the base root.
mount -o bind /mnt/omarchy/etc/resolv.conf /mnt/j86-apps/etc/resolv.conf
# /dev/pts and /dev/shm are distinct submounts of the existing session.
mount -o bind /dev/pts /mnt/j86-apps/dev/pts
mount -o bind /dev/shm /mnt/j86-apps/dev/shm
echo APPS_LAYER_READY
