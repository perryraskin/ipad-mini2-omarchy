/* SPDX-License-Identifier: GPL-2.0-only OR MIT */
/* Bounded receive parser only; unknown payloads are never sensor readings. */
#ifndef J86_OSCAR_RX_H
#define J86_OSCAR_RX_H
#ifdef __KERNEL__
#include <linux/types.h>
#include <linux/string.h>
#else
#include <stdint.h>
#include <stddef.h>
#include <string.h>
typedef uint8_t u8;
typedef uint16_t u16;
#endif
struct j86_oscar_rx {
 u8 data[256];
 unsigned int used, good, bad_length, bad_checksum, discarded;
};
typedef void (*j86_oscar_emit)(void *ctx, const u8 *frame, unsigned int length);
static inline void j86_oscar_drop(struct j86_oscar_rx *r, unsigned int n)
{
 memmove(r->data, r->data+n, r->used-n);
 r->used-=n;
 r->discarded+=n;
}
static inline void j86_oscar_feed(struct j86_oscar_rx *r, const u8 *data,
 size_t count, j86_oscar_emit emit, void *ctx)
{
 static const u8 magic[4]={'I','C','P','A'};
 size_t pos;
 for (pos=0; pos<count; pos++) {
  unsigned int i, length, sum;
  r->data[r->used++]=data[pos];
  for (;;) {
   unsigned int prefix=r->used<4 ? r->used : 4;
   if (memcmp(r->data,magic,prefix)) {
    j86_oscar_drop(r,1);
    if (r->used) continue;
    break;
   }
   if (r->used<6) break;
   length=r->data[5] ? r->data[5] : 256;
   if (length<14) { r->bad_length++;j86_oscar_drop(r,1);continue; }
   if (r->used<length) break;
   sum=0;
   for (i=0;i+1<length;i+=2) sum+=r->data[i] | (r->data[i+1]<<8);
   if (length&1) sum+=r->data[length-1];
   if ((u16)~sum) { r->bad_checksum++;j86_oscar_drop(r,1);continue; }
   r->good++;
   if (emit) emit(ctx,r->data,length);
   r->used-=length;
   memmove(r->data,r->data+length,r->used);
   if (!r->used) break;
  }
 }
}
#endif
