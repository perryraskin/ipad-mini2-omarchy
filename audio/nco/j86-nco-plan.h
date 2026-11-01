/* SPDX-License-Identifier: GPL-2.0-only OR MIT */
/* Fixed-format offline A7 NCO1 primary-parent plan; never executes MMIO. */
#ifndef J86_NCO_PLAN_H
#define J86_NCO_PLAN_H
#include "../mca/j86-mca-plan.h"
#ifndef __KERNEL__
typedef uint64_t u64;
#endif
struct j86_nco_plan { struct j86_mca_write writes[6]; };
static inline int j86_nco_mclk_plan(u32 parent_hz, u32 rate, struct j86_nco_plan *p)
{
 u64 numerator=parent_hz,denominator=1,base,div,remainder;
 u32 state=0x7ff,coarse,encoded,inc1,inc2;
 if (!p || rate!=12288000 || !parent_hz) return -EINVAL;
 /* Exact stock rational special case; this is not a measured parent rate. */
 if (parent_hz==342857142) { numerator=2400000000ULL;denominator=7; }
 base=denominator*rate;
 if (numerator<6*base || numerator>4095*base) return -ERANGE;
 div=2*numerator/base;remainder=2*numerator-div*base;
 coarse=(u32)(div/4)-3;
 while (coarse--) state=(state<<1)^((state&0x400) ? 0xa01 : 0);
 encoded=(state<<2)|((u32)div&3);
 inc1=(u32)remainder;inc2=inc1-(u32)base;
 p->writes[0]=(struct j86_mca_write){0x1000,0};
 p->writes[1]=(struct j86_mca_write){0x1004,encoded};
 p->writes[2]=(struct j86_mca_write){0x1008,inc1};
 p->writes[3]=(struct j86_mca_write){0x100c,inc2};
 p->writes[4]=(struct j86_mca_write){0x1010,(inc1^0x80000000U)-(u32)base};
 p->writes[5]=(struct j86_mca_write){0x1000,0x80001000};
 return 0;
}
/* The stock writer polls control bit30 before parameter writes. A future
 * executor requires a timeout, proven parent selection/global gate ownership,
 * channel-state preservation and restoration. None is provided here. */
#endif
