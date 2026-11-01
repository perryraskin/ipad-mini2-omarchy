/* Bounded ALSA exercise; defaults to silence, explicit --tone for listening. */
#include <alsa/asoundlib.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
static int set_control(snd_ctl_t *ctl,const char *name,long value)
{
 snd_ctl_elem_value_t *v;snd_ctl_elem_value_alloca(&v);
 snd_ctl_elem_value_set_interface(v,SND_CTL_ELEM_IFACE_MIXER);
 snd_ctl_elem_value_set_name(v,name);snd_ctl_elem_value_set_integer(v,0,value);
 int rc=snd_ctl_elem_write(ctl,v);if(rc<0)return rc;
 rc=snd_ctl_elem_read(ctl,v);if(rc<0)return rc;
 return snd_ctl_elem_value_get_integer(v,0)==value?0:-EIO;
}
/* A successful snd_pcm_drop/close does not prove the asynchronous worker stopped. */
static int kernel_result(void)
{
 const char *paths[]={"/sys/module/j86_pcm_native/parameters/result",
                      "/sys/module/j86_pcm_v2/parameters/result"};
 unsigned int i;int result;
 for(i=0;i<sizeof(paths)/sizeof(paths[0]);++i){
  FILE *f=fopen(paths[i],"r");if(!f)continue;
  int n=fscanf(f,"%d",&result);fclose(f);
  return n==1?result:-EIO;
 }
 return -ENODEV;
}
int main(int argc,char **argv)
{
 snd_pcm_t *pcm=NULL;snd_ctl_t *ctl=NULL;snd_pcm_hw_params_t *h;
 snd_pcm_uframes_t period=1024,buffer=4096;unsigned int rate=48000;
 int rc,dir=0,tone=argc>1&&!strcmp(argv[1],"--tone"),seconds=argc>2?atoi(argv[2]):1;
 unsigned int pos=0,total;short samples[2048];
 int volume_check=argc>1&&!strcmp(argv[1],"--volume-check");
 int left=argc>1&&!strcmp(argv[1],"--left"),right=argc>1&&!strcmp(argv[1],"--right");
 int volume_stage=-1;
 tone=tone||volume_check||left||right;
 if(volume_check)seconds=6;
 int prepare_only=argc>1&&!strcmp(argv[1],"--prepare-close");
 int drop=argc>1&&!strcmp(argv[1],"--drop");
 if(argc>1&&!tone&&!prepare_only&&!drop&&strcmp(argv[1],"--silence"))return 2;
 if(seconds<1||seconds>10)return 2;
 total=seconds*48000;
 if((rc=snd_ctl_open(&ctl,"j86",0))<0)goto out;
 if((rc=set_control(ctl,"Speaker Playback Switch",0))<0)goto out;
 if((rc=set_control(ctl,"Speaker Playback Volume",volume_check?40:60))<0)goto out;
 if((rc=snd_pcm_open(&pcm,"j86",SND_PCM_STREAM_PLAYBACK,0))<0)goto out;
 snd_pcm_hw_params_alloca(&h);snd_pcm_hw_params_any(pcm,h);
 #define SET(x) do{rc=(x);if(rc<0)goto out;}while(0)
 SET(snd_pcm_hw_params_set_access(pcm,h,SND_PCM_ACCESS_RW_INTERLEAVED));
 SET(snd_pcm_hw_params_set_format(pcm,h,SND_PCM_FORMAT_S16_LE));
 SET(snd_pcm_hw_params_set_channels(pcm,h,2));
 SET(snd_pcm_hw_params_set_rate_near(pcm,h,&rate,&dir));
 SET(snd_pcm_hw_params_set_period_size_near(pcm,h,&period,&dir));
 SET(snd_pcm_hw_params_set_buffer_size_near(pcm,h,&buffer));
 SET(snd_pcm_hw_params(pcm,h));
 if(rate!=48000||period!=1024||buffer!=4096){rc=-EINVAL;goto out;}
 SET(snd_pcm_prepare(pcm));
 if(prepare_only){rc=0;goto out;}
 if(tone)SET(set_control(ctl,"Speaker Playback Switch",1));
 while(pos<total){
  if(volume_check){
   int stage=pos/96000;
   if(stage!=volume_stage){
    SET(set_control(ctl,"Speaker Playback Volume",stage==0?40:60));
    SET(set_control(ctl,"Speaker Playback Switch",stage<2));
    volume_stage=stage;
   }
  }
  unsigned int n=total-pos<1024?total-pos:1024,j;unsigned int written=0;
  for(j=0;j<n;++j){
   unsigned int t=pos+j,ramp=t<total-1-t?t:total-1-t;
   int sample=tone?(int)lround(1000*sin(2*M_PI*500*t/48000.0)):0;
   if(ramp<240)sample=sample*(int)ramp/240;
   samples[j*2]=right?0:sample;samples[j*2+1]=left?0:sample;
  }
  while(written<n){snd_pcm_sframes_t r=snd_pcm_writei(pcm,samples+written*2,n-written);
   if(r<0){rc=(int)r;goto out;}if(!r){rc=-EIO;goto out;}written+=(unsigned int)r;
  }
  pos+=n;
 }
 if(drop)SET(snd_pcm_drop(pcm));else SET(snd_pcm_drain(pcm));rc=0;
out:
 if(ctl)set_control(ctl,"Speaker Playback Switch",0);
 if(pcm){int close_rc=snd_pcm_close(pcm);if(rc>=0&&close_rc<0)rc=close_rc;}
 if(rc>=0)rc=kernel_result();
 if(ctl)snd_ctl_close(ctl);
 if(rc<0){fprintf(stderr,"ALSA failed at frame %u: %s\n",pos,snd_strerror(rc));return 1;}
 printf("PASS: %u frames at48kHz, %s, %s/close and kernel status verified\n",pos,tone?"quiet500Hz":"muted silence",prepare_only?"prepare":drop?"drop":"drain");return 0;
}
