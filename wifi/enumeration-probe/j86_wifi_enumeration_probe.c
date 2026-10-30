// SPDX-License-Identifier: GPL-2.0-only
/* Eight-second EHCI1-only observation, removed before returning. */
#include <linux/module.h>
#include <linux/of.h>
#include <linux/delay.h>
#include <linux/io.h>
#include <linux/utsname.h>
#include <linux/i2c.h>
#include <linux/platform_device.h>
#include <linux/regmap.h>
#include <linux/usb.h>
#include <linux/slab.h>
#include <linux/usb/hcd.h>
#include <linux/pm_runtime.h>
#include "j86_overlay_blob.h"
static bool matches(u32 phandle,const char *path)
{
 struct device_node *a=of_find_node_by_phandle(phandle),*b=of_find_node_by_path(path);
 bool ok=a&&a==b;
 of_node_put(a);of_node_put(b);return ok;
}
static int query_chip(struct usb_device *dev,void *unused)
{
 __le32 *id;
 int rc,i;
 if(le16_to_cpu(dev->descriptor.idVendor)!=0x0a5c ||
    le16_to_cpu(dev->descriptor.idProduct)!=0xbd1c ||
    strcmp(dev_name(dev->bus->controller),"20c400000.usb-ehci"))return 0;
 pr_info("j86-wifi-enumeration-probe: device class=%02x configurations=%u\n",dev->descriptor.bDeviceClass,dev->descriptor.bNumConfigurations);
 if(dev->actconfig)for(i=0;i<dev->actconfig->desc.bNumInterfaces;i++){
  struct usb_host_interface *a=dev->actconfig->interface[i]->cur_altsetting;
  pr_info("j86-wifi-enumeration-probe: interface=%u class=%02x/%02x/%02x endpoints=%u\n",a->desc.bInterfaceNumber,a->desc.bInterfaceClass,a->desc.bInterfaceSubClass,a->desc.bInterfaceProtocol,a->desc.bNumEndpoints);
 }
 id=kzalloc(24,GFP_KERNEL);if(!id)return -ENOMEM;
 /* Same read-only boot-ROM identity request as brcmfmac DL_GETVER. */
 rc=usb_control_msg(dev,usb_rcvctrlpipe(dev,0),5,USB_DIR_IN|USB_TYPE_VENDOR|USB_RECIP_INTERFACE,0,0,id,24,1000);
 if(rc>=12)pr_info("j86-wifi-enumeration-probe: bootrom rc=%d chip=%08x revision=%u ram=%u boardtype=%x boardrev=%x\n",rc,le32_to_cpu(id[0]),le32_to_cpu(id[1]),le32_to_cpu(id[2]),le32_to_cpu(id[4]),le32_to_cpu(id[5]));
 else pr_info("j86-wifi-enumeration-probe: bootrom identity request rc=%d\n",rc);
 kfree(id);return 0;
}
static void sample(void)
{
 void __iomem *regs=ioremap(0x20c000000ULL,0x80),*ehci=ioremap(0x20c400000ULL,0x80),*pm=ioremap(0x20e020128ULL,4);
 struct device *dev=bus_find_device_by_name(&i2c_bus_type,NULL,"0-003c");
 unsigned int reset=0;
 if(dev){struct regmap *map=dev_get_regmap(dev,NULL);if(map)regmap_read(map,0x403,&reset);put_device(dev);}
 if(regs&&ehci&&pm)pr_info("j86-wifi-enumeration-probe: ctl=%08x ehci1ctl=%08x ehci1cfg=%08x hsic=%08x domain=%08x cmd=%08x status=%08x port=%08x reset=%02x\n",readl(regs),readl(regs+8),readl(regs+12),readl(regs+0x60),readl(pm),readl(ehci+0x10),readl(ehci+0x14),readl(ehci+0x54),reset);
 if(regs)iounmap(regs);
 if(ehci)iounmap(ehci);
 if(pm)iounmap(pm);
}
static int __init j86_wifi_enumeration_probe_init(void)
{
 struct device_node *node;
 struct device *host=NULL,*hub=NULL;
 bool hub_active=false;
 void __iomem *power;
 u32 before,after;
 int id=0,rc,remove_rc;
 if(!of_machine_is_compatible("apple,j86")||PAGE_SIZE!=4096||strcmp(utsname()->release,"7.0.12-gdfa4d4208131-dirty"))return -ENODEV;
 if(!matches(0x20,"/soc/pinctrl@20e300000")||!matches(1,"/soc/interrupt-controller@20e100000")||!matches(0x18,"/soc/power-management@20e000000/power-controller@20180"))return -EINVAL;
 node=of_find_node_by_path("/soc/bus@20c000000/usb-ehci@20c400000");
 if(node){of_node_put(node);return -EBUSY;}
 power=ioremap(0x20e020180ULL,4);if(!power)return -ENOMEM;
 before=readl(power);if(before&0xff){iounmap(power);return -EBUSY;}
 rc=of_overlay_fdt_apply(j86_overlay_blob,sizeof(j86_overlay_blob),&id,NULL);
 if(rc){pr_err("j86-wifi-enumeration-probe: overlay apply rc=%d\n",rc);goto out;}
 pr_info("j86-wifi-enumeration-probe: EHCI1 observation active for8seconds\n");
 msleep(200);
 host=bus_find_device_by_name(&platform_bus_type,NULL,"20c400000.usb-ehci");
 if(host&&host->driver){
  struct usb_hcd *hcd=dev_get_drvdata(host);
  if(hcd&&hcd->self.root_hub){
   hub=get_device(&hcd->self.root_hub->dev);
   rc=pm_runtime_resume_and_get(hub);
   pr_info("j86-wifi-enumeration-probe: hold root hub awake rc=%d\n",rc);
   if(rc>=0){hub_active=true;rc=0;}
  }
 }
 msleep(800);sample();
 msleep(6000);sample();usb_for_each_dev(NULL,query_chip);msleep(1000);
 if(hub_active)pm_runtime_put_sync(hub);
 if(hub)put_device(hub);
 if(host)put_device(host);
 remove_rc=of_overlay_remove(&id);
 if(remove_rc){pr_err("j86-wifi-enumeration-probe: OVERLAY REMOVE FAILED rc=%d; inspect before further work\n",remove_rc);rc=remove_rc;}
out:
 after=readl(power);iounmap(power);
 pr_info("j86-wifi-enumeration-probe: rc=%d power_before=%08x after=%08x restored=%d\n",rc,before,after,after==before);
 return rc?rc:(after==before?-ECANCELED:-EIO);
}
module_init(j86_wifi_enumeration_probe_init);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Bounded exact J86 internal Wi-Fi EHCI1 enumeration observation");
