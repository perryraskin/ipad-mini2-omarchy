/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef J86_SIO_SESSION_H
#define J86_SIO_SESSION_H
#include <linux/types.h>
#include <linux/io.h>
struct device;
/* Single in-kernel handoff. The owner retains all allocations until RAM reboot.
 * Caller must not remap/reboot SIO, free its firmware, or release its resources.
 * RX IRQ is claimed and disabled; polling transport only in this revision.
 */
struct j86_sio_handoff {
 struct device *dma_device;
 void __iomem *sio;
 void __iomem *mca1;
};
int j86_sio_session_claim(struct j86_sio_handoff *handoff);
#endif
