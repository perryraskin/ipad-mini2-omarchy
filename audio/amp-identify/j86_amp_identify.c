// SPDX-License-Identifier: GPL-2.0-only
/* Explicit, bounded CS35L19 identity reads. No codec configuration or audio. */
#include <linux/delay.h>
#include <linux/gpio/consumer.h>
#include <linux/gpio/driver.h>
#include <linux/gpio/machine.h>
#include <linux/i2c.h>
#include <linux/io.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/utsname.h>
#include <generated/utsrelease.h>
#include "overlay.h"
#define TAG "j86-amp-identify: "
static bool allow_identify;
module_param(allow_identify,bool,0600);
MODULE_PARM_DESC(allow_identify,"Opt in to temporary I2C2 and bounded reset-release identity reads; default off");
static int read_registers(struct i2c_adapter *a,u16 address,u8 reg,u8 *data,u16 length)
{
 struct i2c_msg msgs[]={{.addr=address,.len=1,.buf=&reg},
                      {.addr=address,.flags=I2C_M_RD,.len=length,.buf=data}};
 int rc=i2c_transfer(a,msgs,2);
 return rc==2 ? 0 : (rc<0 ? rc : -EIO);
}
static int __init probe_init(void)
{
 struct device_node *bus=NULL,*gpio=NULL;
 struct gpio_device *gdev=NULL;
 struct gpio_desc *reset=NULL;
 struct i2c_adapter *adapter=NULL;
 void __iomem *pins=NULL,*pmgr=NULL;
 u32 saved[4],power=0;
 const u32 numbers[]={100,101,114,161};
 int ov=-1,rc=-ENODEV,ret,i,j,identified=0;
 bool raised=false,restored=true,snapshot=false;
 if(!allow_identify)return -EPERM;
 if(!of_machine_is_compatible("apple,j86") || PAGE_SIZE!=4096 ||
    strcmp(utsname()->release,UTS_RELEASE))return -ENODEV;
 bus=of_find_node_by_path("/soc/i2c@20a112000");
 gpio=of_find_node_by_path("/soc/pinctrl@20e300000");
 if(!bus || !gpio || of_device_is_available(bus))goto out;
 pins=ioremap(0x20e300000ULL,0x400);pmgr=ioremap(0x20e020088ULL,4);
 if(!pins || !pmgr){rc=-ENOMEM;goto out;}
 power=readl(pmgr);
 if(power&0xff){rc=-EBUSY;goto out;}
 for(i=0;i<4;++i)saved[i]=readl(pins+4*numbers[i]);
 snapshot=true;
 /* Existing I2C mux/input-enable; reset and keepalive must be GPIO outputs low. */
 if((saved[0]&0x260)!=0x220 || (saved[1]&0x260)!=0x220 ||
    (saved[2]&0x6f)!=2 || (saved[3]&0x6f)!=2){rc=-EBUSY;goto out;}
 gdev=gpio_device_find_by_fwnode(of_fwnode_handle(gpio));
 if(!gdev){rc=-ENODEV;goto out;}
 reset=gpiochip_request_own_desc(gpio_device_get_chip(gdev),114,"j86-amp-identify",
                                GPIO_LOOKUP_FLAGS_DEFAULT,GPIOD_ASIS);
 if(IS_ERR(reset)){rc=PTR_ERR(reset);reset=NULL;goto out;}
 rc=of_overlay_fdt_apply(overlay_blob,sizeof(overlay_blob),&ov,NULL);
 if(rc)goto out;
 adapter=of_find_i2c_adapter_by_node(bus);
 if(!adapter){rc=-ENODEV;goto out;}
 /* Ordinary I2C driver handles clocks and transfer timeout. No bus scan. */
 rc=gpiod_direction_output_raw(reset,1);
 if(rc)goto out;
 raised=true;usleep_range(2000,3000);
 for(i=0;i<2;++i){
  u8 id[3]={0},rev=0;
  /* CS35L19 does not auto-increment registers within a transfer. */
  for(j=0;j<3;++j){
   rc=read_registers(adapter,0x40+i,1+j,&id[j],1);
   if(rc){pr_err(TAG "amp=%d ID read failed %d\n",i,rc);goto out;}
  }
  if(id[0]!=0x35 || id[1]!=0xa1 || (id[2]&0xf0)!=0x90){
   pr_err(TAG "amp=%d unexpected ID %02x%02x%02x\n",i,id[0],id[1],id[2]);rc=-ENODEV;goto out;
  }
  rc=read_registers(adapter,0x40+i,5,&rev,1);
  if(rc)goto out;
  pr_info(TAG "amp=%d CS35L19 ID=%02x%02x%02x revision=%02x\n",i,id[0],id[1],id[2],rev);
  ++identified;
 }
out:
 if(raised){gpiod_set_raw_value_cansleep(reset,0);usleep_range(2000,3000);}
 if(adapter)i2c_put_adapter(adapter);
 if(ov>0){
  ret=of_overlay_remove(&ov);
  if(ret){pr_err(TAG "overlay cleanup failed %d; retaining module; no further test\n",ret);return 0;}
 }
 if(reset)gpiochip_free_own_desc(reset);
 if(gdev)gpio_device_put(gdev);
 if(snapshot){
  for(i=0;i<4;++i){u32 now=readl(pins+4*numbers[i]);
   pr_info(TAG "gpio%u before=%08x after=%08x\n",numbers[i],saved[i],now);
   if(now!=saved[i])restored=false;
  }
  pr_info(TAG "power before=%08x after=%08x\n",power,readl(pmgr));
  if(readl(pmgr)!=power)restored=false;
 }
 if(pins)iounmap(pins);
 if(pmgr)iounmap(pmgr);
 of_node_put(bus);of_node_put(gpio);
 pr_info(TAG "done rc=%d identified=%d restored=%d; no codec configuration or audio\n",rc,identified,restored);
 if(!rc && identified==2 && restored){pr_info(TAG "J86_AMP_IDENTIFY_PASS\n");return -ECANCELED;}
 return rc ?: -EIO;
}
module_init(probe_init);
MODULE_LICENSE("GPL");
