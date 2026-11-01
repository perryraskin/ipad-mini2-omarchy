#!/usr/bin/env python3
"""Exercise actual close/free/sync-stop callbacks when the worker is still queued."""
import pathlib,subprocess,tempfile,sys
root=pathlib.Path(__file__).resolve().parents[1]
source=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else root/'j86_pcm_native.c'
s=source.read_text()
def function(name):
 a=s.index('static int '+name+'(');b=s.index('{',a);depth=1;i=b+1
 while depth:
  depth+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[a:i]
shim='''#include <stdbool.h>
#include <stddef.h>
struct snd_pcm_substream { int unused; };
static bool running,prepared,poisoned,opened,pending,dma_active;
static int result,playback_work,cleanup_count;
static struct snd_pcm_substream *stream;
#define WRITE_ONCE(x,v) ((x)=(v))
/* Cancel removes a queued job; flush runs its cleanup before returning. */
void cancel_work_sync(int *work){(void)work;pending=false;}
void flush_work(int *work){(void)work;if(pending){if(running)result=-1;dma_active=false;pending=false;++cleanup_count;}}
int restore_hw(void){return 0;}
void snd_pcm_set_runtime_buffer(struct snd_pcm_substream *s,void *p){(void)s;(void)p;}
'''
body='\n'.join(function(n) for n in ['pcm_close','pcm_free','pcm_sync_stop'])
test='''int main(void){
 struct snd_pcm_substream s={0};
 int (*callbacks[])(struct snd_pcm_substream *)={pcm_close,pcm_free,pcm_sync_stop};
 for(unsigned i=0;i<3;i++){
  running=i!=2;prepared=false;poisoned=false;opened=true;stream=&s;
  pending=true;dma_active=true;cleanup_count=0;result=0;
  if(callbacks[i](&s)||pending||dma_active||cleanup_count!=1||result)return 1;
  /* A second stop on an already retired worker must not repeat cleanup. */
  if(callbacks[i](&s)||cleanup_count!=1)return 2;
 }
 return 0;
}
'''
with tempfile.TemporaryDirectory() as tmp:
 p=pathlib.Path(tmp);(p/'test.c').write_text(shim+body+test)
 subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-parameter',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS: queued playback cleanup runs exactly once before close/free/sync-stop return')
