// SPDX-License-Identifier: GPL-2.0-only
/* Exact J86 internal EHCI1 control. Starts disabled. Only the reviewed overlay
 * is added/removed; Lightning USB and iPad internal storage are not touched.
 * Keep a module reference while active so unloading cannot orphan an overlay.
 */
#include <linux/module.h>
#include <linux/of.h>
#include <linux/io.h>
#include <linux/mutex.h>
#include <linux/utsname.h>
#include <generated/utsrelease.h>
#include "j86_overlay_blob.h"
static DEFINE_MUTEX(j86_host_lock);
static bool enabled;
static int overlay_id;
static u32 original_power;
static bool j86_match(u32 phandle,const char *path)
{
 struct device_node *a=of_find_node_by_phandle(phandle),*b=of_find_node_by_path(path);
 bool result=a&&a==b;
 of_node_put(a);of_node_put(b);return result;
}
static int j86_guard(void)
{
 if(!of_machine_is_compatible("apple,j86") || PAGE_SIZE!=4096 || strcmp(utsname()->release,UTS_RELEASE))return -ENODEV;
 if(!j86_match(0x20,"/soc/pinctrl@20e300000") ||
    !j86_match(1,"/soc/interrupt-controller@20e100000") ||
    !j86_match(0x18,"/soc/power-management@20e000000/power-controller@20180"))return -EINVAL;
 return 0;
}
static int j86_host_set(const char *value,const struct kernel_param *kp)
{
 struct device_node *node;
 void __iomem *power;
 bool desired;
 int rc=kstrtobool(value,&desired);
 u32 after;
 if(rc)return rc;
 rc=j86_guard();if(rc)return rc;
 mutex_lock(&j86_host_lock);
 if(desired==enabled){rc=0;goto unlock;}
 power=ioremap(0x20e020180ULL,4);
 if(!power){rc=-ENOMEM;goto unlock;}
 if(desired){
  node=of_find_node_by_path("/soc/bus@20c000000/usb-ehci@20c400000");
  if(node){of_node_put(node);rc=-EBUSY;goto unmap;}
  original_power=readl(power);
  if(original_power&0xff){rc=-EBUSY;goto unmap;}
  if(!try_module_get(THIS_MODULE)){rc=-EBUSY;goto unmap;}
  rc=of_overlay_fdt_apply(j86_overlay_blob,sizeof(j86_overlay_blob),&overlay_id,NULL);
  if(rc){module_put(THIS_MODULE);goto unmap;}
  enabled=true;
  pr_info("j86-wifi-host: exact EHCI1 overlay active; firmware/RF qualification is separate\n");
 }else{
  rc=of_overlay_remove(&overlay_id);
  if(rc){pr_err("j86-wifi-host: overlay removal failed=%d; keeping active state\n",rc);goto unmap;}
  enabled=false;
  after=readl(power);
  pr_info("j86-wifi-host: stopped power_before=%08x after=%08x restored=%d\n",original_power,after,after==original_power);
  module_put(THIS_MODULE);
  if(after!=original_power)rc=-EIO;
 }
unmap:
 iounmap(power);
unlock:
 mutex_unlock(&j86_host_lock);return rc;
}
static const struct kernel_param_ops j86_host_ops={.set=j86_host_set,.get=param_get_bool};
module_param_cb(enabled,&j86_host_ops,&enabled,0600);
MODULE_PARM_DESC(enabled,"Enable exact J86 internal USB host; disable removes overlay and resets Wi-Fi");
static int __init j86_host_init(void){return j86_guard();}
module_init(j86_host_init);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Exact J86 reversible internal Wi-Fi host control; disabled by default");
