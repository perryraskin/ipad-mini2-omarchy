#!/usr/bin/env python3
"""Exercise actual stop callback against ACK/cancel reorderings and errors."""
import pathlib,subprocess,tempfile
root=pathlib.Path(__file__).resolve().parents[1];s=(root/'j86_pcm_native.c').read_text()
a=s.index('static int stop_dma(void)');b=s.index('static void run_playback',a)
shim='''#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#define TAG "test: "
#define pr_err(...) fprintf(stderr,__VA_ARGS__)
typedef uint64_t u64;typedef uint32_t u32;
#define EAGAIN 11
#define EPROTO 71
#define ETIMEDOUT 110
#define PERIOD 4096
#define BIT(x) (1U<<(x))
#define msecs_to_jiffies(x) (x)
#define time_before(a,b) ((a)<(b))
static unsigned long jiffies;
static unsigned int pending_slots,count,pos;
static u64 messages[8];
static int send_cmd(int a,int b,int c){assert(a==8&&b==15&&c==0);return 0;}
static int receive(u64 *v){++jiffies;if(pos==count)return -EAGAIN;*v=messages[pos++];return 0;}
static void usleep_range(int a,int b){(void)a;(void)b;}
static u64 msg(unsigned op,unsigned tag,unsigned param,u32 value){return ((u64)value<<32)|((u64)param<<24)|((u64)op<<16)|(tag<<8)|42;}
'''
test='''int main(void){
pending_slots=3;count=3;messages[0]=msg(0x65,15,0,8);messages[1]=msg(0x68,2,128,(u32)-32);messages[2]=msg(0x68,3,128,(u32)-32);
assert(stop_dma()==0&&pending_slots==0&&pos==3);
pending_slots=3;pos=0;count=4;messages[0]=msg(0x65,3,0,6);messages[1]=msg(0x68,2,128,4096);messages[2]=msg(0x68,3,128,(u32)-32);messages[3]=msg(0x65,15,0,8);
assert(stop_dma()==0&&pending_slots==0&&pos==4);
pending_slots=1;pos=0;count=1;messages[0]=msg(0x65,15,0,8);assert(stop_dma()==-ETIMEDOUT&&pending_slots==1);
pending_slots=1;pos=0;count=1;messages[0]=msg(0x68,3,128,(u32)-32);assert(stop_dma()==-EPROTO);
/* Idle tags are meaningless, including tags outside the descriptor set. */
for(unsigned t=0;t<256;++t){
 pending_slots=3;pos=0;count=5;
 messages[0]=msg(0x68,t,0,0);messages[1]=msg(0x65,15,0,8);
 messages[2]=msg(0x68,2,128,(u32)-32);messages[3]=msg(0x68,t,1,0);
 messages[4]=msg(0x68,3,128,(u32)-32);
 assert(stop_dma()==0&&pending_slots==0&&pos==5);
}
pending_slots=1;pos=0;count=2;messages[0]=msg(0x65,15,0,8);messages[1]=msg(0x68,2,0,0);
assert(stop_dma()==-ETIMEDOUT&&pending_slots==1);
pending_slots=0;pos=0;count=1;messages[0]=msg(0x68,15,0,0);
assert(stop_dma()==-ETIMEDOUT); /* idle is not a STOP ACK */
return 0;}
'''
with tempfile.TemporaryDirectory() as tmp:
 p=pathlib.Path(tmp);(p/'test.c').write_text(shim+s[a:b]+test)
 subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS: stop drains pending buffers before/after ACK and rejects missing/unowned completions')
