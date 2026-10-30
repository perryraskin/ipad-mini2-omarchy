/* SPDX-License-Identifier: GPL-2.0-only */
/* Exact4324 stock16H88 OTP table: 0x18000800,0x18000838,0x1800083a.
 * AppleBCMWLANBusInterfaceHSIC factory0x80bf798 selects chip4324;
 * vslot90=0x80bf6b4 indexes this table. Only USB RDHW16 reads are used.
 * Raw OTP/CIS, MAC and calibration values are never logged or persisted.
 */
#include <linux/unaligned.h>
#include <linux/ktime.h>
#ifdef J86_WIFI_OTP_EXPORT
static u8 j86_otp_snapshot[512];
static unsigned int j86_otp_snapshot_length;
static int j86_otp_snapshot_get(char *buffer,const struct kernel_param *kp)
{
 unsigned int i,pos=0;
 for(i=0;i<j86_otp_snapshot_length;i++)pos+=scnprintf(buffer+pos,PAGE_SIZE-pos,"%02x",j86_otp_snapshot[i]);
 return pos+scnprintf(buffer+pos,PAGE_SIZE-pos,"\n");
}
static int j86_otp_clear(const char *value,const struct kernel_param *kp)
{
 bool clear;
 int rc=kstrtobool(value,&clear);
 if(rc)return rc;
 if(!clear)return -EINVAL;
 memzero_explicit(j86_otp_snapshot,sizeof(j86_otp_snapshot));j86_otp_snapshot_length=0;
 return 0;
}
static const struct kernel_param_ops j86_otp_snapshot_ops={.get=j86_otp_snapshot_get};
static const struct kernel_param_ops j86_otp_clear_ops={.set=j86_otp_clear};
module_param_cb(snapshot,&j86_otp_snapshot_ops,NULL,0400);
module_param_cb(clear,&j86_otp_clear_ops,NULL,0200);
#endif
static int j86_otp_read16(struct usb_device *dev,u32 address,u8 *buffer,u16 *value)
{
 int rc;
 memset(buffer,0,16);
 rc=usb_control_msg(dev,usb_rcvctrlpipe(dev,0),0x11,
  USB_DIR_IN|USB_TYPE_VENDOR|USB_RECIP_INTERFACE,address&0xffff,address>>16,buffer,16,200);
 if(rc!=16)return rc<0?rc:-EIO;
 *value=get_unaligned_le16(buffer+12);return 0;
}
static int j86_wifi_read_otp(struct usb_device *dev)
{
 u8 *storage=kzalloc(528,GFP_KERNEL),*cis;
 u16 begin_field,end_field,word;
 unsigned int begin,end,length,pos,i;
 bool standard=true,have_type=false,have_revision=false;
 u16 boardtype=0,boardrev=0;
 u64 deadline=ktime_get_ns()+3000000000ULL;
 int rc;
 if(!storage)return -ENOMEM;
 cis=storage+16;
 rc=j86_otp_read16(dev,0x1800083a,storage,&end_field);if(rc)goto out;
 rc=j86_otp_read16(dev,0x18000838,storage,&begin_field);if(rc)goto out;
 begin=(begin_field>>3)&0x1fff;end=(end_field>>3)&0x1fff;
 if(end<=begin || end-begin>512 || ((end-begin)&1)){rc=-EPROTO;goto out;}
 length=end-begin;
 for(i=0;i<length;i+=2){
  if(ktime_get_ns()>deadline){rc=-ETIMEDOUT;goto out;}
  rc=j86_otp_read16(dev,0x18000800+begin+i,storage,&word);if(rc)goto out;
  put_unaligned_le16(word,cis+i);
 }
#ifdef J86_WIFI_OTP_EXPORT
 memcpy(j86_otp_snapshot,cis,length);j86_otp_snapshot_length=length;
#endif
 pos=0;
 while(pos<length){
  u8 tag,n;
  if(standard){
   tag=cis[pos++];if(tag==0xff)break;if(!tag)continue;
   if(pos>=length)break;
   n=cis[pos++];
  }else{
   n=cis[pos++];if(n==0xff)break;if(!n)continue;tag=0x80;
  }
  if(pos+n>length)break;
  if(tag==0x80 && n){
   if(cis[pos]==0x1b && n>=3){boardtype=get_unaligned_le16(cis+pos+1);have_type=true;}
   else if(cis[pos]==2 && n>=2){boardrev=n>=3?get_unaligned_le16(cis+pos+1):cis[pos+1];have_revision=true;}
   else if(cis[pos]==0x1d){standard=false;n++;}
  }
  pos+=n;
 }
 pr_info("j86-wifi-otp-probe: bounded OTP bytes=%u boardtype_present=%d boardrev_present=%d\n",length,have_type,have_revision);
 if(have_type&&have_revision)
  pr_info("j86-wifi-otp-probe: OTP_BOARD_ID boardtype=%04x boardrev=%04x; all other tuples suppressed\n",boardtype,boardrev);
 rc=have_type&&have_revision?0:-ENODATA;
out:
 pr_info("j86-wifi-otp-probe: read-only result=%d; raw OTP not logged or persisted\n",rc);
 memzero_explicit(storage,528);kfree(storage);return rc;
}
