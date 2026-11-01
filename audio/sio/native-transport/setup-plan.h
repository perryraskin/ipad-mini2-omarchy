/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef J86_SETUP_PLAN_H
#define J86_SETUP_PLAN_H
/* Exact A7 supported setup. No newer SPI 0x1a/0x1b commands. */
struct j86_setup_command {unsigned char endpoint,tag,parameter;unsigned int value;};
static int j86_setup_plan(const unsigned long long address[4],struct j86_setup_command out[8])
{
 static const unsigned int sizes[]={0x4000,0x4000,0x8000,0x11000};
 static const unsigned int lengths[]={0x4000,0x4000,0xaaa,0x1040};
 static const unsigned char ep[]={0,3,0,0},tags[]={1,1,5,7},params[]={0xf,0xd,1,0xb};
 unsigned int i;
 if(!address||!out)return -22;
 for(i=0;i<4;++i){
  if(!address[i]||(address[i]&4095)||address[i]>(1ULL<<36)-sizes[i])return -22;
 }
 for(i=0;i<4;++i){
  out[2*i]=(struct j86_setup_command){ep[i],tags[i],params[i],address[i]>>12};
  out[2*i+1]=(struct j86_setup_command){ep[i],tags[i]+1,params[i]+1,lengths[i]};
 }
 return 0;
}
#endif
