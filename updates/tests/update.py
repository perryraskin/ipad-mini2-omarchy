#!/usr/bin/env python3
"""Real archive, source update, backups/rollback and hostile-input checks."""
import gzip,hashlib,importlib.util,io,json,pathlib,tarfile,tempfile,unittest.mock
root=pathlib.Path(__file__).resolve().parents[2]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
u=module('update',root/'updates/j86-update.py');b=module('builder',root/'updates/build-release.py')
with tempfile.TemporaryDirectory() as tmp:
 t=pathlib.Path(tmp);release=t/'release';release.mkdir();workspace=t/'workspace';workspace.mkdir();stage=t/'stage';stage.mkdir()
 (workspace/'assets').mkdir();(workspace/'assets/session-assets.json').write_text('{}');(workspace/'private-data').mkdir()
 (workspace/'tool.py').write_bytes(b'old\n');old={'tool.py':u.digest(b'old\n')};baseline=t/'baseline.json';baseline.write_text(json.dumps(old))
 (release/'tool.py').write_bytes(b'new\n');(release/'new.py').write_bytes(b'add\n');manifest={name:u.digest((release/name).read_bytes()) for name in ('tool.py','new.py')};(release/'SOURCE-MANIFEST.json').write_text(json.dumps(manifest))
 bundle,receipt=b.build(release,'source-checkpoint-20261030.1','a'*40)
 assert b.build(release,receipt['tag'],'a'*40)[0]==bundle
 assert u.validate(bundle,receipt)[1]==manifest
 (stage/'checkpoint.json').write_text(json.dumps(receipt));(stage/'source-checkpoint.tar.gz').write_bytes(bundle)
 # A local edit must refuse before changing any other file.
 (workspace/'tool.py').write_bytes(b'local edit\n')
 try:u.update_plan(workspace,stage,baseline)
 except ValueError:pass
 else:raise AssertionError('Overwrote local edit')
 assert not (workspace/'new.py').exists();(workspace/'tool.py').write_bytes(b'old\n')
 installed,count=u.apply(workspace,stage,baseline);assert count==2 and installed['boot_selection_changed'] is False
 assert (workspace/'tool.py').read_bytes()==b'new\n' and (workspace/'new.py').read_bytes()==b'add\n'
 assert u.rollback(workspace,receipt['tag'])==2
 assert (workspace/'tool.py').read_bytes()==b'old\n' and not (workspace/'new.py').exists()
 # Path traversal, symlinks, executable/device artifacts and corrupted archive fail.
 for name in ('../bad','/bad','assets/firmware.bin','private-data/key','x/../bad','.'):
  try:u.path_name(name)
  except (ValueError,TypeError):pass
  else:raise AssertionError(name)
 (workspace/'tool.py').unlink();(workspace/'tool.py').symlink_to(release/'tool.py')
 try:u.update_plan(workspace,stage,baseline)
 except ValueError:pass
 else:raise AssertionError('Destination symlink accepted')
 try:u.validate(bundle+b'corrupt',receipt)
 except ValueError:pass
 else:raise AssertionError('Bad archive hash accepted')
 for url in ('http://github.com/x','https://evil.example/x','https://github.com:443@evil.example/x'):
  try:u.check_url(url)
  except ValueError:pass
  else:raise AssertionError(url)
 # Download stage is private/inert; no source execution or workspace application.
 fake_release={'tag':receipt['tag'],'assets':{'checkpoint.json':'receipt','source-checkpoint.tar.gz':'bundle'}}
 with unittest.mock.patch.object(u,'fetch',side_effect=lambda url,limit:json.dumps(receipt).encode() if url=='receipt' else bundle):
  target=u.stage(t/'downloads',fake_release)
 assert (target/'tool.py').read_bytes()==b'new\n' and not (target/'tool.py').stat().st_mode&0o111
print('Source updater: deterministic archive, integrity, local-edit/symlink refusal, explicit apply and rollback passed')

# Archive validation must reject symlink/traversal/case collisions without extracting.
def malicious(members):
 data=io.BytesIO()
 with tarfile.open(fileobj=data,mode='w') as tar:
  for name,kind in members:
   item=tarfile.TarInfo(name);item.size=0
   if kind=='link':item.type=tarfile.SYMTYPE;item.linkname='/tmp/elsewhere'
   tar.addfile(item,io.BytesIO())
 payload=gzip.compress(data.getvalue(),mtime=0);r=dict(receipt);r.update(size=len(payload),sha256=u.digest(payload))
 try:u.validate(payload,r)
 except (ValueError,KeyError):pass
 else:raise AssertionError(members)
malicious([('../escape','file')]);malicious([('tool.py','link')]);malicious([('Tool.py','file'),('tool.py','file')])
print('Source updater: archive traversal, symlink and case-collision rejection passed')
