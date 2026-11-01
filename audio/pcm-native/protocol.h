/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef J86_PCM_PROTOCOL_H
#define J86_PCM_PROTOCOL_H
/* 1: expected ACK; 0: legal in-flight traffic; -1: reject.
 * Only STOP may overtake descriptor ACKs. Never accept arbitrary opcodes. */
static int j86_ack_classify(unsigned long long msg,unsigned char tag,unsigned char operation)
{
 unsigned char ep=msg,op=msg>>16,t=msg>>8,param=msg>>24;
 unsigned int value=msg>>32;
 if(ep!=42)return -1;
 if(op==0x65 && t==tag && value==operation)return 1;
 if(operation==8 && op==0x65 && (t==2||t==3) && value==6)return 0;
 if(op==0x68 && (t==2||t==3) && !(param&0x7f) &&
    ((param==0 && value==0)||(param==0x80 && value==4096)))return 0;
 return -1;
}
#endif
