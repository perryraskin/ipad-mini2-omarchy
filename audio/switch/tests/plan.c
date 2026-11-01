/* SPDX-License-Identifier: GPL-2.0-only OR MIT */
#include <assert.h>
#include <stdio.h>
#include "../j86-switch-plan.h"
int main(void)
{
 struct j86_switch_edge e;
 u32 defaults[J86_SWITCH_WORDS];
 j86_switch_defaults(defaults);
 printf("defaults");
 for(unsigned int i=0;i<J86_SWITCH_WORDS;i++) printf(" %08x",defaults[i]);
 puts("");
 for(unsigned int reverse=0;reverse<2;reverse++)
  for(unsigned int mode=0;mode<2;mode++)
   for(unsigned int lane=0;lane<2;lane++) {
    assert(!j86_switch_edge(reverse,mode,lane,&e));
    printf("%u%u%u",reverse,mode,lane);
    for(unsigned int i=0;i<J86_SWITCH_WORDS;i++) printf(" %08x",e.mask[i]);
    for(unsigned int i=0;i<J86_SWITCH_WORDS;i++) printf(" %08x",e.value[i]);
    puts("");
   }
 for(unsigned int master=0;master<2;master++) {
  assert(!j86_switch_tx_plan(master,defaults));
  printf("tx%u",master);
  for(unsigned int i=0;i<J86_SWITCH_WORDS;i++) printf(" %08x",defaults[i]);
  puts("");
 }
 assert(j86_switch_tx_plan(2,defaults)==-EINVAL);
 assert(j86_switch_tx_plan(0,NULL)==-EINVAL);
 assert(j86_switch_edge(2,0,0,&e)==-EINVAL);
 assert(j86_switch_edge(0,2,0,&e)==-EINVAL);
 assert(j86_switch_edge(0,0,2,&e)==-EINVAL);
 assert(j86_switch_edge(0,0,0,NULL)==-EINVAL);
 return 0;
}
