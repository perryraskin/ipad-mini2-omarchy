// SPDX-License-Identifier: GPL-2.0-only
/* Bounded J86 SIO control inventory. No SIO, pin or PMIC write.
 * Hardware mapping: exact 16H88 stock/live J86 ADT, SIO at arm-io+0xae00000.
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
#include <generated/utsrelease.h>

#define SIO_BASE 0x20ae00000ULL
#define SIO_SIZE 0x2000
#define SIO_PMGR 0x20e020108ULL
#define TAG "j86-sio-inventory: "

static int __init j86_sio_inventory_init(void)
{
 const char *domain_path = "/soc/power-management@20e000000/power-controller@20108";
 struct of_phandle_args spec = { .args_count = 0 };
 struct device *dev = NULL;
 void __iomem *pmgr = NULL, *sio = NULL;
 bool attached = false, enabled = false, active = false;
 bool observed = false, cleanup_ok = true;
 u32 before = 0, after, first[10], second[10];
 int rc, i;
 /* Passive mapping/control snapshot. Status reads are the same non-consuming
  * reads used by stock A7 empty checks. Never read the RX message FIFO. */
 const u32 offsets[] = { 0x08, 0x0c, 0x10, 0x14, 0x18, 0x1c,
                         0x20, 0x28, 0x1008, 0x1020 };

 if (!of_machine_is_compatible("apple,j86") || PAGE_SIZE != 4096 ||
     strcmp(utsname()->release, UTS_RELEASE)) {
  pr_err(TAG "exact board/kernel/page guard refused\n");
  return -ENODEV;
 }
 spec.np = of_find_node_by_path(domain_path);
 if (!spec.np) return -ENODEV;
 pmgr = ioremap(SIO_PMGR, sizeof(u32));
 if (!pmgr) { rc = -ENOMEM; goto out; }
 before = readl(pmgr);
 /* Low nibbles are request/actual power. Only accept fully off or fully on; never take ownership of an active domain. */
 if ((before & 0xff) == 0xff) {
  pr_info(TAG "active domain: passive control reads only; no power reference\n");
  goto read_controls;
 }
 if (before & 0xff) {
  pr_err(TAG "SIO not idle/off (0x%08x); refusing ownership\n", before);
  rc = -EBUSY; goto out;
 }
 dev = root_device_register("j86-sio-inventory");
 if (IS_ERR(dev)) { rc = PTR_ERR(dev); dev = NULL; goto out; }
 rc = of_genpd_add_device(&spec, dev);
 if (rc) goto out;
 attached = true;
 pm_runtime_enable(dev); enabled = true;
 rc = pm_runtime_resume_and_get(dev);
 if (rc < 0) goto out;
 active = true;
read_controls:
 sio = ioremap(SIO_BASE, SIO_SIZE);
 if (!sio) { rc = -ENOMEM; goto out; }
 for (i = 0; i < ARRAY_SIZE(offsets); ++i)
  first[i] = readl(sio + offsets[i]);
 for (i = 0; i < ARRAY_SIZE(offsets); ++i) {
  second[i] = readl(sio + offsets[i]);
  pr_info(TAG "reg[0x%04x]=0x%08x stable=%d\n",
          offsets[i], first[i], first[i] == second[i]);
  if (first[i] != second[i]) cleanup_ok = false;
 }
 observed = true; rc = 0;
out:
 if (sio) iounmap(sio);
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
  pr_info(TAG "J86_SIO_INVENTORY_PASS; no SIO/FIFO/GPIO/PMIC write; power unchanged/restored\n");
  return -ECANCELED;
 }
 pr_err(TAG "probe stopped rc=%d cleanup_ok=%d\n", rc, cleanup_ok);
 return rc ? rc : -EIO;
}
module_init(j86_sio_inventory_init);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Bounded exact-J86 SIO control-only inventory");
