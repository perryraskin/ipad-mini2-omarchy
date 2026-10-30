// SPDX-License-Identifier: GPL-2.0-only OR MIT
/* Experimental attach-only Oscar receive transport. No reset, firmware upload,
 * subscriptions or IIO claims. Requires an independently configured live M7.
 */
#include <linux/module.h>
#include <linux/of.h>
#include <linux/of_address.h>
#include <linux/serdev.h>
#include "j86-oscar-rx.h"
static bool allow_running_attach;
module_param(allow_running_attach, bool, 0444);
MODULE_PARM_DESC(allow_running_attach, "Opt in to unqualified running-M7 RX attachment (default off)");
struct j86_oscar { struct j86_oscar_rx rx; };
static void oscar_frame(void *ctx, const u8 *frame, unsigned int length)
{
 struct device *dev=ctx;
 /* No raw payload or calibration logging; no invented report decoding. */
 dev_dbg_ratelimited(dev,"validated IPC channel=%u command=%u length=%u\n",
  frame[4],frame[12] | (frame[13]<<8),length);
}
static size_t oscar_receive(struct serdev_device *serdev,const u8 *data,size_t count)
{
 struct j86_oscar *oscar=serdev_device_get_drvdata(serdev);
 j86_oscar_feed(&oscar->rx,data,count,oscar_frame,&serdev->dev);
 return count;
}
static const struct serdev_device_ops oscar_ops={ .receive_buf=oscar_receive };
static int oscar_probe(struct serdev_device *serdev)
{
 struct device *dev=&serdev->dev;
 struct resource resource;
 struct j86_oscar *oscar;
 u32 baud;
 int ret;
 if (!allow_running_attach) return -EPERM;
 if (!of_machine_is_compatible("apple,j86") || PAGE_SIZE!=4096) return -ENODEV;
 if (!of_property_read_bool(dev->of_node,"apple,attach-running-firmware")) return -EPERM;
 if (of_address_to_resource(dev->of_node->parent,0,&resource) ||
     resource.start!=0x20a0b0000ULL || resource_size(&resource)!=0x4000) return -ENODEV;
 /* Baud must come from independently qualified UART evidence, never a default. */
 ret=of_property_read_u32(dev->of_node,"current-speed",&baud);
 if (ret || baud<9600 || baud>4000000) return -EINVAL;
 oscar=devm_kzalloc(dev,sizeof(*oscar),GFP_KERNEL);
 if (!oscar) return -ENOMEM;
 serdev_device_set_drvdata(serdev,oscar);
 serdev_device_set_client_ops(serdev,&oscar_ops);
 ret=devm_serdev_device_open(dev,serdev);
 if (ret) return ret;
 if (serdev_device_set_baudrate(serdev,baud)!=baud) return -ERANGE;
 serdev_device_set_flow_control(serdev,false);
 dev_info(dev,"experimental receive-only attach; no sensor subscription or IIO device\n");
 return 0;
}
static int oscar_suspend(struct device *dev)
{
 /* UART/M7 wake and resume are not qualified; never silently suspend RX. */
 return -EBUSY;
}
static const struct dev_pm_ops oscar_pm={ .suspend=oscar_suspend };
static const struct of_device_id oscar_match[]={
 { .compatible="apple,j86-oscar-experimental" },{}
};
MODULE_DEVICE_TABLE(of,oscar_match);
static struct serdev_device_driver oscar_driver={
 .probe=oscar_probe,
 .driver={ .name="j86-oscar-experimental",.of_match_table=oscar_match,.pm=&oscar_pm },
};
module_serdev_device_driver(oscar_driver);
MODULE_LICENSE("Dual MIT/GPL");
MODULE_DESCRIPTION("Disabled exact-J86 running-M7 receive transport experiment");
