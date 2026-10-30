// SPDX-License-Identifier: GPL-2.0-only
/* Exact-J86 native touchscreen. Resident because kernel MODULE_UNLOAD=n.
 * enabled=N stops input and restores hardware; enabled=Y restarts cleanly.
 * Rail decoding/provenance: ../j86-power-notes.md. Restore every owned control.
 */
#include <linux/device.h>
#include <linux/delay.h>
#include <linux/err.h>
#include <linux/gpio/driver.h>
#include <linux/gpio/machine.h>
#include <linux/gpio/consumer.h>
#include <linux/i2c.h>
#include <linux/io.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/pm_domain.h>
#include <linux/pm_runtime.h>
#include <linux/regmap.h>
#include <linux/utsname.h>
#include <linux/ktime.h>
#include <linux/firmware.h>
#include <linux/sched.h>
#include <linux/unaligned.h>
#include <linux/input.h>
#include <linux/input/mt.h>
#include <linux/kthread.h>
#define TAG "j86-touch-probe: "
static bool enabled=true;
module_param(enabled,bool,0600);
MODULE_PARM_DESC(enabled,"Enable touchscreen; disable restores hardware; re-enable restarts firmware");
static unsigned int state;
module_param(state,uint,0444);
MODULE_PARM_DESC(state,"0 idle, 1 starting, 2 input ready, 3 failed");
static int last_result;
module_param(last_result,int,0444);
static unsigned long long finger_frames, invalid_frames;
module_param(finger_frames,ullong,0444);
module_param(invalid_frames,ullong,0444);
static s16 left,top,right,bottom;
static u32 spi_divisor=480;
static int transfer(void __iomem *spi,struct gpio_desc *cs,const u8 *tx,u8 *rx,unsigned int len) {
 unsigned int sent=0,got=0;u64 deadline;u32 status,lvl;int rc=0;
 if(!len||len>65536)return -EINVAL;
 writel(0,spi);writel(2,spi+12);writel(0x4018,spi+4);
 writel(len,spi+0x34);writel(len,spi+0x4c);writel(spi_divisor,spi+0x30);writel(0,spi+0x38);
 writel(0x40000f,spi+8);
 rc=gpiod_direction_output_raw(cs,0);if(rc)return rc;usleep_range(1000,1200);
 writel(13,spi);writel(0x4038,spi+4);
 deadline=ktime_get_ns()+100000000ULL+(u64)len*100000ULL;
 while(got<len){
  status=readl(spi+8);writel(status&0x40000f,spi+8);
  lvl=(status>>11)&31;while(lvl--&&got<len){u8 v=readl(spi+0x20);if(rx)rx[got]=v;got++;}
  lvl=(status>>6)&31;while(lvl++<16&&sent<len){writel(tx?tx[sent]:0xff,spi+0x10);sent++;}
  if(ktime_get_ns()>deadline){rc=-ETIMEDOUT;break;}cond_resched();
 }
 writel(0,spi);if(gpiod_direction_output_raw(cs,1))rc=-EIO;
 if(rc)pr_err(TAG "transfer rc=%d sent=%u got=%u len=%u\n",rc,sent,got,len);
 usleep_range(1000,1200);return rc;
}
static int hbpp(void __iomem *spi,struct gpio_desc *cs){
 u8 tx[16]={0x1a,0xa1},rx[16]={0};int i,rc;
 for(i=2;i<16;i+=2){tx[i]=0x18;tx[i+1]=0xe1;}
 rc=transfer(spi,cs,tx,rx,16);if(rc)return rc;
 pr_info(TAG "HBPP RX=%*ph\n",16,rx);
 return rx[0]==0x1f&&rx[1]==1&&rx[2]==0x48&&rx[3]==0x79?0:-EPROTO;
}
static u16 sum(const u8 *p,unsigned int len){u16 s=0;while(len--)s+=*p++;return s;}
static void put32(u8 *p,u32 v){p[0]=v>>8;p[1]=v;p[2]=v>>24;p[3]=v>>16;}
static int ack(void __iomem *spi,struct gpio_desc *cs,u16 want){
 u8 tx[2]={0x1a,0xa1},rx[2];int rc=transfer(spi,cs,tx,rx,2);if(rc)return rc;
 pr_info(TAG "ACK=%02x%02x want=%04x\n",rx[0],rx[1],want);
 return ((rx[0]<<8)|rx[1])==want?0:-EPROTO;
}
static int reg_read_chip(void __iomem *spi,struct gpio_desc *cs,u32 addr,u32 *v){
 u8 tx[8]={0x1c,0x73},rx[8],query[8]={0x1a,0xa1,0x18,0xe1,0x18,0xe1,0x18,0xe1};u16 c;int rc;
 put32(tx+2,addr);c=sum(tx+2,4);tx[6]=c>>8;tx[7]=c;
 rc=transfer(spi,cs,tx,NULL,8);if(rc)return rc;msleep(20);
 rc=transfer(spi,cs,query,rx,8);if(rc)return rc;
 *v=((u32)rx[4]<<24)|((u32)rx[5]<<16)|((u32)rx[2]<<8)|rx[3];
 pr_info(TAG "chip[0x%08x]=0x%08x status=%02x%02x\n",addr,*v,rx[0],rx[1]);
 return rx[0]==0x4c&&rx[1]==0x39?0:-EPROTO;
}
static int reg_write_chip(void __iomem *spi,struct gpio_desc *cs,u32 addr,u32 value){
 u8 tx[16]={0x1e,0x33};u16 c;int rc;
 put32(tx+2,addr);put32(tx+6,0xffffffff);put32(tx+10,value);c=sum(tx+2,12);tx[14]=c>>8;tx[15]=c;
 rc=transfer(spi,cs,tx,NULL,16);if(rc)return rc;msleep(20);
 pr_info(TAG "write chip[0x%08x]=0x%08x\n",addr,value);return ack(spi,cs,0x4ad1);
}
static int calibration(void __iomem *spi,struct gpio_desc *cs,const struct firmware *cal,u32 addr){
 static u8 pkt[1024];u8 *o=pkt+2;unsigned int off,n,i;u32 dsum;u16 c;int rc;
 for(off=0;off<cal->size;off+=n){
  n=min_t(unsigned int,cal->size-off,1008);memset(pkt,0,sizeof(pkt));pkt[0]=0x18;pkt[1]=0xe1;
  o[0]=0x30;o[1]=1;o[2]=n>>10;o[3]=n>>2;put32(o+4,addr+off);c=sum(o+2,6);o[8]=c>>8;o[9]=c;
  dsum=0;for(i=0;i<n;i+=4){u32 v=get_unaligned_le32(cal->data+off+i);put32(o+10+i,v);dsum+=sum(o+10+i,4);}
  put32(o+10+n,dsum);rc=transfer(spi,cs,pkt,NULL,n+16);if(rc)return rc;msleep(200);
  rc=ack(spi,cs,0x4bc1);if(rc)return rc;
 }
 pr_info(TAG "panel calibration accepted (%zu bytes)\n",cal->size);return 0;
}
static int command(void __iomem *spi,struct gpio_desc *cs,u8 *c,u8 *r){u16 checksum=sum(c,14);c[14]=checksum;c[15]=checksum>>8;return transfer(spi,cs,c,r,16);}
static int reports(void __iomem *spi,struct gpio_desc *cs){
 const u8 ids[]={0xd1,0xd3,0xd0,0xa1,0xd9,0xab,0xbf,0xaf};u8 c[16],r[16];int i,rc;
 for(i=0;i<ARRAY_SIZE(ids);i++){
  memset(c,0,16);c[0]=0xe3;c[1]=ids[i];rc=command(spi,cs,c,r);if(rc)return rc;
  rc=command(spi,cs,c,r);if(rc)return rc;
  pr_info(TAG "REPORT id=%02x RX=%*ph valid=%d\n",ids[i],16,r,r[0]==0xe3&&r[1]==ids[i]&&sum(r,14)==get_unaligned_le16(r+14));
 }
 return 0;
}
static int get_long(void __iomem *spi,struct gpio_desc *cs,u8 id,unsigned int len){
 u8 c[64]={0xe7,id,0,len},r[64]={0};u16 check=c[0]+id+len;int rc;
 c[14]=check;c[15]=check>>8;rc=transfer(spi,cs,c,r,16);if(rc)return rc;
 memset(c,0,sizeof(c));c[0]=0xe7;c[1]=id;c[2]=1;c[3]=len;c[len+3]=check;c[len+4]=check>>8;
 rc=transfer(spi,cs,c,r,len+5);if(rc)return rc;
 if(r[0]!=0xe7||r[1]!=id||r[2]||sum(r,len+3)!=get_unaligned_le16(r+len+3))return -EPROTO;
 if(id==0xd9){
  left=(s16)get_unaligned_le16(r+11);top=(s16)get_unaligned_le16(r+13);
  right=(s16)get_unaligned_le16(r+15);bottom=(s16)get_unaligned_le16(r+17);
  if(right<=left||bottom<=top)return -EPROTO;
  pr_info(TAG "surface x=%d..%d y=%d..%d\n",left,right,top,bottom);
 }
 return 0;
}
static int set(void __iomem *spi,struct gpio_desc *cs,u8 id,const u8 *p,u8 len){
 u8 c[16]={0xe4,id,len},r[16];int rc;memcpy(c+3,p,len);rc=command(spi,cs,c,r);if(rc)return rc;
 memset(c,0,16);c[0]=0xe1;rc=command(spi,cs,c,r);pr_info(TAG "SET id=%02x response=%*ph\n",id,16,r);return rc;
}
static int report_fingers(struct input_dev *input,const u8 *data,unsigned int len){
 unsigned int count,i;int slot,x,y;const u8 *t;bool down;
 if(len<24 || (data[0]!=0x43 && data[0]!=0x44))return -ENOMSG;
 count=data[16];if(count>10||len<24+count*30)return -EPROTO;
 for(i=0;i<count;i++){
  t=data+24+30*i;down=t[1]==3||t[1]==4;
  slot=input_mt_get_slot_by_key(input,t[0]);if(slot<0)continue;
  input_mt_slot(input,slot);input_mt_report_slot_state(input,MT_TOOL_FINGER,down);
  if(down){
   x=((int)(s16)get_unaligned_le16(t+4)-left)*4095/(right-left);
   y=(bottom-(int)(s16)get_unaligned_le16(t+6))*4095/(bottom-top);
   input_report_abs(input,ABS_MT_POSITION_X,clamp(x,0,4095));
   input_report_abs(input,ABS_MT_POSITION_Y,clamp(y,0,4095));
  }
 }
 input_mt_sync_frame(input);input_sync(input);finger_frames++;return 0;
}
static int capture(void __iomem *spi,struct gpio_desc *cs){
 static u8 q[2048],r[2048];const u8 bf[]={0x9b,0x0b,0x0b,2},zero[]={0};
 struct input_dev *input=NULL;unsigned int seq=1,len,n,plen,i;u16 check;int rc;
 rc=get_long(spi,cs,0xd9,16);if(rc)return rc;
 rc=get_long(spi,cs,0xd3,12);if(rc)return rc;
 rc=set(spi,cs,0xab,zero,1);if(rc)return rc;
 for(i=0;i<2;i++){rc=set(spi,cs,0xbf,bf,4);if(rc)return rc;rc=set(spi,cs,0xaf,zero,1);if(rc)return rc;}
 input=input_allocate_device();if(!input)return -ENOMEM;
 input->name="J86 native touchscreen";input->phys="j86/spi1";input->id.bustype=BUS_SPI;
 __set_bit(INPUT_PROP_DIRECT,input->propbit);
 input_set_abs_params(input,ABS_MT_POSITION_X,0,4095,0,0);
 input_set_abs_params(input,ABS_MT_POSITION_Y,0,4095,0,0);
 rc=input_mt_init_slots(input,10,INPUT_MT_DIRECT|INPUT_MT_DROP_UNUSED);if(rc){input_free_device(input);return rc;}
 rc=input_register_device(input);if(rc){input_free_device(input);return rc;}
 WRITE_ONCE(state,2);pr_info(TAG "J86_TOUCH_INPUT_READY; normalized4095, Y inverted\n");
 while(READ_ONCE(enabled)&&!kthread_should_stop()){
  memset(q,0,16);q[0]=0xeb;q[1]=seq;rc=command(spi,cs,q,r);if(rc)break;
  /* No queued result can be an allzero response; avoid logging idle reads. */
  if((r[0]&0xf0)!=0xe0 || sum(r,14)!=get_unaligned_le16(r+14)){msleep(5);continue;}
  len=get_unaligned_le16(r+1);if(!len){msleep(5);continue;}
  if(len>1944||len<2){invalid_frames++;msleep(5);continue;}
  n=max(len+5,16U);memset(q,0,n);q[0]=0xeb;q[1]=seq;q[2]=1;check=sum(q,14);q[n-2]=check;q[n-1]=check>>8;
  rc=transfer(spi,cs,q,r,n);if(rc)break;plen=get_unaligned_le16(r+2);
  if((r[0]!=0xea&&r[0]!=0xeb)||r[1]!=seq||(sum(r,5)&255)||plen<2||plen+5>n||sum(r+5,plen-2)!=get_unaligned_le16(r+plen+3)){invalid_frames++;msleep(2);continue;}
  seq=seq==1?2:1;
  if(report_fingers(input,r+5,plen-2)==-EPROTO)invalid_frames++;
 }
 /* DROP_UNUSED releases every outstanding finger before removal. */
 input_mt_sync_frame(input);input_sync(input);input_unregister_device(input);
 pr_info(TAG "input stopped; finger_frames=%llu invalid_frames=%llu\n",finger_frames,invalid_frames);
 return rc;
}
static int firmware_test(void __iomem *spi,struct gpio_desc *cs,const struct firmware *fw,const struct firmware *cal){
 u8 tx[2]={0x1a,0xa1},rx[2]={0};int rc;
 rc=hbpp(spi,cs);if(rc)return rc;
 rc=transfer(spi,cs,fw->data,NULL,fw->size);if(rc)return rc;
 msleep(200);rc=transfer(spi,cs,tx,rx,2);if(rc)return rc;
 pr_info(TAG "firmware %zu bytes ACK=%02x%02x\n",fw->size,rx[0],rx[1]);
 if(rx[0]!=0x4b||rx[1]!=0xc1)return -EPROTO;
 {u8 zeros[128]={0};struct firmware prox={.size=128,.data=zeros};rc=calibration(spi,cs,&prox,0x10009600);if(rc)return rc;}
 rc=calibration(spi,cs,cal,0x10009000);if(rc)return rc;
 {u32 ver,v;u8 c[16]={0},r[16]={0};u16 checksum;int i;
 rc=reg_read_chip(spi,cs,0x10008ffc,&ver);if(rc)return rc;
 if(ver!=0x434d15c0)return -ENODEV;
 rc=reg_write_chip(spi,cs,0x10003060,6089);if(rc)return rc;
 rc=reg_write_chip(spi,cs,0x1000305c,0x20);if(rc)return rc;
 rc=reg_write_chip(spi,cs,0x10003058,6);if(rc)return rc;
 rc=reg_write_chip(spi,cs,0x10003000,3);if(rc)return rc;
 rc=reg_write_chip(spi,cs,0x10003518,1);if(rc)return rc;
 rc=reg_read_chip(spi,cs,0x10003800,&v);if(rc)return rc;
 c[0]=0x1f;c[1]=1;rc=transfer(spi,cs,c,r,2);if(rc)return rc;msleep(165);
 rc=ack(spi,cs,0x4969);if(rc)return rc;
 memset(c,0,16);c[0]=0x1d;c[1]=0x53;put32(c+2,0x10003400);put32(c+6,1);
 checksum=sum(c+2,8);c[10]=checksum>>8;c[11]=checksum;
 rc=transfer(spi,cs,c,NULL,12);if(rc)return rc;msleep(240);spi_divisor=60;
 for(i=0;i<3;i++){
  memset(c,0,16);c[0]=i==0?0xee:0xe2;checksum=sum(c,14);c[14]=checksum;c[15]=checksum>>8;
  rc=transfer(spi,cs,c,r,16);if(rc)return rc;
  pr_info(TAG "postboot cmd=%02x RX=%*ph\n",c[0],16,r);msleep(2);
 }
 if(r[0]!=0xe2||sum(r,14)!=get_unaligned_le16(r+14))return -EPROTO;
 pr_info(TAG "J86_FIRMWARE_EXECUTE_PASS family=%02x packet=%u\n",r[1],get_unaligned_le16(r+3));
 rc=reports(spi,cs);if(rc)return rc;
 rc=capture(spi,cs);if(rc)return rc;
 }
 return 0;
}
static int run_touch(void) {
 struct device *pmic=NULL,*pins=NULL,*dev=NULL;
 const struct firmware *fw=NULL,*cal=NULL;
 struct gpio_device *gdev=NULL; struct gpio_desc *reset_desc=NULL,*cs_desc=NULL,*sync_desc=NULL;
 struct regmap *map=NULL,*pinmap=NULL;
 struct device *spidev=NULL;struct of_phandle_args spispec={.args_count=0};
 void __iomem *spi=NULL,*spipower=NULL;u32 spibefore=0,spisave[8];
 const u32 spioffs[]={0,4,12,0x30,0x34,0x38,0x4c,8};
 bool spiattached=false,spienabled=false,spiactive=false,spisaved=false;
 struct of_phandle_args spec={.args_count=0};
 void __iomem *pwm=NULL,*power=NULL;
 unsigned int ana=0,ldo=0,reset=0,cs=0,sync=0,v=0;
 u32 original_power=0,high=0,low=0,ctrl=0;
 bool attached=false,enabled=false,active=false,claimed=false,modified=false;
 bool pwm_saved=false,pass=false,clean=true; int rc=-ENODEV,i;
 if(!of_machine_is_compatible("apple,j86") || PAGE_SIZE!=4096 ||
 strcmp(utsname()->release,"7.0.12-gdfa4d4208131-dirty"))return -ENODEV;
 rc=request_firmware(&fw,"j86-touch-C1F14-3.bin",NULL);if(rc)goto out;
 if(fw->size!=57192){rc=-EINVAL;goto out;}
 rc=request_firmware(&cal,"j86-touch-panel-cal.bin",NULL);if(rc)goto out;
 if(cal->size!=1024){rc=-EINVAL;goto out;}
 pmic=bus_find_device_by_name(&i2c_bus_type,NULL,"0-003c");
 pins=bus_find_device_by_name(&platform_bus_type,NULL,"20e300000.pinctrl");
 if(!pmic || !pins || !pmic->of_node || !of_device_is_compatible(pmic->of_node,"apple,anya-pmic"))goto out;
 map=dev_get_regmap(pmic,NULL);pinmap=dev_get_regmap(pins,NULL);
 if(!map||!pinmap)goto out;
 rc=regmap_read(map,0x84,&ana);if(rc)goto out;
 rc=regmap_read(map,0x85,&ldo);if(rc)goto out;
 rc=regmap_read(pinmap,23*4,&reset);if(rc)goto out;
 rc=regmap_read(pinmap,71*4,&cs);if(rc)goto out;
 rc=regmap_read(pinmap,119*4,&sync);if(rc)goto out;
 /* Require both rails off, reset already output-low, CS output-high. */
 if((ana&4)||(ldo&2)||(reset&0x6f)!=2||(cs&0x6f)!=3){rc=-EBUSY;goto out;}
 gdev=gpio_device_find_by_fwnode(dev_fwnode(pins));if(!gdev){rc=-ENODEV;goto out;}
 reset_desc=gpiochip_request_own_desc(gpio_device_get_chip(gdev),23,"j86-touch-reset-probe",GPIO_ACTIVE_HIGH,GPIOD_ASIS);
 if(IS_ERR(reset_desc)){rc=PTR_ERR(reset_desc);reset_desc=NULL;goto out;}claimed=true;
 cs_desc=gpiochip_request_own_desc(gpio_device_get_chip(gdev),71,"j86-touch-cs-probe",GPIO_ACTIVE_HIGH,GPIOD_ASIS);
 if(IS_ERR(cs_desc)){rc=PTR_ERR(cs_desc);cs_desc=NULL;goto out;}
 sync_desc=gpiochip_request_own_desc(gpio_device_get_chip(gdev),119,"j86-touch-sync-probe",GPIO_ACTIVE_HIGH,GPIOD_ASIS);
 if(IS_ERR(sync_desc)){rc=PTR_ERR(sync_desc);sync_desc=NULL;goto out;}
 spispec.np=of_find_node_by_path("/soc/power-management@20e000000/power-controller@200a0");
 if(!spispec.np){rc=-ENODEV;goto out;}
 spipower=ioremap(0x20e0200a0ULL,4);if(!spipower){rc=-ENOMEM;goto out;}
 spibefore=readl(spipower);if(spibefore&0xff){rc=-EBUSY;goto out;}
 spidev=root_device_register("j86-touch-spi");if(IS_ERR(spidev)){rc=PTR_ERR(spidev);spidev=NULL;goto out;}
 rc=of_genpd_add_device(&spispec,spidev);if(rc)goto out;spiattached=true;
 pm_runtime_enable(spidev);spienabled=true;rc=pm_runtime_resume_and_get(spidev);if(rc<0)goto out;spiactive=true;
 spi=ioremap(0x20a084000ULL,0x4000);if(!spi){rc=-ENOMEM;goto out;}
 for(i=0;i<8;i++)spisave[i]=readl(spi+spioffs[i]);
 spisaved=true;
 if(spisave[0]||spisave[7]){rc=-EBUSY;goto out;}

 spec.np=of_find_node_by_path("/soc/power-management@20e000000/power-controller@20070");
 if(!spec.np){rc=-ENODEV;goto out;}
 power=ioremap(0x20e020070ULL,4);if(!power){rc=-ENOMEM;goto out;}
 original_power=readl(power);if(original_power&0xff){rc=-EBUSY;goto out;}
 dev=root_device_register("j86-touch-probe");if(IS_ERR(dev)){rc=PTR_ERR(dev);dev=NULL;goto out;}
 rc=of_genpd_add_device(&spec,dev);if(rc)goto out;attached=true;
 pm_runtime_enable(dev);enabled=true;rc=pm_runtime_resume_and_get(dev);if(rc<0)goto out;active=true;
 pwm=ioremap(0x20a118000ULL,0x1000);if(!pwm){rc=-ENOMEM;goto out;}
 high=readl(pwm+0x10);low=readl(pwm+0x14);ctrl=readl(pwm+0x20);pwm_saved=true;
 if(high||low||ctrl){rc=-EBUSY;goto out;}
 /* Stock D2089 rail13 needs shared analog bits0:1. Preserve voltage. */
 modified=true;
 /* Exact stock display_sync(true): GPIO function object opcode3 -> ADT
  * altfunction2 -> provider mask0x260/value0x220 (peripheral1/inputenable).
  * AppleMultitouchSPI 0xfffffff007e975b8, GPIO 0xfffffff00859104c/8590b3c. */
 rc=regmap_update_bits(pinmap,119*4,0x260,0x220);if(rc)goto out;

 rc=regmap_update_bits(map,0x84,7,7);if(rc)goto out;usleep_range(5000,6000);
 rc=regmap_update_bits(map,0x85,2,2);if(rc)goto out;usleep_range(5000,6000);
 writel(366,pwm+0x10);writel(366,pwm+0x14);writel(0x4003,pwm+0x20);
 pr_info(TAG "PWM high=%u low=%u ctrl=0x%x\n",readl(pwm+0x10),readl(pwm+0x14),readl(pwm+0x20));
 if(readl(pwm+0x10)!=366 || readl(pwm+0x14)!=366 || readl(pwm+0x20)!=0x4001){rc=-EIO;goto out;}
 usleep_range(2000,3000);
 rc=gpiod_direction_output_raw(reset_desc,1);if(rc)goto out;
 msleep(15);
 for(i=0;i<4;i++){
  rc=regmap_read(pinmap,15*4,&v);if(rc)goto out;
  pr_info(TAG "ATTN sample%d=%u\n",i,v&1);msleep(10);
 }
 rc=firmware_test(spi,cs_desc,fw,cal);pass=!rc;
out:
 if(modified){
  if(gpiod_direction_output_raw(reset_desc,0))clean=false;
  usleep_range(2000,3000);
  if(pwm){writel(0,pwm+0x20);writel(high,pwm+0x10);writel(low,pwm+0x14);writel(ctrl,pwm+0x20);}
  if(regmap_update_bits(map,0x85,2,ldo&2))clean=false;
  usleep_range(2000,3000);
  if(regmap_update_bits(map,0x84,7,ana&7))clean=false;
  if(regmap_write(pinmap,23*4,reset))clean=false;
  if(regmap_write(pinmap,119*4,sync))clean=false;
  if(regmap_read(map,0x84,&v)||v!=ana)clean=false;
  if(regmap_read(map,0x85,&v)||v!=ldo)clean=false;
  if(regmap_read(pinmap,23*4,&v)||v!=reset)clean=false;
 }
 if(spisaved && modified){
  writel(0,spi);writel(12,spi);writel(0,spi);writel(0x40000f,spi+8);
  for(i=1;i<7;i++)writel(spisave[i],spi+spioffs[i]);
  writel(spisave[0],spi);
 }
 if(spi)iounmap(spi);
 if(spiactive && pm_runtime_put_sync_suspend(spidev)<0)clean=false;
 if(spienabled)pm_runtime_disable(spidev);
 if(spiattached && pm_genpd_remove_device(spidev))clean=false;
 if(spidev)root_device_unregister(spidev);
 if(spipower){if(readl(spipower)!=spibefore)clean=false;iounmap(spipower);}
 of_node_put(spispec.np);
 if(sync_desc)gpiochip_free_own_desc(sync_desc);
 if(cs_desc){if(regmap_write(pinmap,71*4,cs))clean=false;gpiochip_free_own_desc(cs_desc);}
 if(pwm_saved && modified && (readl(pwm+0x10)!=high || readl(pwm+0x14)!=low || readl(pwm+0x20)!=ctrl))clean=false;
 if(pwm)iounmap(pwm);
 if(active && pm_runtime_put_sync_suspend(dev)<0)clean=false;
 if(enabled)pm_runtime_disable(dev);
 if(attached && pm_genpd_remove_device(dev))clean=false;
 if(dev)root_device_unregister(dev);
 if(power){if(readl(power)!=original_power)clean=false;iounmap(power);}
 of_node_put(spec.np);
 if(claimed)gpiochip_free_own_desc(reset_desc);
 if(gdev)gpio_device_put(gdev);
 if(pins)put_device(pins);
 if(pmic)put_device(pmic);
 release_firmware(cal);release_firmware(fw);
 pr_info(TAG "done rc=%d pass=%d restored=%d; firmware/calibration/execute test\n",rc,pass,clean);
 return pass&&clean?-ECANCELED:(rc?rc:-EIO);
}
static int touch_worker(void *unused){
 while(!kthread_should_stop()){
  if(!READ_ONCE(enabled)){msleep(100);continue;}
  WRITE_ONCE(state,1);spi_divisor=480;
  last_result=run_touch();
  WRITE_ONCE(enabled,false);
  WRITE_ONCE(state,last_result==-ECANCELED?0:3);
 }
 return 0;
}
static int __init touch_init(void){
 struct task_struct *task;
 if(!of_machine_is_compatible("apple,j86")||PAGE_SIZE!=4096||strcmp(utsname()->release,"7.0.12-gdfa4d4208131-dirty"))return -ENODEV;
 task=kthread_run(touch_worker,NULL,"j86-touch");
 return IS_ERR(task)?PTR_ERR(task):0;
}
module_init(touch_init);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Exact J86 N1 touchscreen; RAM firmware, sysfs enable/stop, native multitouch");
