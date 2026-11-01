// SPDX-License-Identifier: GPL-2.0-only
/* Polling shared-region setup adapted from Orchard apple-sio-core.
 * No peripheral DMA submits. Every shared buffer is retained until RAM reboot.
 */
#include <linux/dma-mapping.h>
#include <linux/iopoll.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/i2c.h>
#include "overlay.h"
#include "../transport/j86-sio-transport.h"
#include "setup-plan.h"
#define TAG "j86-audio-session: "
static bool allow_setup;
module_param(allow_setup,bool,0400);
static bool setup_complete;
module_param(setup_complete,bool,0400);
static int result=-EPERM;
module_param(result,int,0400);
static unsigned int acknowledged;
module_param(acknowledged,uint,0400);
static struct j86_sio_handoff owner;
static atomic_t taken=ATOMIC_INIT(0);
static int overlay_id=-1;
static struct i2c_adapter *retained_bus;
static int enable_codec_bus(void)
{
 struct device_node *node=of_find_node_by_path("/soc/i2c@20a112000");int rc;
 if(!node)return -ENODEV;
 if(of_device_is_available(node)){rc=-EBUSY;goto out;}
 rc=of_overlay_fdt_apply(overlay_blob,sizeof(overlay_blob),&overlay_id,NULL);
 if(rc)goto out;
 /* Never reapply/remove this overlay in a running firmware session. */
 retained_bus=of_find_i2c_adapter_by_node(node);
 if(!retained_bus)rc=-ENODEV;
out:of_node_put(node);return rc;
}
struct region {void *cpu;dma_addr_t dma;size_t size;};
static struct region regions[]={{.size=0x4000},{.size=0x4000},{.size=0x8000},{.size=0x11000}};
int j86_audio_session_claim(struct j86_sio_transport *out);
int j86_audio_session_claim(struct j86_sio_transport *out)
{
 if(!out)return -EINVAL;
 if(!setup_complete || result)return -ENODEV;
 if(atomic_cmpxchg(&taken,0,1))return -EBUSY;
 *out=(struct j86_sio_transport){.owner=owner,.desc0=regions[2].cpu,.desc0_dma=regions[2].dma,.slots=0xaaa};
 return 0;
}
EXPORT_SYMBOL_GPL(j86_audio_session_claim);
static int exchange(u8 endpoint,u8 tag,u8 parameter,u32 value)
{
 u64 tx=((u64)value<<32)|((u32)parameter<<24)|(3<<16)|(tag<<8)|endpoint,rx;
 u32 status;int rc;
 rc=readl_poll_timeout(owner.sio+0x1008,status,(status&BIT(17)) || (status&GENMASK(19,18)),10,200000);
 if(rc)return rc;
 if(status&GENMASK(19,18))return -EIO;
 dma_wmb();writeq(tx,owner.sio+0x1010);
 rc=readl_poll_timeout(owner.sio+0x1020,status,!(status&BIT(17)) || (status&GENMASK(19,18)),50,1000000);
 if(rc)return rc;
 if(status&GENMASK(19,18))return -EIO;
 rx=readq(owner.sio+0x1038);dma_rmb();
 /* Setup ack must match endpoint and request tag, with opcode 0x65. */
 if((rx&0xffffff)!=((0x65<<16)|(tag<<8)|endpoint)){
  pr_err(TAG "unexpected setup response ep=%u tag=%u opcode=%u\n",(u8)rx,(u8)(rx>>8),(u8)(rx>>16));
  return -EPROTO;
 }
 return 0;
}
static int __init transport_init(void)
{
 struct j86_setup_command commands[8];unsigned long long addresses[4];int rc,i;
 if(!allow_setup)return -EPERM;
 rc=j86_sio_session_claim(&owner);if(rc)return rc;
 /* From this point remain resident even on failure, preserving handoff state. */
 for(i=0;i<ARRAY_SIZE(regions);++i){
  struct region *r=&regions[i];
  r->cpu=dma_alloc_coherent(owner.dma_device,r->size,&r->dma,GFP_KERNEL);
  if(!r->cpu){rc=-ENOMEM;goto retained;}
  if(!IS_ALIGNED(r->dma,4096) || r->dma+r->size>BIT_ULL(36)){rc=-ERANGE;goto retained;}
  memset(r->cpu,0,r->size);
 }
 for(i=0;i<4;++i)addresses[i]=regions[i].dma;
 rc=j86_setup_plan(addresses,commands);if(rc)goto retained;
 for(i=0;i<8;++i){
  const struct j86_setup_command *c=&commands[i];
  rc=exchange(c->endpoint,c->tag,c->parameter,c->value);
  if(rc){pr_err(TAG "setup step %d failed %d\n",i,rc);goto retained;}
  ++acknowledged;
 }
 rc=enable_codec_bus();if(rc)goto retained;
 setup_complete=true;rc=0;
retained:
 result=rc;
 pr_info(TAG "setup_complete=%d acknowledged=%u result=%d; buffers retained, no DMA submitted\n",setup_complete,acknowledged,result);
 return 0;
}
module_init(transport_init);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Default-off isolated J86 SIO shared-region setup");
