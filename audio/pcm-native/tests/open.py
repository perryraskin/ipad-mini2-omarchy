#!/usr/bin/env python3
"""Exercise the actual PCM open callback with ALSA refinement return values."""
import pathlib,subprocess,tempfile,sys
root=pathlib.Path(__file__).resolve().parents[1]
s=(pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else root/'j86_pcm_native.c').read_text()
a=s.index('static int pcm_open(');b=s.index('static int pcm_close(',a)
shim='''#include <assert.h>
#include <stdbool.h>
#define EIO 5
#define SNDRV_PCM_HW_PARAM_PERIODS 1
#define WRITE_ONCE(x,y) ((x)=(y))
static int owner_lock,hardware=42,constraint_result;
static bool poisoned,handed_off,opened;
struct runtime {int hw;};
struct snd_pcm_substream {struct runtime *runtime;};
static struct snd_pcm_substream *stream;
static void mutex_lock(int *p){(void)p;}
static void mutex_unlock(int *p){(void)p;}
static int snd_pcm_hw_constraint_integer(struct runtime *r,int p){(void)r;(void)p;return constraint_result;}
'''
test='''int main(void){struct runtime r;struct snd_pcm_substream sub={&r};
for(int rc=0;rc<=1;rc++){stream=0;opened=false;constraint_result=rc;
assert(pcm_open(&sub)==0);assert(stream==&sub);assert(opened);assert(r.hw==42);}
stream=0;opened=false;constraint_result=-22;
assert(pcm_open(&sub)==-22);assert(!stream&&!opened);
constraint_result=1;poisoned=true;assert(pcm_open(&sub)==-EIO);assert(!stream&&!opened);
poisoned=false;handed_off=true;assert(pcm_open(&sub)==-EIO);assert(!stream&&!opened);
return 0;}
'''
with tempfile.TemporaryDirectory() as tmp:
 p=pathlib.Path(tmp);(p/'test.c').write_text(shim+s[a:b]+test)
 subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS: actual PCM open handles positive/zero ALSA success and rejects failed/poisoned handoffs')
