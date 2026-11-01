/* SPDX-License-Identifier: GPL-2.0-only OR MIT */
/* Offline edge encoder only. Not a graph router or an MMIO programming plan. */
#ifndef J86_SWITCH_PLAN_H
#define J86_SWITCH_PLAN_H
#include "../mca/j86-mca-plan.h"
#define J86_SWITCH_WORDS 20
struct j86_switch_edge { u32 mask[J86_SWITCH_WORDS], value[J86_SWITCH_WORDS]; };
static inline void j86_switch_defaults(u32 *words)
{
 unsigned int i;
 for (i=0;i<J86_SWITCH_WORDS;i++) words[i]=i<14 ? 0x181818 : i==14 ? 0x18 : 0;
}
/* Exact aud1/pin1 pair only. mode and lane are stock encoder arguments;
 * their physical direction/clock meaning remains unqualified. */
static inline int j86_switch_edge(unsigned int reverse, unsigned int mode,
 unsigned int lane, struct j86_switch_edge *e)
{
 unsigned int i, index=reverse ? 1 : 6, select=reverse ? 1 : 9;
 if (!e || reverse>1 || mode>1 || lane>1) return -EINVAL;
 for (i=0;i<J86_SWITCH_WORDS;i++) e->mask[i]=e->value[i]=0;
 if (reverse) {
  e->mask[16]=e->value[16]=mode ? 1 : 0x10;
 }
 if (mode) {
  e->mask[index]|=0x1f;e->value[index]|=select;
  if (!reverse) e->mask[16]|=1;
 } else {
  unsigned int shift=lane ? 16 : 8;
  e->mask[index]|=0x1fU<<shift;e->value[index]|=select<<shift;
 }
 return 0;
}
#endif
