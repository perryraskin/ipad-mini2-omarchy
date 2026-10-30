// SPDX-License-Identifier: GPL-2.0-only
/* Bounded J86 HSIC2 PHY register inventory. No pin or PMIC write.
 * Exact 16H88 J86 ADT: usb-complex ranges maps child0 to0x20c000000; wlan reg0x60.
 * HSIC2 generic power domain0x20128 has EHCI1 as its parent.
 * Power ownership stays with the existing Linux generic power-domain provider.
 * Return an error after cleanup so it does not remain loaded on MODULE_UNLOAD=n.
 */
#include <linux/device.h>
#include <linux/err.h>
#include <linux/io.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/pm_domain.h>
#include <linux/pm_runtime.h>
#include <linux/string.h>
#include <linux/utsname.h>

#define HSIC2_BASE 0x20c000060ULL
#define HSIC2_SIZE 0x10
#define HSIC2_PMGR 0x20e020128ULL
#define TAG "j86-wifi-phy-probe: "

static int __init j86_wifi_phy_probe_init(void)
{
 const char *domain_path = "/soc/power-management@20e000000/power-controller@20128";
 struct of_phandle_args spec = { .args_count = 0 };
 struct device *dev = NULL;
 void __iomem *pmgr = NULL, *spi = NULL;
 bool attached = false, enabled = false, active = false;
 bool observed = false, cleanup_ok = true;
 u32 before = 0, after;
 int rc, i;
 const u32 offsets[] = { 0,4,8,12 };

 if (!of_machine_is_compatible("apple,j86") || PAGE_SIZE != 4096 ||
     strcmp(utsname()->release, "7.0.12-gdfa4d4208131-dirty")) {
  pr_err(TAG "exact board/kernel/page guard refused\n");
  return -ENODEV;
 }
 spec.np = of_find_node_by_path(domain_path);
 if (!spec.np) return -ENODEV;
 pmgr = ioremap(HSIC2_PMGR, sizeof(u32));
 if (!pmgr) { rc = -ENOMEM; goto out; }
 before = readl(pmgr);
 /* Low nibbles are request/actual power. Require an unpowered controller. */
 if (before & 0xff) {
  pr_err(TAG "HSIC2 not idle/off (0x%08x); refusing ownership\n", before);
  rc = -EBUSY; goto out;
 }
 dev = root_device_register("j86-wifi-phy-probe");
 if (IS_ERR(dev)) { rc = PTR_ERR(dev); dev = NULL; goto out; }
 rc = of_genpd_add_device(&spec, dev);
 if (rc) goto out;
 attached = true;
 pm_runtime_enable(dev); enabled = true;
 rc = pm_runtime_resume_and_get(dev);
 if (rc < 0) goto out;
 active = true;
 spi = ioremap(HSIC2_BASE, HSIC2_SIZE);
 if (!spi) { rc = -ENOMEM; goto out; }
 for (i = 0; i < ARRAY_SIZE(offsets); ++i)
  pr_info(TAG "reg[0x%02x]=0x%08x\n", offsets[i], readl(spi + offsets[i]));
 observed = true; rc = 0;
out:
 if (spi) iounmap(spi);
 if (active) {
  int ret = pm_runtime_put_sync_suspend(dev);
  if (ret < 0) { pr_err(TAG "suspend cleanup failed: %d\n", ret); cleanup_ok = false; }
 }
 if (enabled) pm_runtime_disable(dev);
 if (attached) {
  int ret = pm_genpd_remove_device(dev);
  if (ret) { pr_err(TAG "domain detach failed: %d\n", ret); cleanup_ok = false; }
 }
 if (dev) root_device_unregister(dev);
 if (pmgr) {
  after = readl(pmgr);
  pr_info(TAG "power before=0x%08x after=0x%08x\n", before, after);
  if (after != before) cleanup_ok = false;
  iounmap(pmgr);
 }
 of_node_put(spec.np);
 if (observed && !rc && cleanup_ok) {
  pr_info(TAG "J86_HSIC2_READ_PROBE_PASS; no SPI/GPIO/PMIC write; power restored\n");
  return -ECANCELED;
 }
 pr_err(TAG "probe stopped rc=%d cleanup_ok=%d\n", rc, cleanup_ok);
 return rc ? rc : -EIO;
}
module_init(j86_wifi_phy_probe_init);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Bounded exact-J86 HSIC2 PHY read-only inventory");
