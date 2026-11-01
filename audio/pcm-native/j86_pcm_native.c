// SPDX-License-Identifier: GPL-2.0-only
/* Experimental fixed-format J86 ALSA PCM. RAM-only, opt-in, muted by default.
 * SIO packet layout adapted from Orchard apple-sio-dma; exact A7 startup is
 * retained by the exclusively handed-off live session. No module unload.
 */
#include <linux/delay.h>
#include <linux/dma-mapping.h>
#include <linux/io.h>
#include <linux/ioport.h>
#include <linux/iopoll.h>
#include <linux/module.h>
#include <linux/workqueue.h>
#include <sound/core.h>
#include <sound/control.h>
#include <sound/pcm.h>
#include <sound/pcm_params.h>
#include <sound/tlv.h>
#include "../sio/transport/j86-sio-transport.h"
#include <linux/firmware.h>
#include <linux/hex.h>
#include <linux/utsname.h>
#include <generated/utsrelease.h>
#include <crypto/sha2.h>
#include <linux/mutex.h>
#include "protocol.h"
#include "../nco/j86-nco-plan.h"
#include "../switch/j86-switch-plan.h"
#include "amp-support.h"
#define PERIOD 4096U
#define PERIODS 4U
#define BUFFER (PERIOD*PERIODS)
#define TAG "j86-pcm-native: "
static DEFINE_MUTEX(owner_lock);
static bool allow_pcm;
module_param(allow_pcm,bool,0400);
static int result=-EPERM;
module_param(result,int,0400);
static unsigned long periods_done;
module_param(periods_done,ulong,0400);
static unsigned int starts,stops;
module_param(starts,uint,0400);
module_param(stops,uint,0400);
static struct j86_sio_transport transport;
static struct snd_card *card;
static struct snd_pcm_substream *stream;
static struct snd_dma_buffer pcm_buf;
static struct work_struct playback_work;
static struct workqueue_struct *playback_queue;
static bool dma_submitted;
static unsigned int phase;
module_param(phase,uint,0400);
static bool running,poisoned,opened,prepared,handed_off;
static unsigned int hw_pos;
static int volume=30,speaker_on; /* -30dB default; switch off */
static void __iomem *nco,*sw,*pins;
static bool nclaim,sclaim,clock_changed,mca_changed,amp_attempted;
static u32 saved[5],defaults[20];
static struct j86_mca_plan mp;
static int applied_volume=-1,applied_switch=-1;
static int send_cmd(u8 op,u8 tag,u32 value)
{
 u32 s;void __iomem *sio=transport.owner.sio;
 int rc=readl_poll_timeout(sio+0x1008,s,(s&BIT(17))||(s&GENMASK(19,18)),10,200000);
 if(rc)return rc;
 if(s&GENMASK(19,18))return -EIO;
 dma_wmb();writeq(((u64)value<<32)|(op<<16)|(tag<<8)|42,sio+0x1010);return 0;
}
static int receive(u64 *message)
{
 u32 s=readl(transport.owner.sio+0x1020);
 if(s&GENMASK(19,18))return -EIO;
 if(s&BIT(17))return -EAGAIN;
 *message=readq(transport.owner.sio+0x1038);dma_rmb();
 if((u8)*message!=42)return -EPROTO;
 if((u8)(*message>>16)==0x66||(u8)(*message>>16)==0x6a)return -EIO;
 return 0;
}
static int ack(u8 tag,u8 operation)
{
 unsigned long deadline=jiffies+msecs_to_jiffies(500);
 do{
  u64 msg;int r=receive(&msg);
  if(r==-EAGAIN){usleep_range(50,100);continue;}
  if(r)return r;
  r=j86_ack_classify(msg,tag,operation);
  if(r==1)return 0;
  if(r<0){pr_err(TAG "unexpected ACK op=%02x tag=%02x param=%02x value=%08x while waiting op=%02x tag=%02x\n",
   (unsigned int)((msg>>16)&255),(unsigned int)((msg>>8)&255),(unsigned int)((msg>>24)&255),(unsigned int)(msg>>32),operation,tag);return -EPROTO;}
 }while(time_before(jiffies,deadline));
 return -ETIMEDOUT;
}
static int idle(void __iomem *base)
{u32 v;return readl_poll_timeout(base,v,!(v&BIT(30)),10,10000);}
static int setup_hw(void)
{
 struct j86_nco_plan np;u32 route[20],value;int i,rc;void __iomem *mca=transport.owner.mca1;
 nco=sw=pins=NULL;nclaim=sclaim=clock_changed=mca_changed=amp_attempted=false;
 applied_volume=applied_switch=-1;
 if(!request_mem_region(0x20e012000ULL,0x1000,"j86-pcm"))return -EBUSY;
 nclaim=true;
 if(!request_mem_region(0x20a003000ULL,0x1000,"j86-pcm"))return -EBUSY;
 sclaim=true;
 nco=ioremap(0x20e012000ULL,0x1000);sw=ioremap(0x20a003000ULL,0x1000);pins=ioremap(0x20e300000ULL,0x400);
 if(!nco||!sw||!pins)return -ENOMEM;
 if((readl(pins+456)&0x6f)!=2||(readl(pins+644)&0x6f)!=2)return -EBUSY;
 if(!j86_mca_identity(readl(mca),readl(mca+4))||(readl(mca+0x18)&1))return -EBUSY;
 j86_mca_plan(48000,2,16,1,&mp);j86_nco_mclk_plan(342857142,12288000,&np);
 j86_switch_defaults(defaults);j86_switch_tx_plan(1,route);
 for(i=0;i<5;++i)saved[i]=readl(nco+4*i);
 if(saved[0]!=0x80308000||saved[1]||saved[2]||saved[3]||saved[4])return -EBUSY;
 for(i=0;i<20;++i)if(readl(sw+4*i)!=defaults[i])return -EBUSY;
 clock_changed=true;
 for(i=0;i<6;++i){rc=idle(nco);if(rc)return rc;writel(np.writes[i].value,nco+np.writes[i].offset-0x1000);}
 rc=idle(nco);if(rc)return rc;
 for(i=0;i<20;++i)writel(route[i],sw+4*i);
 mca_changed=true;
 for(i=0;i<J86_MCA_CONFIGURE_COUNT;++i){
  writel(mp.configure[i].value,mca+mp.configure[i].offset);
  if(i==1){rc=readl_poll_timeout(mca+0x48,value,!(value&1),10,10000);if(rc)return rc;}
 }
 amp_attempted=true;return amps_on();
}
static int restore_hw(void)
{
 int r=0,i;u32 v;void __iomem *mca=transport.owner.mca1;
 if(amp_attempted)r=amps_off();
 if(mca_changed){
  writel(0,mca+0x18);writel(1,mca+0x44);
  if(readl_poll_timeout(mca+0x44,v,!(v&1),10,10000))r=-EIO;
 }
 if(clock_changed){
  for(i=0;i<20;++i)writel(defaults[i],sw+4*i);
  writel(0,nco);
  if(idle(nco))r=-EIO;
  else {
   int nr=0;
   for(i=1;i<5;++i){writel(saved[i],nco+4*i);if(idle(nco)){nr=-EIO;break;}}
   if(!nr){writel(saved[0],nco);if(idle(nco))nr=-EIO;}
   if(nr)r=nr;
  }
  for(i=0;i<5;++i)if(readl(nco+4*i)!=saved[i])r=-EIO;
  for(i=0;i<20;++i)if(readl(sw+4*i)!=defaults[i])r=-EIO;
 }
 if(pins&&((readl(pins+456)&0x6f)!=2||(readl(pins+644)&0x6f)!=2))r=-EIO;
 if(r)return r; /* retain claims on an unverified restore */
 if(pins)iounmap(pins);
 if(sw)iounmap(sw);
 if(nco)iounmap(nco);
 if(sclaim)release_mem_region(0x20a003000ULL,0x1000);
 if(nclaim)release_mem_region(0x20e012000ULL,0x1000);
 return 0;
}
static int apply_mixer(void)
{
 int a,r,v=READ_ONCE(volume),on=READ_ONCE(speaker_on);
 if(v==applied_volume&&on==applied_switch)return 0;
 for(a=0;a<2;++a){r=wr(a,0x10,on?(u8)(2*(v-60)):0x19,255);if(r)return r;}
 applied_volume=v;applied_switch=on;return 0;
}
static int submit(unsigned int slot,unsigned int period)
{
 u32 *h=(u32 *)transport.desc0+(8+slot*8)*3;
 dma_addr_t a=pcm_buf.addr+period*PERIOD;
 memset(h,0,7*12);h[15]=1;h[18]=lower_32_bits(a);h[19]=upper_32_bits(a);h[20]=PERIOD;
 return send_cmd(6,2+slot,8+slot*8);
}
static void run_playback(struct work_struct *work)
{
 unsigned int index[2]={0,1},next=2,expected=0;int rc=0,stoprc;
 unsigned long deadline;struct snd_pcm_substream *s=READ_ONCE(stream);
 WRITE_ONCE(phase,3);
 deadline=jiffies+msecs_to_jiffies(500);
 while(READ_ONCE(running)){
  u64 msg;u8 op,tag,param;unsigned int slot;
  rc=receive(&msg);
  if(rc==-EAGAIN){
   if(time_after_eq(jiffies,deadline)){rc=-ETIMEDOUT;break;}
   usleep_range(50,100);continue;
  }
  if(rc)break;
  op=msg>>16;tag=msg>>8;param=msg>>24;
  if(op==0x65){if((tag!=2&&tag!=3)||(u32)(msg>>32)!=6){rc=-EPROTO;break;}continue;}
  if(op!=0x68){rc=-EPROTO;break;}
  if(!(param&0x80))continue;
  if(tag!=2&&tag!=3){rc=-EPROTO;break;}
  slot=tag-2;
  if(index[slot]!=expected||(u32)(msg>>32)!=PERIOD){rc=-EPROTO;break;}
  expected=(expected+1)%PERIODS;WRITE_ONCE(hw_pos,expected*(PERIOD/4));++periods_done;
  snd_pcm_period_elapsed(s);
  if(!READ_ONCE(running)){rc=0;break;}
  rc=apply_mixer();if(rc)break;
  index[slot]=next;next=(next+1)%PERIODS;
  rc=submit(slot,index[slot]);if(rc)break;
  deadline=jiffies+msecs_to_jiffies(500);
 }
 if(!READ_ONCE(running)&&rc==-EAGAIN)rc=0;
 /* Stop DMA before releasing any backing storage (which is retained anyway). */
 if(amp_attempted){int a;for(a=0;a<2;++a)if(bus)wr(a,0x10,0x19,255);}
 WRITE_ONCE(phase,4);
 if(dma_submitted){stoprc=send_cmd(8,15,0);if(!stoprc)stoprc=ack(15,8);if(stoprc){poisoned=true;if(!rc)rc=stoprc;}}
 stoprc=prepared?restore_hw():0;prepared=false;if(stoprc){poisoned=true;if(!rc)rc=stoprc;}
 dma_submitted=false;
 ++stops;WRITE_ONCE(result,rc);WRITE_ONCE(phase,5);
 if(rc){pr_err(TAG "stream failed %d poisoned=%d; amps reset\n",rc,poisoned);if(READ_ONCE(running))snd_pcm_stop_xrun(s);}
 WRITE_ONCE(running,false);
}
static const struct snd_pcm_hardware hardware={
 .info=SNDRV_PCM_INFO_INTERLEAVED|SNDRV_PCM_INFO_MMAP|SNDRV_PCM_INFO_MMAP_VALID|SNDRV_PCM_INFO_BLOCK_TRANSFER,
 .formats=SNDRV_PCM_FMTBIT_S16_LE,.rates=SNDRV_PCM_RATE_48000,.rate_min=48000,.rate_max=48000,
 .channels_min=2,.channels_max=2,.buffer_bytes_max=BUFFER,
 .period_bytes_min=PERIOD,.period_bytes_max=PERIOD,.periods_min=PERIODS,.periods_max=PERIODS,
};
static int pcm_open(struct snd_pcm_substream *s)
{
 int rc;
 mutex_lock(&owner_lock);
 if(poisoned||handed_off){rc=-EIO;goto out;}
 s->runtime->hw=hardware;
 rc=snd_pcm_hw_constraint_integer(s->runtime,SNDRV_PCM_HW_PARAM_PERIODS);
 if(!rc){WRITE_ONCE(stream,s);WRITE_ONCE(opened,true);}
out:mutex_unlock(&owner_lock);return rc;
}
static int pcm_close(struct snd_pcm_substream *s)
{WRITE_ONCE(running,false);cancel_work_sync(&playback_work);if(prepared){int r=restore_hw();if(r){poisoned=true;WRITE_ONCE(result,r);}prepared=false;}WRITE_ONCE(stream,NULL);WRITE_ONCE(opened,false);return 0;}
static int pcm_params(struct snd_pcm_substream *s,struct snd_pcm_hw_params *p)
{
 if(params_buffer_bytes(p)!=BUFFER||params_period_bytes(p)!=PERIOD)return -EINVAL;
 snd_pcm_set_runtime_buffer(s,&pcm_buf);s->runtime->dma_bytes=BUFFER;return 0;
}
static int pcm_free(struct snd_pcm_substream *s)
{WRITE_ONCE(running,false);cancel_work_sync(&playback_work);if(prepared){int r=restore_hw();if(r){poisoned=true;WRITE_ONCE(result,r);}prepared=false;}snd_pcm_set_runtime_buffer(s,NULL);return 0;}
static int pcm_prepare(struct snd_pcm_substream *s)
{
 int rc;
 WRITE_ONCE(running,false);cancel_work_sync(&playback_work);
 if(poisoned||handed_off)return -EIO;
 if(prepared){rc=restore_hw();prepared=false;if(rc){poisoned=true;return rc;}}
 rc=setup_hw();if(rc){if(restore_hw())poisoned=true;result=rc;return rc;}
 prepared=true;WRITE_ONCE(hw_pos,0);WRITE_ONCE(result,0);return 0;
}
/* PCM is nonatomic: START may wait for bounded mailbox ACKs. Complete the
 * startup before returning, so ALSA does not count scheduler/mailbox delay as
 * already-played audio. The worker only services an already-started stream. */
