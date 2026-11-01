#!/usr/bin/env python3
"""Validate live symbol exports, transfer/hash-check a bounded module, load once."""
import base64,hashlib,pathlib,re,subprocess,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]))
from sessionlib import network
p=pathlib.Path(sys.argv[1]).resolve()
if not re.fullmatch(r'j86_[a-z0-9_]+\.ko',p.name):raise SystemExit('Unexpected module name')
nm=subprocess.check_output(['xcrun','llvm-nm','-u',str(p)],text=True)
symbols=re.findall(r' U (\S+)',nm)
pattern='__ksymtab_('+'|'.join(re.escape(s) for s in symbols)+')([[:space:]]+\[[^]]+\])?$'
exports=network("busybox grep -E '"+pattern+"' /proc/kallsyms")
missing=[s for s in re.findall(r' U (\S+)',nm) if not re.search(r'\b__ksymtab_'+re.escape(s)+r'(?:\s+\[[A-Za-z0-9_]+\])?$',exports,re.M)]
if missing:raise SystemExit('Missing live exports: '+str(missing))
if '--check-only' in sys.argv[2:]:
 print('Validated',len(symbols),'live exports without loading; build VM is not required.');raise SystemExit(0)
b=p.read_bytes();h=hashlib.sha256(b).hexdigest();s=base64.b64encode(b).decode();remote='/tmp/'+p.name
cmd="cat > /tmp/j86-module.b64 <<'J86_MODULE_EOF'\n"+'\n'.join(s[i:i+1024]for i in range(0,len(s),1024))+"\nJ86_MODULE_EOF\n"
cmd+=f"busybox base64 -d /tmp/j86-module.b64 > {remote}\nactual=$(busybox sha256sum {remote}); [ \"${{actual%% *}}\" = {h} ] || exit 90\nrm /tmp/j86-module.b64\n/tmp/load-once {remote}; echo LOAD_ONCE_EXIT:$?\ndmesg | tail -18"
print('Validated',len(re.findall(r' U (\S+)',nm)),'live exports; SHA256',h)
print(network(cmd,timeout=360))
