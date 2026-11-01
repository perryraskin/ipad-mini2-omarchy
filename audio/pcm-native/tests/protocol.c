/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include "../protocol.h"
#define MSG(ep,op,t,p,v) ((unsigned long long)(v)<<32 | (unsigned long long)(p)<<24 | (unsigned long long)(op)<<16 | (unsigned long long)(t)<<8 | (ep))
int main(void)
{
 assert(j86_ack_classify(MSG(42,0x65,15,0,8),15,8)==1);
 assert(j86_ack_classify(MSG(42,0x65,2,0,6),15,8)==0);
 assert(j86_ack_classify(MSG(42,0x65,3,0,6),15,8)==0);
 assert(j86_ack_classify(MSG(42,0x65,2,0,6),1,5)==-1);
 assert(j86_ack_classify(MSG(42,0x68,3,0x80,4096),15,8)==0);
 assert(j86_ack_classify(MSG(42,0x68,3,0,0),15,8)==0);
 assert(j86_ack_classify(MSG(42,0x68,3,0x81,4096),15,8)==-1);
 assert(j86_ack_classify(MSG(42,0x68,1,0x80,4096),15,8)==-1);
 assert(j86_ack_classify(MSG(42,0x68,2,0x80,1024),15,8)==-1);
 assert(j86_ack_classify(MSG(42,0x66,15,0,8),15,8)==-1);
 assert(j86_ack_classify(MSG(41,0x65,15,0,8),15,8)==-1);
 return 0;
}
