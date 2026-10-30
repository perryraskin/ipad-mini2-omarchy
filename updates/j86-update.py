#!/usr/bin/env python3
"""Explicit Mac-side source checkpoint updates. No background task/device I/O.

Downloads only source releases from the fixed public repo. Applying updates is
explicit, verifies the old manifest, backs up changed files and never runs code,
restarts services, changes boot selection or writes iPad storage.
"""
import argparse,fcntl,gzip,hashlib,io,json,os,pathlib,re,tarfile,tempfile,time,urllib.request
REPO='perryraskin/ipad-mini2-linux'
TAG=re.compile(r'source-checkpoint-[0-9]{8}\.[0-9]+')
ASSETS={'source-checkpoint.tar.gz','checkpoint.json'}
HOSTS={'api.github.com','github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'}
DOCS={'README.md':'publication-docs/README.md','BUILDING.md':'publication-docs/BUILDING.md','HARDWARE.md':'publication-docs/HARDWARE.md','LICENSE':'research/labwc/LICENSE'}
def digest(data):return hashlib.sha256(data).hexdigest()
def path_name(name):
 p=pathlib.PurePosixPath(name)
 if not re.fullmatch(r'[A-Za-z0-9_.+/-]+',name) or not p.parts or len(name)>240 or any(ord(c)<32 for c in name) or not isinstance(name,str) or not name or str(p)!=name or p.is_absolute() or any(v in ('.','..') for v in p.parts) or '\\' in name:raise ValueError('Unsafe source path')
 if p.parts[0] in ('assets','private-data','.git','session.json','controller.lock','usb-session.lock') or name.endswith(('.bin','.ko','.img','.ext4','.trx','.dtb','.dtbo','.cpio')):raise ValueError('Non-source update path')
 return name
class HTTPSRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  check_url(newurl);return super().redirect_request(req,fp,code,msg,headers,newurl)
def check_url(url):
 from urllib.parse import urlparse
 p=urlparse(url)
 if p.scheme!='https' or p.hostname not in HOSTS or p.port not in (None,443) or p.username or p.password:raise ValueError('Update URL outside fixed HTTPS origins')
def fetch(url,limit):
 check_url(url)
 req=urllib.request.Request(url,headers={'Accept':'application/vnd.github+json','User-Agent':'J86-source-update'})
 deadline=time.monotonic()+30;value=bytearray()
 with urllib.request.build_opener(HTTPSRedirect()).open(req,timeout=20) as response:
  while True:
   remaining=deadline-time.monotonic()
   if remaining<=0:raise TimeoutError('Total update download deadline expired')
   if response.fp is not None:response.fp.raw._sock.settimeout(min(20,remaining))
   chunk=response.read1(min(65536,limit+1-len(value)))
   if not chunk:break
   value.extend(chunk)
   if len(value)>limit:raise ValueError('Oversized update response')
 return bytes(value)

def discover(tag=None):
 if tag and not TAG.fullmatch(tag):raise ValueError('Unsupported source tag')
 url='https://api.github.com/repos/'+REPO+'/releases'+('/tags/'+tag if tag else '?per_page=20')
 data=json.loads(fetch(url,2*1024*1024));releases=[data] if tag else data
 for release in releases:
  name=release.get('tag_name','')
  if release.get('draft') or not TAG.fullmatch(name):continue
  assets={a['name']:a for a in release.get('assets',[]) if a.get('name') in ASSETS}
  if set(assets)!=ASSETS:continue
  urls={}
  for filename,asset in assets.items():
   expected=f'https://github.com/{REPO}/releases/download/{name}/{filename}'
   if asset.get('browser_download_url')!=expected:raise ValueError('Unexpected release asset URL')
   urls[filename]=expected
  return {'tag':name,'url':release['html_url'],'prerelease':release.get('prerelease',False),'assets':urls}
 raise ValueError('No source checkpoint release available')

def validate(bundle,receipt):
 if receipt.get('schema')!=1 or receipt.get('repository')!=REPO or receipt.get('kind')!='source-only' or not TAG.fullmatch(receipt.get('tag','')):raise ValueError('Unsupported checkpoint receipt')
 if not re.fullmatch('[0-9a-f]{40}',receipt.get('commit','')) or receipt.get('boot_qualified') is not False:raise ValueError('Invalid source identity/qualification')
 if len(bundle)>8*1024*1024 or receipt.get('size')!=len(bundle) or receipt.get('sha256')!=digest(bundle):raise ValueError('Archive integrity failure')
 with gzip.GzipFile(fileobj=io.BytesIO(bundle)) as stream:raw=stream.read(20*1024*1024+1)
 if len(raw)>20*1024*1024:raise ValueError('Expanded archive limit exceeded')
 files={};folded=set();total=0
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:') as archive:
  for member in archive:
   name=path_name(member.name)
   if name.casefold() in folded or name in files or not member.isfile() or member.size>2*1024*1024:raise ValueError('Unsafe archive member')
   folded.add(name.casefold())
   total+=member.size
   if total>16*1024*1024 or len(files)>=512:raise ValueError('Source archive limits exceeded')
   data=archive.extractfile(member).read()
   if b'\0' in data:raise ValueError('Binary source member')
   data.decode('utf-8');files[name]=data
 manifest=json.loads(files['SOURCE-MANIFEST.json'])
 if set(files)!=set(manifest)|{'SOURCE-MANIFEST.json'}:raise ValueError('Archive/manifest membership mismatch')
 for name,sha in manifest.items():
  path_name(name)
  if not re.fullmatch('[0-9a-f]{64}',sha) or digest(files[name])!=sha:raise ValueError('Source hash mismatch')
 return files,manifest

