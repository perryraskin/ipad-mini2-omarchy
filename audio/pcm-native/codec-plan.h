/* SPDX-License-Identifier: GPL-2.0-only */
/* Caller supplies its own exact 40-byte J86 records. No calibration defaults. */
#ifndef J86_CODEC_PLAN_H
#define J86_CODEC_PLAN_H
struct op {unsigned char amp,reg,value,mask;};
struct j86_codec_plan {struct op revision[22],serial[32],boost[4],power[24],status[24];unsigned int nr;};
static void j86_codec_plan(const unsigned char *records,struct j86_codec_plan *p)
{
 unsigned int a,n,k=0,s=0,b=0,w=0,t=0;
 const unsigned char masks[]={0x7f,0xff,0x1c,0xff,0x3f,0xff,0x7f,0x9f};
 #define ADD(arr,idx,r,v,m) p->arr[idx++]=(struct op){a,r,v,m}
 for(a=0;a<2;++a){const unsigned char *c=records+20*a;
  ADD(revision,k,0,0x99,255);ADD(revision,k,0x45,0x3f,255);ADD(revision,k,0x46,c[16],255);
  ADD(revision,k,0x51,255,255);ADD(revision,k,0x59,10,255);ADD(revision,k,0x6b,32,255);
  if(c[18]){ADD(revision,k,0x54,c[18],255);}ADD(revision,k,0,0,255);
  if(c[17]){ADD(revision,k,0,0x99,255);ADD(revision,k,0x66,c[17],255);ADD(revision,k,0,0,255);}
  for(n=0x2d;n<0x32;++n){ADD(serial,s,n,128,255);}
  ADD(serial,s,0xd,3,255);ADD(serial,s,8,0x49,255);
  for(n=0x32;n<0x36;++n){ADD(serial,s,n,0,255);}
  ADD(serial,s,0x36,0x20+2*a,255);ADD(serial,s,0x38,128,255);ADD(serial,s,0x37,128,255);
  ADD(serial,s,0xb,0,64);ADD(serial,s,0xc,0,16);
  ADD(boost,b,0xb,c[1]&63,255);ADD(boost,b,0xc,c[2],3);
  ADD(power,w,7,0xf8,255);ADD(power,w,8,0x40,0xc0);ADD(power,w,9,c[0],255);ADD(power,w,0x10,0x19,255);
  ADD(power,w,0xf,0,16);ADD(power,w,0x11,0x1c,255);ADD(power,w,0xe,0xc4,0xcf);ADD(power,w,0x12,c[3],0xf0);
  for(n=0;n<4;++n){ADD(power,w,0x3a+n,c[12+n],255);}
  ADD(status,t,0x17,0x5a,255);ADD(status,t,0x18,c[19],255);ADD(status,t,0x17,0,255);
  for(n=0;n<8;++n){ADD(status,t,0x23+n,c[4+n],masks[n]);}ADD(status,t,0x11,0x14,255);
 }
 p->nr=k;
 #undef ADD
}
#endif