static int pcm_trigger(struct snd_pcm_substream *s,int cmd)
{
 int rc,stoprc;u32 *rec=transport.desc0;
 switch(cmd){
 case SNDRV_PCM_TRIGGER_START:
  if(poisoned||handed_off||!prepared)return -EIO;
  WRITE_ONCE(phase,1);++starts;dma_submitted=false;
  memset(rec,0,24*12);rec[0]=0x21;rec[2]=0xcc;rec[3]=0xac;rec[4]=192;rec[6]=4;
  rc=send_cmd(5,1,0);if(rc)goto fail;rc=ack(1,5);if(rc)goto fail;
  dma_submitted=true; /* even a failed submit may have reached the firmware */
  rc=submit(0,0);if(rc)goto fail;rc=ack(2,6);if(rc)goto fail;
  rc=submit(1,1);if(rc)goto fail;rc=ack(3,6);if(rc)goto fail;
  rc=apply_mixer();if(rc)goto fail;
  WRITE_ONCE(running,true);WRITE_ONCE(phase,2);
  writel(mp.start[0].value,transport.owner.mca1+0x18);
  writel(mp.start[1].value,transport.owner.mca1+0x0c);
  if(!queue_work(playback_queue,&playback_work)){rc=-EBUSY;goto fail;}
  return 0;
 case SNDRV_PCM_TRIGGER_STOP:WRITE_ONCE(running,false);return 0;
 default:return -EINVAL;
 }
fail:
 WRITE_ONCE(running,false);WRITE_ONCE(phase,4);
 if(dma_submitted){stoprc=send_cmd(8,15,0);if(!stoprc)stoprc=ack(15,8);if(stoprc)poisoned=true;}
 stoprc=restore_hw();prepared=false;if(stoprc)poisoned=true;
 dma_submitted=false;++stops;WRITE_ONCE(result,rc);WRITE_ONCE(phase,5);
 pr_err(TAG "synchronous start failed %d poisoned=%d\n",rc,poisoned);
 return rc;
}
static int pcm_sync_stop(struct snd_pcm_substream *s)
{cancel_work_sync(&playback_work);return 0;}
static snd_pcm_uframes_t pcm_pointer(struct snd_pcm_substream *s)
{return READ_ONCE(hw_pos);}
static const struct snd_pcm_ops pcm_ops={.open=pcm_open,.close=pcm_close,.ioctl=snd_pcm_lib_ioctl,
 .hw_params=pcm_params,.hw_free=pcm_free,.prepare=pcm_prepare,.trigger=pcm_trigger,.sync_stop=pcm_sync_stop,.pointer=pcm_pointer};
