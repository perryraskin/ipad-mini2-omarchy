/* SPDX-License-Identifier: GPL-2.0-only OR MIT */
#include <stdio.h>
#include <assert.h>
#include "../oscar/j86-oscar-rx.h"
static void emit(void *ctx,const u8 *data,unsigned int length)
{
 (void)ctx;
 for (unsigned int i=0;i<length;i++) printf("%02x",data[i]);
 putchar('\n');
}
int main(void)
{
 struct j86_oscar_rx r={0};
 u8 data[113];size_t n;
 while ((n=fread(data,1,sizeof(data),stdin))) {
  j86_oscar_feed(&r,data,n,emit,NULL);
  assert(r.used<256);
 }
 fprintf(stderr,"%u %u %u %u %u\n",r.good,r.bad_length,r.bad_checksum,r.discarded,r.used);
 return ferror(stdin) ? 1 : 0;
}
