/* SPDX-License-Identifier: GPL-2.0-only OR MIT */
/* A7 MCA-v1 backend: pure register plans, never an MMIO executor.
 * Adaptation boundary for Orchard's ASoC/dmaengine front end. Only the exact
 * stock descriptor modeled by derive-mca.py is supported. Do not generalize
 * these words to arbitrary PCM formats, clocks or speaker configurations.
 */
#ifndef J86_MCA_PLAN_H
#define J86_MCA_PLAN_H
#ifdef __KERNEL__
#include <linux/types.h>
#include <linux/errno.h>
#else
#include <stdint.h>
#include <errno.h>
typedef uint32_t u32;
#endif
#define J86_MCA_WRITES 16
struct j86_mca_write { u32 offset, value; };
struct j86_mca_plan {
 struct j86_mca_write configure[J86_MCA_WRITES];
 struct j86_mca_write start[2];
 struct j86_mca_write stop[2];
 u32 mclk_hz, endpoint, transfer_control, timeout, frame_bytes;
};
/* External clock (slave) vs NCO1 requested at 12.288 MHz (master).
 * Parent rate and route are deliberately not derived from guessed clocks.
 * reset/flush require bounded busy-clear polls after writes 0 and 1.
 * TX stop is followed by a bounded bit0-clear poll at0x44; stock first
 * invokes the IRQ object callback. The plan does not emulate that callback.
 */
static inline int j86_mca_plan(unsigned int rate, unsigned int channels,
 unsigned int bits, unsigned int master, struct j86_mca_plan *p)
{
 static const struct j86_mca_write configure[J86_MCA_WRITES] = {
  {0x44,3}, {0x48,1}, {0x10,0}, {0x1c,0xd}, {0x30,0xd},
  {0x08,0x1010}, {0x20,0x002f0004}, {0x34,0x006f0004},
  {0x14,0}, {0x24,3}, {0x38,0xff}, {0x18,0x108},
  {0x2c,0x10a}, {0x10,1}, {0x40,0xb0003000}, {0x0c,0x0f107000}
 };
 unsigned int i;
 if (!p || rate != 48000 || channels != 2 || bits != 16 || master > 1)
  return -EINVAL;
 for (i=0; i<J86_MCA_WRITES; i++) p->configure[i]=configure[i];
 p->configure[11].value=master ? 0x208 : 0x108;
 p->configure[15].value=master ? 0x0f107005 : 0x0f107000;
 p->start[0]=(struct j86_mca_write){0x18, master ? 0x209 : 0x109};
 p->start[1]=(struct j86_mca_write){0x0c, master ? 0x0f107007 : 0x0f107002};
 p->stop[0]=(struct j86_mca_write){0x18,0};
 p->stop[1]=(struct j86_mca_write){0x44,1};
 p->mclk_hz=master ? 12288000 : 0;
 p->endpoint=0x2a; p->transfer_control=0x21; p->timeout=0xcc;
 p->frame_bytes=4; /* SIO parameter10; not the measured 128-word FIFO. */
 return 0;
}
#define J86_MCA_CONFIGURE_COUNT 16
#endif
