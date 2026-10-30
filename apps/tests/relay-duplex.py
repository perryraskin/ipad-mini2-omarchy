import importlib.util,socket,threading,hashlib,pathlib
spec=importlib.util.spec_from_file_location('relay',str(pathlib.Path(__file__).resolve().parents[2]/'serve-apps-disk.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
# Concurrent 16MiB each direction, deliberately constrained TCP buffers.
up=socket.socket();up.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);up.bind(('127.0.0.1',0));up.listen()
server=m.Server(('127.0.0.1',0),m.Relay);server.peer='127.0.0.1';server.upstream_address=up.getsockname()
threading.Thread(target=server.serve_forever,daemon=True).start()
client=socket.create_connection(server.server_address);remote,_=up.accept()
results=[];payload=b'A'*65536;total=16*1024*1024
for sock in (client,remote):sock.setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,4096);sock.settimeout(20)
def sender(sock):
 for _ in range(total//len(payload)):sock.sendall(payload)
def receiver(sock):
 n=0;digest=hashlib.sha256()
 while n<total:
  b=sock.recv(65536)
  if not b:raise RuntimeError('short read')
  digest.update(b);n+=len(b)
 results.append((n,digest.hexdigest()))
threads=[threading.Thread(target=f,args=(s,)) for s in (client,remote) for f in (sender,receiver)]
for t in threads:t.start()
for t in threads:t.join(30)
assert all(not t.is_alive() for t in threads)
assert results==[(total,hashlib.sha256(payload*(total//len(payload))).hexdigest())]*2,results
print('PASS: simultaneous 16MiB request/reply streams with 4KiB send buffers')
client.close();remote.close();up.close();server.shutdown();server.server_close()