def stage(directory,release):
 receipt=json.loads(fetch(release['assets']['checkpoint.json'],65536))
 if receipt.get('tag')!=release['tag']:raise ValueError('Release tag mismatch')
 bundle=fetch(release['assets']['source-checkpoint.tar.gz'],8*1024*1024)
 files,manifest=validate(bundle,receipt)
 directory.mkdir(parents=True,exist_ok=True)
 target=directory/receipt['tag']
 if target.exists():raise ValueError('Stage already exists; verify it rather than overwriting')
 with tempfile.TemporaryDirectory(prefix='.j86-update-',dir=directory) as tmp:
  temp=pathlib.Path(tmp)
  for name,data in files.items():
   p=temp/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
  (temp/'checkpoint.json').write_text(json.dumps(receipt,indent=2)+'\n')
  # Keep the verified compressed bundle for later revalidation; never execute it.
  (temp/'source-checkpoint.tar.gz').write_bytes(bundle)
  os.rename(temp,target)
 return target

def safe_destination(workspace,name):
 dest=workspace/DOCS.get(name,name)
 current=dest
 while current!=workspace:
  if current.is_symlink():raise ValueError('Symlink in update destination: '+name)
  current=current.parent
 return dest

def update_plan(workspace,stage_dir,baseline=None):
 if pathlib.Path('/proc/device-tree/model').exists():raise ValueError('Host-only updater refuses device environment')
 workspace=workspace.resolve()
 if not (workspace/'assets/session-assets.json').is_file() or not (workspace/'private-data').is_dir():raise ValueError('Require the existing Mac RAM-boot workspace, not a device/rootfs')
 receipt=json.loads((stage_dir/'checkpoint.json').read_text());bundle=(stage_dir/'source-checkpoint.tar.gz').read_bytes()
 files,manifest=validate(bundle,receipt)
 if baseline is None:
  stored=workspace/'private-data/source-update-baseline.json'
  baseline=stored if stored.is_file() else workspace/'source-release/SOURCE-MANIFEST.json'
 if not baseline.is_file():raise ValueError('No trusted local source baseline; supply --baseline from the installed checkpoint')
 old=json.loads(baseline.read_text())
 changes=[]
 for name,newsha in manifest.items():
  dest=safe_destination(workspace,path_name(name));before=dest.read_bytes() if dest.exists() else None
  if before is not None and digest(before)==newsha:continue
  if name in old:
   if before is None or digest(before)!=old[name]:raise ValueError('Local edit/missing baseline file: '+name)
  elif before is not None:raise ValueError('Untracked local file would be overwritten: '+name)
  changes.append((name,dest,before,files[name]))
 # Removing old sources is deliberately not automatic.
 return receipt,manifest,changes

def atomic(path,data,mode):
 path.parent.mkdir(parents=True,exist_ok=True)
 fd,tmp=tempfile.mkstemp(prefix='.j86-source-',dir=path.parent)
 try:
  with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
  os.chmod(tmp,mode);os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)

