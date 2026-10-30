/* SPDX-License-Identifier: GPL-2.0-only */
/* Bounded RAM-only Broadcom download, following brcmfmac USB RDL protocol.
 * Exact stock seyval image only. No nonvolatile writes, scan, interface-up or TX.
 */
#include <linux/firmware.h>
#ifdef J86_WIFI_NVRAM_PROBE
#include <linux/crc32.h>
#include <linux/hex.h>
#endif
#include <linux/unaligned.h>
#include <linux/ktime.h>
static int j86_dl_read(struct usb_device *dev,u8 command,void *buffer,u16 length)
{
 int rc=usb_control_msg(dev,usb_rcvctrlpipe(dev,0),command,
  USB_DIR_IN|USB_TYPE_VENDOR|USB_RECIP_INTERFACE,0,0,buffer,length,500);
 return rc==length?0:(rc<0?rc:-EIO);
}
static int j86_wifi_ram_firmware(struct usb_device *dev)
{
 const struct firmware *fw=NULL;
 struct usb_host_interface *iface;
 u8 *buffer=NULL,*state=NULL,*id=NULL;
 unsigned int pipe=0,sent=0,received=0,dlstate=0,i;
 int rc,actual;
#ifdef J86_WIFI_NVRAM_PROBE
 u8 expected_mac[6];
 bool have_mac=false;
#endif
 u64 deadline;
#ifdef J86_WIFI_NVRAM_PROBE
 rc=request_firmware_direct(&fw,"j86-wifi-seyval-configured-probe.trx",&dev->dev);
 if(rc)return rc;
 if(fw->size<482056 || fw->size>490244 ||
    get_unaligned_le32(fw->data)!=0x30524448 ||
    get_unaligned_le32(fw->data+4)!=fw->size ||
    get_unaligned_le32(fw->data+12)!=0x10020 ||
    get_unaligned_le32(fw->data+16)!=482024 ||
    get_unaligned_le32(fw->data+20)!=129 ||
    !get_unaligned_le32(fw->data+24) ||
    get_unaligned_le32(fw->data+24)>8192 ||
    482052+get_unaligned_le32(fw->data+24)!=fw->size ||
    crc32_le(~0U,fw->data+12,fw->size-12)!=get_unaligned_le32(fw->data+8)){
  rc=-EINVAL;goto out;
 }
 {
  const char *vars=(const char *)fw->data+482052;
  size_t left=fw->size-482052;
  while(left){
   size_t length=strnlen(vars,left);
   if(length==left){rc=-EINVAL;goto out;}
   if(length==25 && !memcmp(vars,"macaddr=",8)){
    for(i=0;i<6;i++){
     int hi=hex_to_bin(vars[8+i*3]),lo=hex_to_bin(vars[9+i*3]);
     if(hi<0||lo<0||(i<5&&vars[10+i*3]!=':')){rc=-EINVAL;goto out;}
     expected_mac[i]=(hi<<4)|lo;
    }
    have_mac=true;
   }
   vars+=length+1;left-=length+1;
  }
  if(!have_mac){rc=-EINVAL;goto out;}
 }
#else
 rc=request_firmware_direct(&fw,"j86-wifi-seyval.trx",&dev->dev);
 if(rc)return rc;
 if(fw->size!=483328 || get_unaligned_le32(fw->data)!=0x30524448 ||
    get_unaligned_le32(fw->data+4)!=483328 ||
    get_unaligned_le32(fw->data+8)!=0x7074e760 ||
    get_unaligned_le32(fw->data+12)!=0x10020){rc=-EINVAL;goto out;}
#endif
 if(!dev->actconfig){rc=-ENODEV;goto out;}
 iface=dev->actconfig->interface[0]->cur_altsetting;
 for(i=0;i<iface->desc.bNumEndpoints;i++){
  struct usb_endpoint_descriptor *ep=&iface->endpoint[i].desc;
  if(usb_endpoint_is_bulk_out(ep)){pipe=usb_sndbulkpipe(dev,usb_endpoint_num(ep));break;}
 }
 if(!pipe){rc=-ENODEV;goto out;}
 buffer=kmalloc(1500,GFP_KERNEL);state=kzalloc(8,GFP_KERNEL);id=kzalloc(24,GFP_KERNEL);
 if(!buffer||!state||!id){rc=-ENOMEM;goto out;}
 rc=j86_dl_read(dev,5,id,24);
 if(rc || get_unaligned_le32(id)!=0x4324 || get_unaligned_le32(id+4)!=6){rc=rc?rc:-ENODEV;goto out;}
 rc=j86_dl_read(dev,3,state,8);if(rc)goto out;
 if(get_unaligned_le32(state)!=0){rc=-EBUSY;goto out;}
 deadline=ktime_get_ns()+15000000000ULL;
 while(received<fw->size){
  if(ktime_get_ns()>deadline){rc=-ETIMEDOUT;goto out;}
  if(received==sent){
   unsigned int length=min_t(unsigned int,fw->size-sent,1500);
   if(!(length%64))length-=4;
   memcpy(buffer,fw->data+sent,length);
   rc=usb_bulk_msg(dev,pipe,buffer,length,&actual,500);
   if(rc || actual!=length){rc=rc?rc:-EIO;goto out;}
   sent+=length;
  }else msleep(5);
  rc=j86_dl_read(dev,0,state,8);if(rc)goto out;
  dlstate=get_unaligned_le32(state);received=get_unaligned_le32(state+4);
  if(received>sent || dlstate==2 || dlstate==3 || dlstate>4){rc=-EPROTO;goto out;}
 }
 pr_info("j86-wifi-firmware-probe: RAM download bytes=%u state=%u\n",received,dlstate);
 if(dlstate!=4){rc=-EPROTO;goto out;}
 rc=j86_dl_read(dev,2,state,8);if(rc)goto out;
 for(i=0;i<20;i++){
  msleep(100);rc=j86_dl_read(dev,5,id,24);
  if(!rc && get_unaligned_le32(id)==0xa123)break;
 }
 if(i==20){rc=rc?rc:-ETIMEDOUT;goto out;}
 rc=j86_dl_read(dev,8,id,24);if(rc)goto out;
 pr_info("j86-wifi-firmware-probe: RAM_FIRMWARE_BOOT_PASS; no RF interface-up/scan/TX requested\n");
 /* Read-only firmware version query. Do not log its returned raw buffer. */
 memset(buffer,0,1500);
 put_unaligned_le32(262,buffer);put_unaligned_le32(256,buffer+4);
 put_unaligned_le32(1U<<16,buffer+8);memcpy(buffer+16,"ver",4);
 rc=usb_control_msg(dev,usb_sndctrlpipe(dev,0),0,USB_DIR_OUT|USB_TYPE_CLASS|USB_RECIP_INTERFACE,0,0,buffer,20,500);
 if(rc!=20){rc=rc<0?rc:-EIO;goto out;}
 memset(buffer,0,1500);
 rc=usb_control_msg(dev,usb_rcvctrlpipe(dev,0),1,USB_DIR_IN|USB_TYPE_CLASS|USB_RECIP_INTERFACE,0,0,buffer,272,500);
 if(rc>=16){
  pr_info("j86-wifi-firmware-probe: version query bytes=%d cmd=%u flags=%08x status=%d\n",rc,get_unaligned_le32(buffer),get_unaligned_le32(buffer+8),(s32)get_unaligned_le32(buffer+12));
  if(get_unaligned_le32(buffer)!=262 || get_unaligned_le32(buffer+8)!=(1U<<16) || get_unaligned_le32(buffer+12)){rc=-EPROTO;goto out;}
  memset(buffer,0,1500);
  put_unaligned_le32(98,buffer);put_unaligned_le32(68,buffer+4);put_unaligned_le32(2U<<16,buffer+8);
  rc=usb_control_msg(dev,usb_sndctrlpipe(dev,0),0,USB_DIR_OUT|USB_TYPE_CLASS|USB_RECIP_INTERFACE,0,0,buffer,16,500);
  if(rc!=16){rc=rc<0?rc:-EIO;goto out;}
  memset(buffer,0,1500);
  rc=usb_control_msg(dev,usb_rcvctrlpipe(dev,0),1,USB_DIR_IN|USB_TYPE_CLASS|USB_RECIP_INTERFACE,0,0,buffer,84,500);
  if(rc>=84 && get_unaligned_le32(buffer)==98 && get_unaligned_le32(buffer+8)==(2U<<16) && !get_unaligned_le32(buffer+12)){
   pr_info("j86-wifi-firmware-probe: revinfo vendor=%x device=%x chiprev=%u boardid=%x boardvendor=%x boardrev=%x chipnum=%x\n",get_unaligned_le32(buffer+16),get_unaligned_le32(buffer+20),get_unaligned_le32(buffer+28),get_unaligned_le32(buffer+36),get_unaligned_le32(buffer+40),get_unaligned_le32(buffer+44),get_unaligned_le32(buffer+60));
#ifdef J86_WIFI_NVRAM_PROBE
   memset(buffer,0,1500);
   put_unaligned_le32(262,buffer);put_unaligned_le32(32,buffer+4);put_unaligned_le32(4U<<16,buffer+8);memcpy(buffer+16,"cur_etheraddr",14);
   rc=usb_control_msg(dev,usb_sndctrlpipe(dev,0),0,USB_DIR_OUT|USB_TYPE_CLASS|USB_RECIP_INTERFACE,0,0,buffer,30,500);
   if(rc!=30){rc=rc<0?rc:-EIO;goto out;}
   memset(buffer,0,1500);
   rc=usb_control_msg(dev,usb_rcvctrlpipe(dev,0),1,USB_DIR_IN|USB_TYPE_CLASS|USB_RECIP_INTERFACE,0,0,buffer,48,500);
   if(rc<22 || get_unaligned_le32(buffer)!=262 || get_unaligned_le32(buffer+8)!=(4U<<16) || get_unaligned_le32(buffer+12) || memcmp(buffer+16,expected_mac,6)){
    pr_err("j86-wifi-firmware-probe: owner MAC query failed; private address suppressed\n");rc=-EPROTO;goto out;
   }
   pr_info("j86-wifi-firmware-probe: OWNER_MAC_MATCH_PASS; address suppressed\n");
#endif
   memset(buffer,0,1500);
   put_unaligned_le32(262,buffer);put_unaligned_le32(524,buffer+4);put_unaligned_le32(3U<<16,buffer+8);
   memcpy(buffer+16,"cisdump",8);put_unaligned_le32(512,buffer+32);
   rc=usb_control_msg(dev,usb_sndctrlpipe(dev,0),0,USB_DIR_OUT|USB_TYPE_CLASS|USB_RECIP_INTERFACE,0,0,buffer,36,500);
   if(rc!=36){rc=rc<0?rc:-EIO;goto out;}
   memset(buffer,0,1500);
   rc=usb_control_msg(dev,usb_rcvctrlpipe(dev,0),1,USB_DIR_IN|USB_TYPE_CLASS|USB_RECIP_INTERFACE,0,0,buffer,540,500);
   if(rc>=28 && get_unaligned_le32(buffer)==262 && !(get_unaligned_le32(buffer+8)&1) && !get_unaligned_le32(buffer+12)){
    unsigned int pos=28,end=rc;
    pr_info("j86-wifi-firmware-probe: cisdump response=%d source=%u; private raw tuples suppressed\n",rc,get_unaligned_le16(buffer+16));
    while(pos<end){
     u8 tag=buffer[pos++],length;
     if(tag==0xff)break;
     if(!tag)continue;
     if(pos>=end)break;
     length=buffer[pos++];if(pos+length>end)break;
     if(tag==0x80 && length>=3 && buffer[pos]==0x1b)
      pr_info("j86-wifi-firmware-probe: OTP CIS boardtype=%04x\n",get_unaligned_le16(buffer+pos+1));
     if(tag==0x80 && length>=2 && buffer[pos]==2)
      pr_info("j86-wifi-firmware-probe: OTP CIS boardrev=%04x\n",length>=3?get_unaligned_le16(buffer+pos+1):buffer[pos+1]);
     pos+=length;
    }
   }else pr_info("j86-wifi-firmware-probe: cisdump unavailable response=%d flags=%08x status=%d\n",rc,get_unaligned_le32(buffer+8),(s32)get_unaligned_le32(buffer+12));
   rc=0;
  }else{pr_info("j86-wifi-firmware-probe: revinfo query response=%d status=%d\n",rc,(s32)get_unaligned_le32(buffer+12));rc=rc<0?rc:-EPROTO;}
 }else rc=rc<0?rc:-EIO;
out:
 pr_info("j86-wifi-firmware-probe: result=%d sent=%u received=%u; physical reset restored by overlay removal\n",rc,sent,received);
 kfree(id);kfree(state);kfree(buffer);if(fw)release_firmware(fw);return rc;
}
