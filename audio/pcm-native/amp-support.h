/* Runtime-calibrated amplifier support. Retains the already enabled I2C bus. */
#include <linux/gpio/consumer.h>
#include <linux/gpio/driver.h>
#include <linux/i2c.h>
#include <linux/of.h>
#include "codec-plan.h"
static struct j86_codec_plan codec_plan;
static struct i2c_adapter *bus;
static struct gpio_device *amp_gd;
static struct gpio_desc *amp_reset;
static void __iomem *amp_clk;
static bool amp_region,amp_raised,amp_clocked;
static int rd(int amp,u8 reg,u8 *v)
{
 struct i2c_msg m[]={{.addr=0x40+amp,.len=1,.buf=&reg},{.addr=0x40+amp,.flags=I2C_M_RD,.len=1,.buf=v}};
 int r=i2c_transfer(bus,m,2);return r==2?0:r<0?r:-EIO;
}
static int wr(int amp,u8 reg,u8 val,u8 mask)
{
 u8 b[]={reg,val},old;struct i2c_msg m={.addr=0x40+amp,.len=2,.buf=b};int r;
 if(mask!=255){r=rd(amp,reg,&old);if(r)return r;b[1]=(old&~mask)|(val&mask);}
 r=i2c_transfer(bus,&m,1);return r==1?0:r<0?r:-EIO;
}
static int stage(const struct op *ops,size_t n)
{size_t i;int r;for(i=0;i<n;++i){r=wr(ops[i].amp,ops[i].reg,ops[i].value,ops[i].mask);if(r)return r;}return 0;}
#define STAGE(x) do {rc=stage(codec_plan.x,ARRAY_SIZE(codec_plan.x));if(rc)goto out;}while(0)
#define BOTH(r,v,m) do {for(a=0;a<2;++a){rc=wr(a,r,v,m);if(rc)goto out;}}while(0)
static int amps_on(void)
{
 struct device_node *node=NULL,*gnode=NULL;
 void __iomem *pins=NULL;int rc,a,j;u8 v,id[4];
 bus=NULL;amp_gd=NULL;amp_reset=NULL;amp_clk=NULL;
 amp_region=false;amp_raised=false;amp_clocked=false;
 node=of_find_node_by_path("/soc/i2c@20a112000");gnode=of_find_node_by_path("/soc/pinctrl@20e300000");
 if(!node||!gnode||!of_device_is_available(node)){rc=-ENODEV;goto out;}
 amp_gd=gpio_device_find_by_fwnode(of_fwnode_handle(gnode));if(!amp_gd){rc=-ENODEV;goto out;}
 /* Borrow within the exclusively handed-off subsystem. The persistent SIO
  * session retains the GPIO request and has no asynchronous GPIO workers. */
 amp_reset=gpio_device_get_desc(amp_gd,114);if(IS_ERR(amp_reset)){rc=PTR_ERR(amp_reset);amp_reset=NULL;goto out;}
 pins=ioremap(0x20e300000ULL,0x400);if(!pins){rc=-ENOMEM;goto out;}
 if((readl(pins+456)&0x6f)!=2 || (readl(pins+644)&0x6f)!=2){rc=-EBUSY;goto out;}
 if(!request_mem_region(0x20a002004ULL,4,"j86-amp-bench")){rc=-EBUSY;goto out;}amp_region=true;
 amp_clk=ioremap(0x20a002004ULL,4);if(!amp_clk){rc=-ENOMEM;goto out;}
 if(readl(amp_clk)){rc=-EBUSY;goto out;}
 bus=of_find_i2c_adapter_by_node(node);if(!bus){rc=-ENODEV;goto out;}
 rc=gpiod_direction_output_raw(amp_reset,1);if(rc)goto out;amp_raised=true;usleep_range(2000,3000);
 for(a=0;a<2;++a){
  for(j=0;j<3;++j){rc=rd(a,1+j,&id[j]);if(rc)goto out;}
  rc=rd(a,5,&id[3]);if(rc)goto out;
  if(id[0]!=0x35||id[1]!=0xa1||(id[2]&0xf0)!=0x90||id[3]!=0xb0){rc=-ENODEV;goto out;}
 }
 rc=stage(codec_plan.revision,codec_plan.nr);if(rc)goto out;
 writel(0x58,amp_clk);amp_clocked=true;if(readl(amp_clk)!=0x58){rc=-EIO;goto out;}
 /* No keepalive timer: use exact stock no-keepalive branch for this bounded test. */
 for(a=0;a<2;++a){rc=wr(a,0xa,8,15);if(rc)goto out;rc=wr(a,0xc,8,8);if(rc)goto out;}
 STAGE(serial);STAGE(boost);BOTH(6,0x80,255);STAGE(power);
 /* Verify mute at the last possible point before powering the output stage. */
 for(a=0;a<2;++a){rc=rd(a,0x10,&v);if(rc)goto out;if(v!=0x19){rc=-EIO;goto out;}}
 usleep_range(10000,11000);BOTH(6,0,255);usleep_range(8000,9000);
 for(a=0;a<2;++a){
  u8 st1,st2;
  rc=rd(a,0x15,&v);if(rc)goto out;rc=rd(a,0x15,&st1);if(rc)goto out;
  rc=rd(a,0x16,&v);if(rc)goto out;rc=rd(a,0x16,&st2);if(rc)goto out;
  if(st1 || st2){rc=-EIO;pr_err("j86-pcm: amp=%d bad status=%02x/%02x\n",a,st1,st2);goto out;}
  for(j=0;j<ARRAY_SIZE(codec_plan.status);++j)if(codec_plan.status[j].amp==a){
   rc=wr(a,codec_plan.status[j].reg,codec_plan.status[j].value,codec_plan.status[j].mask);if(rc)goto out;
  }
 }

 for(a=0;a<2;++a){rc=rd(a,0x10,&v);if(rc)goto out;if(v!=0x19){rc=-EIO;goto out;}}
 rc=0;
out:
 if(pins)iounmap(pins);
 of_node_put(node);of_node_put(gnode);
 return rc;
}
static int amps_off(void)
{
 int a,e=0;
 if(amp_raised){
  for(a=0;a<2;++a)e|=wr(a,0x10,0x19,255);
  for(a=0;a<2;++a)e|=wr(a,6,0x80,0x80);
  for(a=0;a<2;++a)e|=wr(a,7,0xfe,255);
  usleep_range(1000,2000);
  for(a=0;a<2;++a)e|=wr(a,6,0x87,255);
  usleep_range(4000,5000);gpiod_set_raw_value_cansleep(amp_reset,0);
  usleep_range(2000,3000);
  if(gpiod_get_raw_value_cansleep(amp_reset)!=0)e=-EIO;
 }
 if(amp_clocked){writel(0,amp_clk);if(readl(amp_clk))e=-EIO;}
 if(amp_clk)iounmap(amp_clk);
 if(amp_region)release_mem_region(0x20a002004ULL,4);
 if(amp_gd)gpio_device_put(amp_gd);
 if(bus)i2c_put_adapter(bus);
 bus=NULL;amp_gd=NULL;amp_reset=NULL;amp_clk=NULL;
 amp_region=false;amp_raised=false;amp_clocked=false;
 return e ? -EIO : 0;
}
