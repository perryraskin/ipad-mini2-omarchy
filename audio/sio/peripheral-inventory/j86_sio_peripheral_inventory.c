// SPDX-License-Identifier: GPL-2.0-only
/* Exact J86 read-only inventory of firmware startup DMA control targets.
 * Balanced genpd references for off domains; never unbinds another driver.
 * No firmware, stream setup, controller reset or peripheral register writes.
 */
#include <linux/device.h>
#include <linux/err.h>
#include <linux/io.h>
#include <linux/ioport.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/pm_domain.h>
#include <linux/pm_runtime.h>
#include <linux/utsname.h>
#include <generated/utsrelease.h>
#define TAG "j86-sio-peripheral-inventory: "
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
static int observe(const struct target *t)
{
 struct of_phandle_args spec = {.args_count=0};
 struct device *dev = NULL;
 void __iomem *base = NULL, *pmgr = NULL;
 bool attached=false, enabled=false, active=false, claimed=false, observed=false;
 u32 before=0, after, values[2];
 char path[100], name[64];
 int rc=0, i;
 snprintf(path,sizeof(path),"/soc/power-management@20e000000/power-controller@%x",t->gate);
 spec.np=of_find_node_by_path(path);
 if (!spec.np) return -ENODEV;
 if (!request_mem_region(t->base,0x4000,"j86-sio-peripheral-inventory")) {
  pr_info(TAG "%s owned by another driver; skipped\n",t->name);
  rc=-EBUSY; goto out;
 }
 claimed=true;
 pmgr=ioremap(0x20e000000ULL+t->gate,4);
 if (!pmgr) {rc=-ENOMEM;goto out;}
 before=readl(pmgr);
 if ((before&0xff)!=0 && (before&0xff)!=0xff) {rc=-EBUSY;goto out;}
 if (!(before&0xff)) {
  snprintf(name,sizeof(name),"j86-sio-inventory-%s",t->name);
  dev=root_device_register(name);
  if (IS_ERR(dev)) {rc=PTR_ERR(dev);dev=NULL;goto out;}
  rc=of_genpd_add_device(&spec,dev);if(rc)goto out;attached=true;
  pm_runtime_enable(dev);enabled=true;
  rc=pm_runtime_resume_and_get(dev);if(rc<0)goto out;active=true;
 }
 base=ioremap(t->base,0x4000);
 if (!base) {rc=-ENOMEM;goto out;}
 /* Only the two control registers written by stock startup 0x15e6.
  * No ring addresses, FIFOs, IRQ or clear-on-read status are inspected. */
 for(i=0;i<2;++i)values[i]=readl(base+0x1010+i*0x800);
 for(i=0;i<2;++i) {
  u32 second=readl(base+0x1010+i*0x800);
  pr_info(TAG "%s direction=%d control=%08x stable=%d\n",t->name,i,values[i],values[i]==second);
  if(values[i]!=second)rc=-EAGAIN;
 }
 observed=true;
out:
 if(base)iounmap(base);
 if(active && pm_runtime_put_sync_suspend(dev)<0)rc=-EIO;
 if(enabled)pm_runtime_disable(dev);
 if(attached && pm_genpd_remove_device(dev))rc=-EIO;
 if(dev)root_device_unregister(dev);
 if(pmgr) {
  after=readl(pmgr);
  pr_info(TAG "%s power before=%08x after=%08x observed=%d rc=%d\n",t->name,before,after,observed,rc);
  if(after!=before)rc=-EIO;
  iounmap(pmgr);
 }
 if(claimed)release_mem_region(t->base,0x4000);
 of_node_put(spec.np);
 return rc;
}
static int __init probe_init(void)
{
 unsigned int i, observed=0, refused=0;
 int rc;
 if(!of_machine_is_compatible("apple,j86") || PAGE_SIZE!=4096 ||
    strcmp(utsname()->release,UTS_RELEASE))return -ENODEV;
 for(i=0;i<ARRAY_SIZE(targets);++i) {
  rc=observe(&targets[i]);
  if(rc==-EBUSY || rc==-ENODEV) {++refused;continue;}
  if(rc) {pr_err(TAG "stopped on %s rc=%d\n",targets[i].name,rc);return rc;}
  ++observed;
 }
 pr_info(TAG "READONLY_DONE observed=%u refused=%u; no peripheral writes; not ownership or DMA-idle qualification\n",observed,refused);
 return -ECANCELED;
}
module_init(probe_init);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Exact J86 shared SIO peripheral control inventory");
