// SPDX-License-Identifier: GPL-2.0-only
/* Bounded J86 MCA1 controller inventory. No audio, pin or PMIC write.
 * Hardware mapping: exact 16H88 stock/live J86 ADT, MCA1 at arm-io+0xa0c4000.
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

#define MCA1_BASE 0x20a0c4000ULL
#define MCA1_SIZE 0x4000
#define MCA1_PMGR 0x20e020050ULL
#define TAG "j86-audio-controller-probe: "

static int __init j86_audio_controller_probe_init(void)
{
 const char *domain_path = "/soc/power-management@20e000000/power-controller@20050";
 struct of_phandle_args spec = { .args_count = 0 };
 struct device *dev = NULL;
 void __iomem *pmgr = NULL, *mca = NULL;
 bool attached = false, enabled = false, active = false;
 bool observed = false, cleanup_ok = true;
 u32 before = 0, after;
 int rc, i;
 const u32 offsets[] = { 0,4,8,12,16,20,24,28,32,36,44,48,52,56,64,68,72 };

 if (!of_machine_is_compatible("apple,j86") || PAGE_SIZE != 4096 ||
     strcmp(utsname()->release, UTS_RELEASE)) {
  pr_err(TAG "exact board/kernel/page guard refused\n");
  return -ENODEV;
 }
 spec.np = of_find_node_by_path(domain_path);
 if (!spec.np) return -ENODEV;
 pmgr = ioremap(MCA1_PMGR, sizeof(u32));
 if (!pmgr) { rc = -ENOMEM; goto out; }
 before = readl(pmgr);
 /* Low nibbles are request/actual power. Require an unpowered controller. */
 if (before & 0xff) {
  pr_err(TAG "MCA1 not idle/off (0x%08x); refusing ownership\n", before);
  rc = -EBUSY; goto out;
 }
 dev = root_device_register("j86-audio-controller-probe");
 if (IS_ERR(dev)) { rc = PTR_ERR(dev); dev = NULL; goto out; }
 rc = of_genpd_add_device(&spec, dev);
 if (rc) goto out;
 attached = true;
 pm_runtime_enable(dev); enabled = true;
 rc = pm_runtime_resume_and_get(dev);
 if (rc < 0) goto out;
 active = true;
 mca = ioremap(MCA1_BASE, MCA1_SIZE);
 if (!mca) { rc = -ENOMEM; goto out; }
 for (i = 0; i < ARRAY_SIZE(offsets); ++i)
  pr_info(TAG "reg[0x%02x]=0x%08x\n", offsets[i], readl(mca + offsets[i]));
 {
  void __iomem *nco=ioremap(0x20e012000ULL,0x14);
  if(!nco){rc=-ENOMEM;goto out;}
  for(i=0;i<5;i++)pr_info(TAG "nco1[0x%02x]=0x%08x\n",4*i,readl(nco+4*i));
  iounmap(nco);
 }
 observed = true; rc = 0;
out:
 if (mca) iounmap(mca);
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
  pr_info(TAG "J86_MCA1_INVENTORY_PASS; no audio/GPIO/PMIC write; power restored\n");
  return -ECANCELED;
 }
 pr_err(TAG "probe stopped rc=%d cleanup_ok=%d\n", rc, cleanup_ok);
 return rc ? rc : -EIO;
}
module_init(j86_audio_controller_probe_init);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Bounded exact-J86 MCA1 controller-only inventory");