def apply(workspace,stage_dir,baseline=None):
 workspace=workspace.resolve()
 # Serialize with the existing host controller; no running USB command is interrupted.
 with (workspace/'controller.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  receipt,manifest,changes=update_plan(workspace,stage_dir,baseline)
  backup=workspace/'private-data/source-update-backups'/receipt['tag']
  if backup.exists():raise ValueError('Backup already exists; inspect prior application')
  backup.mkdir(parents=True,mode=0o700)
  records=[]
  for name,dest,before,after in changes:
   mode=dest.stat().st_mode&0o777 if dest.exists() else (0o755 if name.endswith(('.py','.sh')) or name in ('ipad-linux',) or name.startswith('desktop/j86-') else 0o644)
   if before is not None:
    p=backup/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(before);p.chmod(0o600)
   records.append({'source':name,'destination':str(dest.relative_to(workspace)),'before':digest(before) if before is not None else None,'after':digest(after),'mode':mode})
  (backup/'transaction.json').write_text(json.dumps({'state':'prepared','files':records},indent=2)+'\n')
  completed=[]
  try:
   for (name,dest,before,after),record in zip(changes,records):
    atomic(dest,after,record['mode']);completed.append((dest,before,record['mode']))
  except Exception:
   for dest,before,mode in reversed(completed):
    if before is None:dest.unlink()
    else:atomic(dest,before,mode)
   raise
  previous=workspace/'private-data/source-update-installed.json'
  if previous.exists():(backup/'previous-installed.json').write_bytes(previous.read_bytes())
  previous_baseline=workspace/'private-data/source-update-baseline.json'
  if previous_baseline.exists():(backup/'previous-baseline.json').write_bytes(previous_baseline.read_bytes())
  atomic(previous_baseline,(json.dumps(manifest,indent=2)+'\n').encode(),0o600)
  installed={'tag':receipt['tag'],'commit':receipt['commit'],'manifest':manifest,'source_only':True,'services_restarted':False,'boot_selection_changed':False}
  atomic(workspace/'private-data/source-update-installed.json',(json.dumps(installed,indent=2)+'\n').encode(),0o600)
  (backup/'transaction.json').write_text(json.dumps({'state':'applied','files':records},indent=2)+'\n')
  return installed,len(changes)

def rollback(workspace,tag):
 if not TAG.fullmatch(tag):raise ValueError('Unsupported source tag')
 if pathlib.Path('/proc/device-tree/model').exists():raise ValueError('Host-only rollback')
 workspace=workspace.resolve()
 if not (workspace/'assets/session-assets.json').is_file():raise ValueError('Require host workspace')
 with (workspace/'controller.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  backup=workspace/'private-data/source-update-backups'/tag
  transaction=json.loads((backup/'transaction.json').read_text())
  if transaction['state'] not in ('prepared','applied'):raise ValueError('Checkpoint already rolled back')
  changes=[]
  for record in transaction['files']:
   name=path_name(record['source']);dest=safe_destination(workspace,name)
   if str(dest.relative_to(workspace))!=record['destination']:raise ValueError('Backup destination mismatch')
   current=digest(dest.read_bytes()) if dest.exists() else None
   if current not in (record['before'],record['after']):raise ValueError('Local edit blocks rollback: '+name)
   before=(backup/name).read_bytes() if record['before'] is not None else None
   if before is not None and digest(before)!=record['before']:raise ValueError('Backup integrity failure')
   changes.append((dest,before,record['mode']))
  for dest,before,mode in changes:
   if before is None:dest.unlink(missing_ok=True)
   else:atomic(dest,before,mode)
  previous=backup/'previous-installed.json';installed=workspace/'private-data/source-update-installed.json'
  if previous.exists():atomic(installed,previous.read_bytes(),0o600)
  elif installed.exists() and json.loads(installed.read_text()).get('tag')==tag:installed.unlink()
  baseline=workspace/'private-data/source-update-baseline.json';old_baseline=backup/'previous-baseline.json'
  if old_baseline.exists():atomic(baseline,old_baseline.read_bytes(),0o600)
  else:baseline.unlink(missing_ok=True)
  transaction['state']='rolled-back';(backup/'transaction.json').write_text(json.dumps(transaction,indent=2)+'\n')
  return len(changes)

def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
 for name in ('check','download'):
  cmd=sub.add_parser(name);cmd.add_argument('--tag')
  if name=='download':cmd.add_argument('--directory',type=pathlib.Path,required=True)
 for name in ('plan','apply'):
  cmd=sub.add_parser(name);cmd.add_argument('--workspace',type=pathlib.Path,required=True);cmd.add_argument('--stage',type=pathlib.Path,required=True);cmd.add_argument('--baseline',type=pathlib.Path)
 cmd=sub.add_parser('rollback');cmd.add_argument('--workspace',type=pathlib.Path,required=True);cmd.add_argument('--tag',required=True)
 a=p.parse_args()
 if a.action=='check':print(json.dumps(discover(a.tag),indent=2))
 elif a.action=='download':print(stage(a.directory,discover(a.tag)))
 elif a.action=='plan':
  receipt,_,changes=update_plan(a.workspace,a.stage,a.baseline);print(json.dumps({'tag':receipt['tag'],'source_changes':[c[0] for c in changes],'activation':False},indent=2))
 elif a.action=='rollback':print('Rolled back',rollback(a.workspace,a.tag),'host source files; services unchanged.')
 else:
  installed,count=apply(a.workspace,a.stage,a.baseline);print('Updated',count,'host source files to',installed['tag'],'; services and boot selection unchanged.')
if __name__=='__main__':
 try:main()
 except (OSError,ValueError,KeyError,tarfile.TarError) as error:raise SystemExit(str(error))
