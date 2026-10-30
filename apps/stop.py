#!/usr/bin/env python3
"""Detach only the separate Mac-backed app root, preserving the live desktop."""
import pathlib,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from sessionlib import network,network_checked

def stop():
 if network('test -e /mnt/omarchy/run/j86-apps-transaction.json && echo TRANSACTION').strip():raise RuntimeError('Transaction active or uncertain; inspect processes/storage before detaching.')
 # Never kill a package transaction midway through its database update.
 busy=network("for p in /proc/[0-9]*; do [ \"$(busybox readlink \"$p/root\" 2>/dev/null)\" != /mnt/j86-apps ] || { [ \"$(cat \"$p/comm\" 2>/dev/null)\" != pacman ] || echo PACMAN_ACTIVE; }; done")
 if 'PACMAN_ACTIVE' in busy:raise RuntimeError('Package transaction active; app layer was not detached.')
 network("for p in /proc/[0-9]*; do [ \"$(busybox readlink \"$p/root\" 2>/dev/null)\" != /mnt/j86-apps ] || kill -TERM \"${p##*/}\"; done")
 for _ in range(20):
  alive=network("for p in /proc/[0-9]*; do [ \"$(busybox readlink \"$p/root\" 2>/dev/null)\" != /mnt/j86-apps ] || echo \"${p##*/}\"; done")
  if not alive.strip():break
  time.sleep(.25)
 else:raise RuntimeError('App-root processes remain; refusing to unmount: '+alive)
 print(network_checked('''set -e
for n in dev/pts dev/shm dev proc sys run home tmp; do
 if grep -q " /mnt/j86-apps/$n " /proc/mounts; then umount "/mnt/j86-apps/$n"; fi
done
if grep -q ' /mnt/j86-apps ' /proc/mounts; then umount /mnt/j86-apps; fi
if grep -q ' /mnt/j86-apps-store ' /proc/mounts; then umount /mnt/j86-apps-store; fi
if [ -s /sys/block/nbd3/pid ]; then busybox nbd-client -d /dev/nbd3; fi
rm -f /mnt/omarchy/run/j86-apps.sock /mnt/omarchy/run/j86-apps-ready /mnt/omarchy/run/j86-apps-installer-enabled
if [ -f /mnt/omarchy/run/j86-apps-vm-before ]; then
 while read key value; do
  case "$key" in
   min_free_kbytes) echo "$value" > /proc/sys/vm/$key ;;
   dirty_bytes|dirty_background_bytes|dirty_ratio|dirty_background_ratio)
    if [ "$value" -gt 0 ]; then echo "$value" > /proc/sys/vm/$key; fi ;;
  esac
 done < /mnt/omarchy/run/j86-apps-vm-before
 rm /mnt/omarchy/run/j86-apps-vm-before
fi
echo APPS_LAYER_DETACHED''',timeout=60),end='')
if __name__=='__main__':stop()
