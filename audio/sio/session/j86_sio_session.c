// SPDX-License-Identifier: GPL-2.0-only
/* Persistent isolated J86 SIO ownership. No stream setup; amps stay reset.
 * Once firmware can execute, memory and leases remain held until RAM reboot.
 * Unknown shared registers are never "restored" by guessed writeback.
 */
#include <clocksource/arm_arch_timer.h>
#include <crypto/sha2.h>
#include <linux/delay.h>
#include <linux/device.h>
#include <linux/dma-mapping.h>
#include <linux/firmware.h>
#include <linux/gpio/consumer.h>
#include <linux/gpio/driver.h>
#include <linux/gpio/machine.h>
#include <linux/interrupt.h>
#include <linux/io.h>
#include <linux/irqdomain.h>
#include <linux/ioport.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/of_irq.h>
#include <linux/pm_domain.h>
#include <linux/pm_runtime.h>
#include <linux/utsname.h>
#include <generated/utsrelease.h>
#include "j86-sio-session.h"
#define TAG "j86-sio-session: "
#define BASE 0x20ae00000ULL
#define EMPTY BIT(17)
static bool allow_session;
module_param(allow_session,bool,0400);
MODULE_PARM_DESC(allow_session,"Own isolated SIO/shared peripherals until RAM reboot; no playback; default off");
static bool preflight_only=true;
module_param(preflight_only,bool,0400);
MODULE_PARM_DESC(preflight_only,"Acquire and release resources without SIO writes; default true");
static atomic_t handoff_taken=ATOMIC_INIT(0);
static bool ready;
module_param(ready,bool,0400);
static int result = -EPERM;
module_param(result,int,0400);
struct target { const char *name; u64 base; u32 gate; };
static const struct target targets[] = {
 {"spi0",0x20a080000ULL,0x20098}, {"spi1",0x20a084000ULL,0x200a0},
 {"spi2",0x20a088000ULL,0x200a8}, {"spi3",0x20a08c000ULL,0x200b0},
 {"uart0",0x20a0a0000ULL,0x200b8}, {"uart1",0x20a0a4000ULL,0x200c0},
 {"uart2",0x20a0a8000ULL,0x200c8}, {"uart3",0x20a0ac000ULL,0x200d0},
 {"uart4",0x20a0b0000ULL,0x200d8}, {"uart5",0x20a0b4000ULL,0x200e0},
 {"uart6",0x20a0b8000ULL,0x200e8}, {"mca0",0x20a0c0000ULL,0x20048},
 {"mca1",0x20a0c4000ULL,0x20050}, {"mca2",0x20a0c8000ULL,0x20058},
 {"mca3",0x20a0cc000ULL,0x20060}, {"mca4",0x20a0d0000ULL,0x20068},
};

