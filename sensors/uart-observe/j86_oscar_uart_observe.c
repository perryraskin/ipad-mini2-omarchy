// SPDX-License-Identifier: GPL-2.0-only
/* Bounded J86 Oscar UART4 passive RX observation. No UART, pin or PMIC write.
 * Hardware mapping: exact 16H88 stock/live J86 ADT, UART4 at arm-io+0xa0b0000.
 * Power ownership stays with the existing Linux generic power-domain provider.
 * Return an error after cleanup so it does not remain loaded on MODULE_UNLOAD=n.
 */
#include <linux/delay.h>
#include <linux/jiffies.h>
#include "j86-oscar-rx.h"
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

#define UART4_BASE 0x20a0b0000ULL
#define UART4_SIZE 0x4000
#define UART4_PMGR 0x20e0200d8ULL
#define TAG "j86-oscar-uart-observe: "

static int __init j86_oscar_uart_observe_init(void)
{
 const char *domain_path = "/soc/power-management@20e000000/power-controller@200d8";
 struct of_phandle_args spec = { .args_count = 0 };
 struct device *dev = NULL;
 void __iomem *pmgr = NULL, *uart = NULL;
 bool attached = false, enabled = false, active = false;
 bool observed = false, cleanup_ok = true;
 u32 before = 0, after;
 struct j86_oscar_rx rx = {0};
 unsigned long deadline;
 unsigned int bytes = 0;
 int rc, i;
 /* Samsung UART control and divisor words only. Never read RX/TX FIFO,
  * clear-on-read/error/interrupt status, or issue UART commands. */
 const u32 offsets[] = { 0x00,0x04,0x08,0x0c,0x28,0x2c };

 if (!of_machine_is_compatible("apple,j86") || PAGE_SIZE != 4096 ||
     strcmp(utsname()->release, UTS_RELEASE)) {
  pr_err(TAG "exact board/kernel/page guard refused\n");
  return -ENODEV;
 }
 spec.np = of_find_node_by_path(domain_path);
 if (!spec.np) return -ENODEV;
 pmgr = ioremap(UART4_PMGR, sizeof(u32));
 if (!pmgr) { rc = -ENOMEM; goto out; }
 before = readl(pmgr);
 /* Low nibbles are request/actual power. Require an unpowered controller. */
 if (before & 0xff) {
  pr_err(TAG "UART4 not idle/off (0x%08x); refusing ownership\n", before);
  rc = -EBUSY; goto out;
 }
 dev = root_device_register("j86-oscar-uart-observe");
 if (IS_ERR(dev)) { rc = PTR_ERR(dev); dev = NULL; goto out; }
 rc = of_genpd_add_device(&spec, dev);
 if (rc) goto out;
 attached = true;
 pm_runtime_enable(dev); enabled = true;
 rc = pm_runtime_resume_and_get(dev);
 if (rc < 0) goto out;
 active = true;
 uart = ioremap(UART4_BASE, UART4_SIZE);
 if (!uart) { rc = -ENOMEM; goto out; }
 for (i = 0; i < ARRAY_SIZE(offsets); ++i)
  pr_info(TAG "reg[0x%02x]=0x%08x\n", offsets[i], readl(uart + offsets[i]));
 /* Preserve the observed inherited line configuration. No baud, FIFO,
  * IRQ, flow-control, GPIO, firmware or transmit operation is performed. */
 if (readl(uart) != 3 || readl(uart+4) != 0x405 ||
     readl(uart+8) != 1 || readl(uart+0x28) != 12 || readl(uart+0x2c)) {
  rc = -EINVAL; goto out;
 }
 deadline = jiffies + msecs_to_jiffies(2000);
 while (time_before(jiffies, deadline) && bytes < 512) {
  if (readl(uart+0x10) & 1) {
   u8 value = readl(uart+0x24);
   j86_oscar_feed(&rx, &value, 1, NULL, NULL);
   bytes++;
  } else {
   usleep_range(1000, 2000);
  }
 }
 pr_info(TAG "RX bytes=%u valid_frames=%u bad_length=%u bad_checksum=%u discarded=%u partial=%u capped=%u\n",
         bytes, rx.good, rx.bad_length, rx.bad_checksum, rx.discarded, rx.used, bytes == 512);
 observed = true; rc = 0;
out:
 if (uart) iounmap(uart);
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
  pr_info(TAG "J86_UART4_OBSERVE_PASS; no UART/FIFO/GPIO/PMIC write (RX reads consume bytes); power restored\n");
  return -ECANCELED;
 }
 pr_err(TAG "probe stopped rc=%d cleanup_ok=%d\n", rc, cleanup_ok);
 return rc ? rc : -EIO;
}
module_init(j86_oscar_uart_observe_init);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Bounded exact-J86 UART4 passive RX observation");
