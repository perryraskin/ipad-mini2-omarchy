# Touch controls

The active RAM desktop uses an opt-in Labwc0.20.2 patch:
`LABWC_TOUCH_LONG_PRESS_MS=600`. A stationary single-finger hold becomes one
right-click. A short tap stays a left-click. Moving more than12logical pixels
cancels the hold and permits a drag; a second finger cancels hold detection.
Native touch down is deferred until release, movement or a second finger, so
client long-touch handling cannot activate first. Pointer capability remains
advertised while touch-only long-press mode is enabled. Pointer focus
is restored even when the cursor was already at that location. Device/window
removal clears timers and releases any emulated pressed button.

Actual synthetic touchscreen tests in the running desktop verified a calculator
button tap, title-bar hold opening the window menu, and corner drag resizing the
calculator. A Firefox event-probe page received only button2 pointer/mouse
events and contextmenu, with the actual browser menu visible and no VNC client
connected. Physical finger confirmation remains pending.

Window grab zones extend just outside the visible border:20logical pixels at
2x scale, with36logical-pixel corner regions. Drag just outside a window edge
or corner. These larger invisible targets do not cover application buttons.

The original `/usr/bin/labwc` remains in the read-only root. The candidate lives
only in RAM under `/run/j86-desktop/build/`. Startup selects it only when its
SHA256 matches the staged `active.sha256`; omitting that activation file restores
the stock compositor on the next session. The candidate has Xwayland disabled
because the base image does not ship the Xwayland binary/pkg-config metadata.

Build with `desktop/build.sh` after mounting the verified root **read-only** at
`/mnt/j86-sysroot` in the existing ARM64 Linux VM. Native build tools are Meson,
Ninja, GCC, pkg-config and wayland-scanner. The result is staged separately as
`labwc-rebuilt`; building does not replace or restart the active compositor.

October31 regression: Perry confirmed missed physical taps with the original
long-press candidate and reliable taps with stock Labwc. The candidate now
flushes a native touch frame after deferred down, before release; real-handler
tests pass. Perry then physically confirmed reliable quick taps and the
title-bar hold menu together. This revised binary is the active default. Do not treat the
old synthetic results as physical qualification.

`desktop/window-bar.qml` provides a separate bottom panel using the standard
wlr-foreign-toplevel protocol instead of the Hyprland-only upstream dock.
Every open window remains listed when minimized; tap to unminimize and activate.
The 48logical-pixel buttons scroll horizontally when the row fills. Perry
physically confirmed minimized-window restoration October31.

Window title buttons now use48logical-pixel width/height with2pixels of
vertical title padding through the RAM-home `themerc-override`. This keeps
controls finger-sized across Omarchy theme changes. Rendering is verified;
physical drag/resize qualification is pending. A landscape-sized viewer
retained a width beyond the portrait output, leaving controls off-screen;
portrait Terminal is being used to separate window geometry from touch input.
