#!/bin/sh
# Build only in the Linux VM's case-sensitive filesystem, never on host APFS.
set -eu
case "${1:-}" in spi1|pwm|state|startup|firmware|capture|native) name=$1;; *) echo 'usage: touch/build.sh spi1|pwm|state|startup|firmware|capture|native' >&2; exit 2;; esac
TASK=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
export J86_TASK_ROOT="$TASK" J86_PROBE_NAME="$name"
# Quote the path as data; Lima propagates these explicit environment variables.
limactl shell j86-build env "J86_TASK_ROOT=$TASK" "J86_PROBE_NAME=$name" bash -c '
set -eu
probe="$J86_PROBE_NAME-probe"
filename="j86_${J86_PROBE_NAME}_probe"
if [ "$J86_PROBE_NAME" = native ]; then probe=native; filename=j86_touch; fi
mod="$HOME/j86-modules/$probe"
mkdir -p "$mod"
cp "$J86_TASK_ROOT/touch/$probe/${filename}.c" "$J86_TASK_ROOT/touch/$probe/Makefile" "$mod/"
make -C "$HOME/j86-kernel" ARCH=arm64 M="$mod" KBUILD_MODPOST_WARN=1 KCFLAGS=-Werror modules > "$J86_TASK_ROOT/touch/$probe/build.log" 2>&1
cp "$mod/${filename}.ko" "$J86_TASK_ROOT/touch/$probe/"
'
