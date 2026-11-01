// SPDX-License-Identifier: GPL-2.0-only OR MIT
/* Experimental A7 MCA-v1, fixed-format muted-bench CPU DAI.
 * ASoC/dmaengine integration adapted from Orchard S8000 MCA,
 * Copyright (C) 2026 Berkay Kösebay. A7 register backend is independently
 * modeled from exact J86 stock code. No codec/amp, NCO or route programming.
 * No sound card/DT activation is supplied. No IRQ/error recovery claim.
 */
#include <linux/clk.h>
#include <linux/io.h>
#include <linux/iopoll.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/pm_runtime.h>
#include <linux/soc/apple/sio.h>
#include <sound/dmaengine_pcm.h>
#include <sound/pcm_params.h>
#include <sound/soc.h>
#include "j86-mca-plan.h"
static bool allow_muted_bench;
module_param(allow_muted_bench,bool,0444);
MODULE_PARM_DESC(allow_muted_bench,"Unqualified pre-routed muted bench only (default off)");
struct j86_mca {
 struct device *dev;
 void __iomem *base;
 struct clk *mclk;
 struct j86_mca_plan plan;
 struct snd_dmaengine_dai_dma_data tx;
 struct apple_sio_dma_config shim;
 unsigned long previous_rate;
 bool powered,prepared;
};
static int mca_startup(struct snd_pcm_substream *s,struct snd_soc_dai *dai)
{
 struct j86_mca *m=snd_soc_dai_get_drvdata(dai);
 int ret=pm_runtime_resume_and_get(m->dev);
 if (ret<0) return ret;
 ret=clk_rate_exclusive_get(m->mclk);
 if (ret) goto power_off;
 m->previous_rate=clk_get_rate(m->mclk);
 if (!m->previous_rate) { ret=-EINVAL;goto release_rate; }
 ret=clk_set_rate(m->mclk,12288000);
 if (ret) goto restore_rate;
 if (clk_get_rate(m->mclk)!=12288000) { ret=-ERANGE;goto restore_rate; }
 ret=clk_prepare_enable(m->mclk);
 if (ret) goto restore_rate;
 m->powered=true;
 return 0;
restore_rate:
 if (clk_set_rate(m->mclk,m->previous_rate)) dev_err(m->dev,"MCLK rate restore failed\n");
release_rate:
 clk_rate_exclusive_put(m->mclk);
power_off:
 pm_runtime_put_sync_suspend(m->dev);
 return ret;
}
static int mca_stop(struct j86_mca *m)
{
 u32 value;
 if (!m->powered) return 0;
 writel(0,m->base+0x18);
 writel(1,m->base+0x44);
 return readl_poll_timeout_atomic(m->base+0x44,value,!(value&1),1,1000);
}
static void mca_shutdown(struct snd_pcm_substream *s,struct snd_soc_dai *dai)
{
 struct j86_mca *m=snd_soc_dai_get_drvdata(dai);
 if (!m->powered) return;
 if (mca_stop(m)) dev_err(m->dev,"TX stop timed out; bench requires recovery\n");
 m->prepared=false;
 clk_disable_unprepare(m->mclk);
 if (clk_set_rate(m->mclk,m->previous_rate)) dev_err(m->dev,"MCLK rate restore failed\n");
 clk_rate_exclusive_put(m->mclk);
 pm_runtime_put_sync_suspend(m->dev);
 m->powered=false;
}
static int mca_fmt(struct snd_soc_dai *dai,unsigned int fmt)
{
 if ((fmt&SND_SOC_DAIFMT_CLOCK_PROVIDER_MASK)!=SND_SOC_DAIFMT_BP_FP ||
     (fmt&SND_SOC_DAIFMT_FORMAT_MASK)!=SND_SOC_DAIFMT_I2S ||
     (fmt&SND_SOC_DAIFMT_INV_MASK)!=SND_SOC_DAIFMT_NB_NF) return -EINVAL;
 return 0;
}
static int mca_params(struct snd_pcm_substream *s,struct snd_pcm_hw_params *params,struct snd_soc_dai *dai)
{
 struct j86_mca *m=snd_soc_dai_get_drvdata(dai);
 return j86_mca_plan(params_rate(params),params_channels(params),params_width(params),1,&m->plan);
}
static int mca_prepare(struct snd_pcm_substream *s,struct snd_soc_dai *dai)
{
 struct j86_mca *m=snd_soc_dai_get_drvdata(dai);
 unsigned int i;u32 value;
 int ret;
 if (!m->powered || m->plan.mclk_hz!=12288000) return -EINVAL;
 m->prepared=false;
 for (i=0;i<J86_MCA_CONFIGURE_COUNT;i++) {
  const struct j86_mca_write *w=&m->plan.configure[i];
  writel(w->value,m->base+w->offset);
  /* A7 stock writes reset then flush, and polls only flush bit0.
   * Waiting for reset before issuing flush is not the observed protocol.
   */
  if (i==1) {
   ret=readl_poll_timeout(m->base+w->offset,value,!(value&1),10,10000);
   if (ret) return ret;
  }
 }
 m->prepared=true;
 return 0;
}
static int mca_trigger(struct snd_pcm_substream *s,int cmd,struct snd_soc_dai *dai)
{
 struct j86_mca *m=snd_soc_dai_get_drvdata(dai);
 switch (cmd) {
 case SNDRV_PCM_TRIGGER_START:
  if (!m->prepared) return -EINVAL;
  writel(m->plan.start[0].value,m->base+0x18);
  writel(m->plan.start[1].value,m->base+0x0c);
  return 0;
 case SNDRV_PCM_TRIGGER_STOP:
  return mca_stop(m);
 default:return -EINVAL; /* No unqualified suspend/resume/pause shortcuts. */
 }
}
static int mca_dai_probe(struct snd_soc_dai *dai)
{
 struct j86_mca *m=snd_soc_dai_get_drvdata(dai);
 snd_soc_dai_init_dma_data(dai,&m->tx,NULL);
 return 0;
}
static const struct snd_soc_dai_ops mca_ops={
 .probe=mca_dai_probe,.startup=mca_startup,.shutdown=mca_shutdown,
 .set_fmt=mca_fmt,.hw_params=mca_params,.prepare=mca_prepare,.trigger=mca_trigger,
};
static struct snd_soc_dai_driver mca_dai={
 .name="j86-mca-bench",.ops=&mca_ops,
 .playback={ .stream_name="Muted bench playback",.channels_min=2,.channels_max=2,
  .rates=SNDRV_PCM_RATE_48000,.formats=SNDRV_PCM_FMTBIT_S16_LE },
};
static const struct snd_soc_component_driver mca_component={ .name="j86-mca-bench" };
static const struct snd_pcm_hardware mca_hw={
 .info=SNDRV_PCM_INFO_INTERLEAVED|SNDRV_PCM_INFO_MMAP|SNDRV_PCM_INFO_MMAP_VALID|
  SNDRV_PCM_INFO_BLOCK_TRANSFER|SNDRV_PCM_INFO_BATCH,
 .formats=SNDRV_PCM_FMTBIT_S16_LE,.rates=SNDRV_PCM_RATE_48000,
 .rate_min=48000,.rate_max=48000,.channels_min=2,.channels_max=2,
 .buffer_bytes_max=128*1024,.period_bytes_min=512,.period_bytes_max=32*1024,
 .periods_min=2,.periods_max=16,
};
static int mca_slave(struct snd_pcm_substream *s,struct snd_pcm_hw_params *p,struct dma_slave_config *sc)
{
 struct snd_soc_pcm_runtime *rtd=snd_soc_substream_to_rtd(s);
 struct j86_mca *m=snd_soc_dai_get_drvdata(snd_soc_rtd_to_cpu(rtd,0));
 int ret;
 if (params_rate(p)!=48000 || params_channels(p)!=2 || params_width(p)!=16) return -EINVAL;
 ret=snd_dmaengine_pcm_prepare_slave_config(s,p,sc);
 if (ret) return ret;
 /* Exact ADT endpoint words; limit is one millisecond of stereo16 samples.
  * SIO parameter10/shared word6 is frame4, never FIFO128.
  */
 m->shim=(struct apple_sio_dma_config){.xfer=0x21,.timeout=0,.fifo=0xcc,
  .trigger=0xac,.limit=192,.frame=4};
 sc->peripheral_config=&m->shim;sc->peripheral_size=sizeof(m->shim);
 return 0;
}
static const struct snd_dmaengine_pcm_config mca_pcm={
 .prepare_slave_config=mca_slave,.pcm_hardware=&mca_hw,.prealloc_buffer_size=128*1024,
};
static int mca_probe(struct platform_device *pdev)
{
 struct device *dev=&pdev->dev;
 struct resource *r;struct j86_mca *m;u32 version,fifo;
 int ret;
 if (!allow_muted_bench) return -EPERM;
 if (!of_machine_is_compatible("apple,j86") || PAGE_SIZE!=4096) return -ENODEV;
 /* Prerequisites are not fulfilled by any supplied DT. No guessed clock/route.
  * A future bench must independently hold both amps muted/reset throughout.
  */
 if (!of_property_read_bool(dev->of_node,"apple,bench-amps-held-reset") ||
     !of_property_read_bool(dev->of_node,"apple,route-preconfigured") || !dev->pm_domain) return -EPERM;
 r=platform_get_resource(pdev,IORESOURCE_MEM,0);
 if (!r || r->start!=0x20a0c4000ULL || resource_size(r)!=0x4000) return -ENODEV;
 m=devm_kzalloc(dev,sizeof(*m),GFP_KERNEL);if (!m) return -ENOMEM;
 m->dev=dev;platform_set_drvdata(pdev,m);
 m->base=devm_ioremap_resource(dev,r);if (IS_ERR(m->base)) return PTR_ERR(m->base);
 m->mclk=devm_clk_get(dev,"mclk");if (IS_ERR(m->mclk)) return PTR_ERR(m->mclk);
 ret=devm_pm_runtime_enable(dev);if (ret) return ret;
 ret=pm_runtime_resume_and_get(dev);if (ret<0) return ret;
 version=readl(m->base);fifo=readl(m->base+4);
 pm_runtime_put_sync_suspend(dev);
 if (!j86_mca_identity(version,fifo)) return -ENODEV;
 m->tx.addr_width=DMA_SLAVE_BUSWIDTH_2_BYTES;m->tx.maxburst=1;
 ret=devm_snd_soc_register_component(dev,&mca_component,&mca_dai,1);if (ret) return ret;
 return devm_snd_dmaengine_pcm_register(dev,&mca_pcm,0);
}
static int mca_suspend(struct device *dev)
{
 struct j86_mca *m=dev_get_drvdata(dev);
 return m->powered ? -EBUSY : 0;
}
static const struct dev_pm_ops mca_pm={ .suspend=mca_suspend };
static const struct of_device_id mca_match[]={ {.compatible="apple,j86-mca-bench"},{} };
MODULE_DEVICE_TABLE(of,mca_match);
static struct platform_driver mca_driver={.probe=mca_probe,.driver={.name="j86-mca-bench",.of_match_table=mca_match,.pm=&mca_pm}};
module_platform_driver(mca_driver);
MODULE_LICENSE("Dual MIT/GPL");
MODULE_DESCRIPTION("Disabled pre-routed muted-bench A7 MCA CPU DAI");
