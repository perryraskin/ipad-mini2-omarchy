// SPDX-License-Identifier: GPL-2.0-only
/* Exact-J86 passive I2C2/reset/keepalive pin snapshot; no writes. */
#include <linux/io.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/utsname.h>
#include <generated/utsrelease.h>
static int __init probe_init(void)
{
 const unsigned int pins[]={100,101,114,161};
 void __iomem *base;
 unsigned int i;
 if(!of_machine_is_compatible("apple,j86") || PAGE_SIZE!=4096 ||
    strcmp(utsname()->release,UTS_RELEASE))return -ENODEV;
 base=ioremap(0x20e300000ULL,0x400);
 if(!base)return -ENOMEM;
 for(i=0;i<ARRAY_SIZE(pins);++i) {
  u32 a=readl(base+pins[i]*4),b=readl(base+pins[i]*4);
  pr_info("j86-amp-pin-inventory: gpio%u=%08x stable=%d\n",pins[i],a,a==b);
  if(a!=b){iounmap(base);return -EAGAIN;}
 }
 iounmap(base);
 pr_info("j86-amp-pin-inventory: PASS; no GPIO, amplifier or power writes\n");
 return -ECANCELED;
}
module_init(probe_init);
MODULE_LICENSE("GPL");
