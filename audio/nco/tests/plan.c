/* SPDX-License-Identifier: GPL-2.0-only OR MIT */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include "../j86-nco-plan.h"
int main(int argc,char **argv)
{
 struct j86_nco_plan p;
 assert(j86_nco_mclk_plan(0,12288000,&p)==-EINVAL);
 assert(j86_nco_mclk_plan(342857142,48000,&p)==-EINVAL);
 assert(j86_nco_mclk_plan(24000000,12288000,&p)==-ERANGE);
 assert(j86_nco_mclk_plan(342857142,12288000,NULL)==-EINVAL);
 if (argc==2) {
  char *end;unsigned long parent;
  errno=0;parent=strtoul(argv[1],&end,10);
  if (errno || *end || !*argv[1] || parent>UINT32_MAX || j86_nco_mclk_plan((u32)parent,12288000,&p)) return 2;
  for(unsigned int i=0;i<6;i++) printf("%04x %08x\n",p.writes[i].offset,p.writes[i].value);
 } else {
  const u32 parents[]={96000000,192000000,240000000,342857142,400000000,600000000};
  for(unsigned int i=0;i<sizeof(parents)/sizeof(*parents);i++) assert(!j86_nco_mclk_plan(parents[i],12288000,&p));
  puts("NCO fixed-format input guards passed; no hardware accesses");
 }
 return 0;
}
