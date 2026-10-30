#!/usr/bin/python3
import ipaddress,pathlib,re,sys
host=sys.argv[1];assert ipaddress.ip_address(host).is_link_local
assert any(x.split()[1:3]==['/','overlay'] for x in pathlib.Path('/proc/mounts').read_text().splitlines())
p=pathlib.Path('/etc/pacman.conf');s=p.read_text()
assert re.search(r'^SigLevel\s*=\s*Required DatabaseOptional\s*$',s,re.M),'Do not weaken package signatures'
line='XferCommand = /usr/bin/curl --socks5-hostname '+host+':1080 --fail --location --connect-timeout 10 --max-time 180 --output %o %u'
if re.search(r'^XferCommand\s*=',s,re.M):s=re.sub(r'^XferCommand\s*=.*$',line,s,flags=re.M)
else:s=s.replace('[options]','[options]\n'+line,1)
s=re.sub(r'^DownloadUser\s*=.*$','# External USB proxy downloader runs inside this isolated app root.',s,flags=re.M)
temporary=p.with_name('pacman.conf.j86-new')
with temporary.open('w') as f:
 f.write(s);f.flush();__import__('os').fsync(f.fileno())
temporary.replace(p)
assert re.search(r'^SigLevel\s*=\s*Required DatabaseOptional\s*$',s,re.M),'Do not weaken package signatures'
