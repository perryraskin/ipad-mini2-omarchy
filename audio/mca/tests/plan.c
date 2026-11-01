/* SPDX-License-Identifier: GPL-2.0-only OR MIT */
#include <assert.h>
#include <stdio.h>
#include "../j86-mca-plan.h"
int main(void)
{
 struct j86_mca_plan p;
 assert(j86_mca_identity(0x00010001,0x00800080));
 assert(!j86_mca_identity(1,0x00800080));
 assert(!j86_mca_identity(0x00020001,0x00800080));
 assert(!j86_mca_identity(0x00010001,0x00400080));
 assert(!j86_mca_identity(0x00010001,0x00800040));
 for (unsigned int master=0; master<2; master++) {
  assert(!j86_mca_plan(48000,2,16,master,&p));
  for (unsigned int i=0; i<J86_MCA_CONFIGURE_COUNT; i++)
   printf("%u configure %04x %08x\n",master,p.configure[i].offset,p.configure[i].value);
  for (unsigned int i=0; i<2; i++)
   printf("%u start %04x %08x\n",master,p.start[i].offset,p.start[i].value);
  for (unsigned int i=0; i<2; i++)
   printf("%u stop %04x %08x\n",master,p.stop[i].offset,p.stop[i].value);
  assert(p.endpoint==0x2a && p.frame_bytes==4);
  assert(p.timeout==0 && p.fifo_bytes==0xcc && p.trigger_bytes==0xac);
 }
 assert(j86_mca_plan(44100,2,16,0,&p)==-EINVAL);
 assert(j86_mca_plan(48000,1,16,0,&p)==-EINVAL);
 assert(j86_mca_plan(48000,2,32,0,&p)==-EINVAL);
 assert(j86_mca_plan(48000,2,16,2,&p)==-EINVAL);
 assert(j86_mca_plan(48000,2,16,0,0)==-EINVAL);
 return 0;
}