static int mixer_info(struct snd_kcontrol *k,struct snd_ctl_elem_info *i)
{
 i->type=k->private_value?SNDRV_CTL_ELEM_TYPE_BOOLEAN:SNDRV_CTL_ELEM_TYPE_INTEGER;
 i->count=1;i->value.integer.min=0;i->value.integer.max=k->private_value?1:60;return 0;
}
static int mixer_get(struct snd_kcontrol *k,struct snd_ctl_elem_value *v)
{v->value.integer.value[0]=k->private_value?READ_ONCE(speaker_on):READ_ONCE(volume);return 0;}
static int mixer_put(struct snd_kcontrol *k,struct snd_ctl_elem_value *v)
{
 long x=v->value.integer.value[0];int *p=k->private_value?&speaker_on:&volume,old;
 if(x<0||x>(k->private_value?1:60))return -EINVAL;
 old=READ_ONCE(*p);WRITE_ONCE(*p,x);return old!=x;
}
static const DECLARE_TLV_DB_SCALE(volume_tlv,-6000,100,0);
static const struct snd_kcontrol_new controls[]={
 {.iface=SNDRV_CTL_ELEM_IFACE_MIXER,.name="Speaker Playback Volume",.access=SNDRV_CTL_ELEM_ACCESS_READWRITE|SNDRV_CTL_ELEM_ACCESS_TLV_READ,.info=mixer_info,.get=mixer_get,.put=mixer_put,.tlv.p=volume_tlv},
 {.iface=SNDRV_CTL_ELEM_IFACE_MIXER,.name="Speaker Playback Switch",.private_value=1,.info=mixer_info,.get=mixer_get,.put=mixer_put},
};
static char *calibration_sha256;
module_param(calibration_sha256,charp,0400);
static const char *provider;
static int load_calibration(void)
{
 const struct firmware *fw;u8 expected[32],actual[32];int rc;
 if(!calibration_sha256||strlen(calibration_sha256)!=64||
    hex2bin(expected,calibration_sha256,32))return -EINVAL;
 rc=request_firmware_direct(&fw,"apple/j86-speaker-config.bin",NULL);if(rc)return rc;
 if(fw->size!=40){rc=-EINVAL;goto out;}
 sha256(fw->data,fw->size,actual);
 if(memcmp(expected,actual,32)){rc=-EBADMSG;goto out;}
 j86_codec_plan(fw->data,&codec_plan);rc=0;
out:release_firmware(fw);return rc;
}
static int take_live_transport(void)
{
 int (*claim)(struct j86_sio_transport *);int rc;
 /* Both providers must guarantee exclusive ownership and retain all DMA memory. */
 provider="j86_audio_session_claim";claim=__symbol_get(provider);
 if(!claim){provider="j86_pcm_v2_claim";claim=__symbol_get(provider);}
 if(!claim)return -ENODEV;
 rc=claim(&transport);
 /* Retain even on failure: provider may have disconnected before returning. */
 return rc;
}
int j86_pcm_native_claim(struct j86_sio_transport *out);
int j86_pcm_native_claim(struct j86_sio_transport *out)
{
 int rc=0;
 mutex_lock(&owner_lock);
 if(!out||handed_off||opened||running||poisoned){rc=-EBUSY;goto out;}
 handed_off=true;
 mutex_unlock(&owner_lock);
 snd_card_disconnect_sync(card);cancel_work_sync(&playback_work);
 if(prepared){rc=restore_hw();prepared=false;if(rc){poisoned=true;return rc;}}
 *out=transport;return 0;
out:mutex_unlock(&owner_lock);return rc;
}
EXPORT_SYMBOL_GPL(j86_pcm_native_claim);
static int __init pcm_init(void)
{
 struct snd_pcm *pcm;int rc,i;
 if(!allow_pcm)return -EPERM;
 if(!of_machine_is_compatible("apple,j86")||PAGE_SIZE!=4096||strcmp(utsname()->release,UTS_RELEASE))return -ENODEV;
 rc=load_calibration();if(rc)return rc;
 rc=take_live_transport();if(rc)return rc;
 /* After handoff retain ownership/module, including failure paths. */
 INIT_WORK(&playback_work,run_playback);
 playback_queue=alloc_workqueue("j86-pcm",WQ_HIGHPRI|WQ_UNBOUND|WQ_MEM_RECLAIM,1);
 if(!playback_queue){rc=-ENOMEM;goto out;}
 rc=snd_card_new(transport.owner.dma_device,-1,"J86Native",THIS_MODULE,0,&card);if(rc)goto out;
 rc=snd_dma_alloc_pages(SNDRV_DMA_TYPE_DEV,transport.owner.dma_device,BUFFER,&pcm_buf);if(rc)goto out;
 if(!IS_ALIGNED(pcm_buf.addr,4096)||pcm_buf.addr+BUFFER>BIT_ULL(36)){rc=-ERANGE;goto out;}
 memset(pcm_buf.area,0,BUFFER);
 rc=snd_pcm_new(card,"J86 Speakers",0,1,0,&pcm);if(rc)goto out;
 pcm->nonatomic=true;strscpy(pcm->name,"J86 Speakers");snd_pcm_set_ops(pcm,SNDRV_PCM_STREAM_PLAYBACK,&pcm_ops);
 for(i=0;i<ARRAY_SIZE(controls);++i){rc=snd_ctl_add(card,snd_ctl_new1(&controls[i],NULL));if(rc)goto out;}
 strscpy(card->driver,"J86SIO");strscpy(card->shortname,"J86 Speakers");strscpy(card->longname,"J86 A7 MCA1 CS35L19 experimental RAM playback");
 rc=snd_card_register(card);
out:
 result=rc;pr_info(TAG "registered result=%d; 48k stereo16, switch OFF, volume -30dB; RAM-only\n",rc);
 return 0;
}
module_init(pcm_init);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Opt-in fixed-format J86 ALSA playback, muted by default");
