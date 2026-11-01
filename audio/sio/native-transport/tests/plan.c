/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stddef.h>
#include "../setup-plan.h"
int main(void)
{
 unsigned long long a[]={0x100000,0x200000,0x300000,0x400000};
 struct j86_setup_command c[8];
 const unsigned char ep[]={0,0,3,3,0,0,0,0},tag[]={1,2,1,2,5,6,7,8},p[]={15,16,13,14,1,2,11,12};
 const unsigned int v[]={0x100,0x4000,0x200,0x4000,0x300,0xaaa,0x400,0x1040};
 unsigned int i;
 assert(j86_setup_plan(a,c)==0);
 for(i=0;i<8;++i){assert(c[i].endpoint==ep[i]);assert(c[i].tag==tag[i]);assert(c[i].parameter==p[i]);assert(c[i].value==v[i]);}
 a[0]=1;assert(j86_setup_plan(a,c)<0);
 a[0]=0;assert(j86_setup_plan(a,c)<0);
 a[0]=(1ULL<<36)-0x1000;assert(j86_setup_plan(a,c)<0);
 a[0]=~0ULL-4095;assert(j86_setup_plan(a,c)<0);
 a[0]=(1ULL<<36)-0x4000;assert(j86_setup_plan(a,c)==0);
 assert(j86_setup_plan(NULL,c)<0);assert(j86_setup_plan(a,NULL)<0);
 return 0;
}
