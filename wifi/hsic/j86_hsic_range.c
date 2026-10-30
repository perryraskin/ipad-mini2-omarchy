// SPDX-License-Identifier: GPL-2.0-only
/* Exact J86 HSIC2 PHY, based on the matching stock ADT and wake sequence.
 * ADT ranges resolve0x60 to0x20c000060, not the separate remapper.
 * Never touches the Lightning gadget PHY or USB-complex global controls.
 */
#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/phy/phy.h>
#include <linux/of.h>
#include <linux/i2c.h>
#include <linux/regmap.h>
#include <linux/gpio/consumer.h>
#include <linux/delay.h>
#include <linux/io.h>
#include <linux/pm_runtime.h>
#include <linux/pm_domain.h>
struct j86_hsic_range {
 struct device *pmic, *pins;
 struct regmap *reset, *pinmap;
 struct gpio_desc *host;
 void __iomem *base;
 u32 regs[4];
 unsigned int reset_before, host_before;
 bool active;
};
static int j86_hsic_range_off(struct phy *phy)
{
 struct j86_hsic_range *p=phy_get_drvdata(phy);
 int rc=0, r;
 if(!p->active)return 0;
 r=regmap_write(p->reset,0x403,p->reset_before);if(r)rc=r;
 r=regmap_write(p->pinmap,163*4,p->host_before);if(r)rc=r;
 writel(p->regs[0],p->base);
 p->active=false;
 return rc;
}
static int j86_hsic_range_on(struct phy *phy)
{
 struct j86_hsic_range *p=phy_get_drvdata(phy);
 int rc,i;
 if(p->active)return 0;
 rc=regmap_read(p->reset,0x403,&p->reset_before);if(rc)return rc;
 rc=regmap_read(p->pinmap,163*4,&p->host_before);if(rc)return rc;
 if(p->reset_before!=0x09)return -EBUSY;
 for(i=0;i<4;i++)p->regs[i]=readl(p->base+4*i);
 if(p->regs[0]!=4||p->regs[1]!=0xc||p->regs[2]!=0x153||p->regs[3]!=0x08000000)return -EBUSY;
 p->active=true;
 writel(p->regs[0]|3,p->base);
 writel(readl(p->base)&~0x26U,p->base);udelay(20);
 writel(readl(p->base)&~1U,p->base);usleep_range(1000,1200);
 rc=gpiod_direction_output_raw(p->host,1);if(rc)goto fail;
 usleep_range(10000,12000);
 rc=regmap_update_bits(p->reset,0x403,2,2);if(rc)goto fail;
 usleep_range(10000,12000);
 return 0;
fail:
 j86_hsic_range_off(phy);return rc;
}
static const struct phy_ops j86_hsic_range_ops={.owner=THIS_MODULE,.power_on=j86_hsic_range_on,.power_off=j86_hsic_range_off};
static void j86_hsic_range_put(void *arg){put_device(arg);}
static void j86_hsic_range_domain_remove(void *arg){pm_genpd_remove_device(arg);}
static void j86_hsic_range_pm_disable(void *arg){pm_runtime_disable(arg);}
static int j86_hsic_range_probe(struct platform_device *pdev)
{
 struct j86_hsic_range *p;
 struct phy *phy;
 struct phy_provider *provider;
 struct resource *res;
 struct of_phandle_args domain={.args_count=0};
 int rc;
 if(!of_machine_is_compatible("apple,j86")||PAGE_SIZE!=4096)return -ENODEV;
 res=platform_get_resource(pdev,IORESOURCE_MEM,0);
 if(!res||res->start!=0x20c000060ULL||resource_size(res)!=0x10)return -EINVAL;
 p=devm_kzalloc(&pdev->dev,sizeof(*p),GFP_KERNEL);if(!p)return -ENOMEM;
 p->pmic=bus_find_device_by_name(&i2c_bus_type,NULL,"0-003c");
 if(!p->pmic)return -EPROBE_DEFER;
 rc=devm_add_action_or_reset(&pdev->dev,j86_hsic_range_put,p->pmic);if(rc)return rc;
 if(!of_device_is_compatible(p->pmic->of_node,"apple,anya-pmic"))return -ENODEV;
 p->pins=bus_find_device_by_name(&platform_bus_type,NULL,"20e300000.pinctrl");
 if(!p->pins)return -EPROBE_DEFER;
 rc=devm_add_action_or_reset(&pdev->dev,j86_hsic_range_put,p->pins);if(rc)return rc;
 p->reset=dev_get_regmap(p->pmic,NULL);p->pinmap=dev_get_regmap(p->pins,NULL);
 if(!p->reset||!p->pinmap)return -EPROBE_DEFER;
 p->host=devm_gpiod_get(&pdev->dev,"host-ready",GPIOD_ASIS);
 if(IS_ERR(p->host))return PTR_ERR(p->host);
 /* ADT ranges, not the parent remapper reg, translate child0x60.
  * This disjoint resource excludes the active Lightning PHY0x20..0x3f. */
 p->base=devm_platform_ioremap_resource(pdev,0);
 if(IS_ERR(p->base))return PTR_ERR(p->base);
 domain.np=of_find_node_by_path("/soc/power-management@20e000000/power-controller@20128");
 if(!domain.np)return -ENODEV;
 rc=of_genpd_add_device(&domain,&pdev->dev);of_node_put(domain.np);if(rc)return rc;
 rc=devm_add_action_or_reset(&pdev->dev,j86_hsic_range_domain_remove,&pdev->dev);if(rc)return rc;
 pm_runtime_enable(&pdev->dev);
 rc=devm_add_action_or_reset(&pdev->dev,j86_hsic_range_pm_disable,&pdev->dev);if(rc)return rc;
 phy=devm_phy_create(&pdev->dev,NULL,&j86_hsic_range_ops);if(IS_ERR(phy))return PTR_ERR(phy);
 phy_set_drvdata(phy,p);
 provider=devm_of_phy_provider_register(&pdev->dev,of_phy_simple_xlate);
 return PTR_ERR_OR_ZERO(provider);
}
static const struct of_device_id j86_hsic_range_match[]={{.compatible="apple,s5l8960x-hsic-phy-range"},{}};
MODULE_DEVICE_TABLE(of,j86_hsic_range_match);
static struct platform_driver j86_hsic_range_driver={.probe=j86_hsic_range_probe,.driver={.name="j86-hsic2-range",.of_match_table=j86_hsic_range_match}};
module_platform_driver(j86_hsic_range_driver);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Exact J86 HSIC2 PHY with reversible Wi-Fi reset and host-ready");