struct lease {struct device *dev; void __iomem *base; bool claimed,attached,enabled,active;};
static struct lease leases[ARRAY_SIZE(targets)];
static const u64 globals[]={0x20a000000ULL,0x20a001000ULL,0x20a100000ULL,BASE};
static const u32 sizes[]={0x1000,0x1000,0x1000,0x2000};
static bool global_claims[ARRAY_SIZE(globals)];
static struct device *fwdev;
static bool fw_attached,fw_enabled,fw_active;
static void *buffer;
static dma_addr_t dma;
static void __iomem *sio;
static unsigned int irqs[4];
static bool irq_claimed[4];
static struct gpio_device *gdev;
static struct gpio_desc *reset,*alive;
int j86_sio_session_claim(struct j86_sio_handoff *h)
{
 if(!h)return -EINVAL;
 if(!ready || result)return -ENODEV;
 if(atomic_cmpxchg(&handoff_taken,0,1))return -EBUSY;
 *h=(struct j86_sio_handoff){.dma_device=fwdev,.sio=sio,.mca1=leases[12].base};
 return 0;
}
EXPORT_SYMBOL_GPL(j86_sio_session_claim);
static irqreturn_t forbidden_irq(int irq,void *cookie) {return IRQ_NONE;}
static void release_preboot(void)
{
 int i;
 if(sio)iounmap(sio);
 if(buffer)dma_free_coherent(fwdev,0x72000,buffer,dma);
 if(fw_active)pm_runtime_put_sync_suspend(fwdev);
 if(fw_enabled)pm_runtime_disable(fwdev);
 if(fw_attached)pm_genpd_remove_device(fwdev);
 if(fwdev)root_device_unregister(fwdev);
 for(i=3;i>=0;--i){if(irq_claimed[i])free_irq(irqs[i],&irqs[i]);if(irqs[i])irq_dispose_mapping(irqs[i]);}
 for(i=ARRAY_SIZE(targets)-1;i>=0;--i){struct lease *l=&leases[i];
  if(l->base)iounmap(l->base);
  if(l->active)pm_runtime_put_sync_suspend(l->dev);
  if(l->enabled)pm_runtime_disable(l->dev);
  if(l->attached)pm_genpd_remove_device(l->dev);
  if(l->dev)root_device_unregister(l->dev);
  if(l->claimed)release_mem_region(targets[i].base,0x4000);
 }
 for(i=ARRAY_SIZE(globals)-1;i>=0;--i)if(global_claims[i])release_mem_region(globals[i],sizes[i]);
 if(alive)gpiochip_free_own_desc(alive);
 if(reset)gpiochip_free_own_desc(reset);
 if(gdev)gpio_device_put(gdev);
}
static int acquire(unsigned int i)
{
 const struct target *t=&targets[i];struct lease *l=&leases[i];
 struct of_phandle_args spec={.args_count=0};
 char path[100],name[64];int rc;
 if(!request_mem_region(t->base,0x4000,"j86-sio-session"))return -EBUSY;
 l->claimed=true;
 snprintf(path,sizeof(path),"/soc/power-management@20e000000/power-controller@%x",t->gate);
 spec.np=of_find_node_by_path(path);if(!spec.np)return -ENODEV;
 snprintf(name,sizeof(name),"j86-sio-session-%s",t->name);
 l->dev=root_device_register(name);
 if(IS_ERR(l->dev)){rc=PTR_ERR(l->dev);l->dev=NULL;of_node_put(spec.np);return rc;}
 rc=of_genpd_add_device(&spec,l->dev);of_node_put(spec.np);if(rc)return rc;
 l->attached=true;pm_runtime_enable(l->dev);l->enabled=true;
 rc=pm_runtime_resume_and_get(l->dev);if(rc<0)return rc;l->active=true;
 l->base=ioremap(t->base,0x4000);if(!l->base)return -ENOMEM;
 if(readl(l->base+0x1010) || readl(l->base+0x1810))return -EBUSY;
 return 0;
}
static int __init session_init(void)
{
 struct device_node *node=NULL;const struct firmware *fw=NULL;
 void __iomem *pins=NULL,*pmgr=NULL;
 struct irq_fwspec irqspec={.param_count=3};
 struct of_phandle_args powerspec={.args_count=0};
 const u32 hwirqs[]={133,132,135,134};
 u8 hash[SHA256_DIGEST_SIZE];
 static const u8 expected[SHA256_DIGEST_SIZE]={0xaf,0x3d,0x61,0x85,0x1d,0x4a,0x2d,0xd5,0x3d,0x73,0x01,0xd9,0x45,0xd7,0xff,0x3f,0x0d,0x94,0xee,0xf2,0xe1,0x59,0x47,0xf1,0xde,0x2c,0x9a,0x89,0x82,0x70,0x8e,0x33};
 int rc=-EPERM,i;u64 message,counter;unsigned long deadline;
 if(!allow_session)return -EPERM;
 if(!of_machine_is_compatible("apple,j86") || PAGE_SIZE!=4096 || strcmp(utsname()->release,UTS_RELEASE))return -ENODEV;
 /* Claim existing-low output pins ASIS, without pulsing either amplifier. */
 pins=ioremap(0x20e300000ULL,0x400);if(!pins){rc=-ENOMEM;goto fail;}
 if((readl(pins+4*114)&0x6f)!=2 || (readl(pins+4*161)&0x6f)!=2){rc=-EBUSY;goto fail;}
 node=of_find_node_by_path("/soc/pinctrl@20e300000");if(!node){rc=-ENODEV;goto fail;}
 gdev=gpio_device_find_by_fwnode(of_fwnode_handle(node));of_node_put(node);node=NULL;
 if(!gdev){rc=-ENODEV;goto fail;}
 reset=gpiochip_request_own_desc(gpio_device_get_chip(gdev),114,"j86-sio-speakers-reset",GPIO_LOOKUP_FLAGS_DEFAULT,GPIOD_ASIS);
 if(IS_ERR(reset)){rc=PTR_ERR(reset);reset=NULL;goto fail;}
 alive=gpiochip_request_own_desc(gpio_device_get_chip(gdev),161,"j86-sio-speakers-alive",GPIO_LOOKUP_FLAGS_DEFAULT,GPIOD_ASIS);
 if(IS_ERR(alive)){rc=PTR_ERR(alive);alive=NULL;goto fail;}
 for(i=0;i<ARRAY_SIZE(globals);++i){
  if(!request_mem_region(globals[i],sizes[i],"j86-sio-session")){rc=-EBUSY;goto fail;}
  global_claims[i]=true;
 }
 for(i=0;i<ARRAY_SIZE(targets);++i){rc=acquire(i);if(rc){pr_err(TAG "cannot own %s: %d\n",targets[i].name,rc);goto fail;}}
 node=of_find_node_by_path("/soc/interrupt-controller@20e100000");if(!node){rc=-ENODEV;goto fail;}
 irqspec.fwnode=of_fwnode_handle(node);irqspec.param[0]=0;irqspec.param[2]=IRQ_TYPE_LEVEL_HIGH;
 for(i=0;i<4;++i){
  irqspec.param[1]=hwirqs[i];
  irqs[i]=irq_create_fwspec_mapping(&irqspec);if(!irqs[i]){rc=-ENODEV;goto fail;}
  rc=request_irq(irqs[i],forbidden_irq,IRQF_NO_AUTOEN,"j86-sio-session",&irqs[i]);
  if(rc)goto fail;
  irq_claimed[i]=true;
 }
 of_node_put(node);node=NULL;
 pmgr=ioremap(0x20e020108ULL,4);if(!pmgr){rc=-ENOMEM;goto fail;}
 /* Inherited SIO must already be fully on; never reset or rewrite its gate. */
 if((readl(pmgr)&0xff)!=0xff){rc=-EBUSY;goto fail;}
 sio=ioremap(BASE,0x2000);if(!sio){rc=-ENOMEM;goto fail;}
 if(readl(sio+0x28) || readl(sio+0x20)!=1 || readl(sio+0x1008)!=EMPTY || readl(sio+0x1020)!=EMPTY){rc=-EBUSY;goto fail;}
 fwdev=root_device_register("j86-sio-session-fw");if(IS_ERR(fwdev)){rc=PTR_ERR(fwdev);fwdev=NULL;goto fail;}
 powerspec.np=of_find_node_by_path("/soc/power-management@20e000000/power-controller@20108");
 if(!powerspec.np){rc=-ENODEV;goto fail;}
 rc=of_genpd_add_device(&powerspec,fwdev);of_node_put(powerspec.np);if(rc)goto fail;
 fw_attached=true;pm_runtime_enable(fwdev);fw_enabled=true;
 rc=pm_runtime_resume_and_get(fwdev);if(rc<0)goto fail;fw_active=true;
 rc=dma_coerce_mask_and_coherent(fwdev,DMA_BIT_MASK(36));if(rc)goto fail;
 rc=request_firmware_direct(&fw,"apple/s5l8960x-smartio.bin",fwdev);if(rc)goto fail;
 if(fw->size!=0x71550){rc=-EINVAL;goto fail;}
 sha256(fw->data,fw->size,hash);
 if(memcmp(hash,expected,sizeof(hash))){rc=-EKEYREJECTED;goto fail;}
 buffer=dma_alloc_coherent(fwdev,0x72000,&dma,GFP_KERNEL);if(!buffer){rc=-ENOMEM;goto fail;}
 if(!IS_ALIGNED(dma,4096) || dma+0x72000>BIT_ULL(36)){rc=-ERANGE;goto fail;}
 memset(buffer,0,0x72000);memcpy(buffer,fw->data,fw->size);release_firmware(fw);fw=NULL;dma_wmb();
 /* Last preflight before any SIO writes. All leases remain held from here. */
 for(i=0;i<ARRAY_SIZE(targets);++i)if(readl(leases[i].base+0x1010) || readl(leases[i].base+0x1810)){rc=-EBUSY;goto fail;}
 if((readl(pins+4*114)&0x6f)!=2 || (readl(pins+4*161)&0x6f)!=2 || readl(sio+0x28)){rc=-EBUSY;goto fail;}
 if(preflight_only){rc=-ECANCELED;pr_info(TAG "PREFLIGHT_PASS: exact firmware, 16 peripheral leases, 4 shared ranges, 4 disabled IRQs, reset held; no SIO writes\n");goto fail;}
 iounmap(pins);pins=NULL;iounmap(pmgr);pmgr=NULL;
 writel(0,sio+0x20);readl(sio+0x20);
 writel(0,sio+0x10);writel(0,sio+0x14);writel(0x72000,sio+0x18);writel(0,sio+0x1c);
 writel(lower_32_bits(dma),sio+8);writel(upper_32_bits(dma),sio+12);writel(1,sio+0x20);readl(sio+0x20);
 writel(0x1111,sio+0x1000);writel(1,sio+0x1004);writel(0x1000,sio+0x1004);
 writel(readl(sio+0x1020)|1,sio+0x1020);
 writel(readl(sio+0x80c)&~BIT(1),sio+0x80c);counter=arch_timer_read_counter();
 writel(lower_32_bits(counter),sio+0x810);writel(upper_32_bits(counter),sio+0x818);
 writel(readl(sio+0x80c)|BIT(1),sio+0x80c);writel(BIT(4),sio+0x28);readl(sio+0x28);
 deadline=jiffies+msecs_to_jiffies(1500);rc=-ETIMEDOUT;
 do {
  u32 status=readl(sio+0x1020);
  if(status&GENMASK(19,18)){rc=-EIO;break;}
  if(!(status&EMPTY)){
   message=readq(sio+0x1038);
   if((u32)message==0x036d0000){ready=true;rc=0;break;}
   rc=-EPROTO;break;
  }
  usleep_range(500,1000);
 }while(time_before(jiffies,deadline));
 result=rc;
 if(rc){writel(0,sio+0x28);readl(sio+0x28);}
 pr_info(TAG "ready=%d result=%d; all leases and firmware RAM retained; no stream setup; amps held reset\n",ready,result);
 /* Keep module loaded even on failure: no buffers or shared leases freed. */
 return 0;
fail:
 result=rc;if(fw)release_firmware(fw);if(pins)iounmap(pins);if(pmgr)iounmap(pmgr);of_node_put(node);
 release_preboot();pr_err(TAG "preboot refusal=%d; no firmware executed\n",rc);return rc;
}
module_init(session_init);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Default-off persistent isolated J86 SIO READY session");
