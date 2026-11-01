/* RAM-session mixer control. No PCM stream, firmware or storage access. */
#include <alsa/asoundlib.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static int control(snd_ctl_t *ctl,const char *name,long *value,int write)
{
 snd_ctl_elem_value_t *v;snd_ctl_elem_value_alloca(&v);
 snd_ctl_elem_value_set_interface(v,SND_CTL_ELEM_IFACE_MIXER);
 snd_ctl_elem_value_set_name(v,name);
 if(write){int r;snd_ctl_elem_value_set_integer(v,0,*value);r=snd_ctl_elem_write(ctl,v);if(r<0)return r;}
 int r=snd_ctl_elem_read(ctl,v);if(r<0)return r;
 long actual=snd_ctl_elem_value_get_integer(v,0);
 if(write&&actual!=*value)return -EIO;
 *value=actual;return 0;
}
int main(int argc,char **argv)
{
 snd_ctl_t *ctl=NULL;snd_ctl_card_info_t *info;long volume=30,on=0;int rc;
 int status=argc==2&&!strcmp(argv[1],"status");
 int mute=argc==2&&!strcmp(argv[1],"mute");
 int enable=argc==3&&!strcmp(argv[1],"enable");
 if(!status&&!mute&&!enable)return 2;
 if(enable){char *end;volume=strtol(argv[2],&end,10);if(!*argv[2]||*end||volume<0||volume>60)return 2;}
 rc=snd_ctl_open(&ctl,"j86",0);if(rc<0)goto out;
 snd_ctl_card_info_alloca(&info);rc=snd_ctl_card_info(ctl,info);if(rc<0)goto out;
 if(strcmp(snd_ctl_card_info_get_id(info),"J86Native")){rc=-ENODEV;goto out;}
 if(enable){rc=control(ctl,"Speaker Playback Volume",&volume,1);if(rc<0)goto out;on=1;}
 rc=control(ctl,"Speaker Playback Switch",&on,!status);if(rc<0)goto out;
 rc=control(ctl,"Speaker Playback Volume",&volume,0);if(rc<0)goto out;
 printf("speaker_switch=%ld volume=%ld dB=%ld\n",on,volume,volume-60);
out:
 if(ctl)snd_ctl_close(ctl);
 if(rc<0){fprintf(stderr,"Mixer: %s\n",snd_strerror(rc));return 1;}
 return 0;
}
