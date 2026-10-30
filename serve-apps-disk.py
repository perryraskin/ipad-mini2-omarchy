#!/usr/bin/env python3
"""USB-peer-only relay to standard nbdkit in the local j86-build VM."""
import argparse,ipaddress,socket,socketserver,threading
class Relay(socketserver.BaseRequestHandler):
 def handle(self):
  if self.client_address[0]!=self.server.peer:return
  try:
   with socket.create_connection(self.server.upstream_address,timeout=10) as upstream:
    upstream.settimeout(None)
    for sock in (upstream,self.request):sock.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
    # NBD requests and replies must drain independently: a blocking sendall
    # in a single select loop deadlocks when both TCP windows fill.
    def pump(source,destination):
     try:
      while True:
       data=source.recv(65536)
       if not data:break
       destination.sendall(data)
     except OSError:pass
     finally:
      for sock in (source,destination):
       try:sock.shutdown(socket.SHUT_RDWR)
       except OSError:pass
    receiver=threading.Thread(target=pump,args=(upstream,self.request),daemon=True)
    receiver.start()
    pump(self.request,upstream)
    receiver.join()
  except OSError as error:print(type(error).__name__,flush=True)
class Server(socketserver.ThreadingTCPServer):
 upstream_address=('127.0.0.1',10814)
 allow_reuse_address=True
 daemon_threads=True
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('bind');p.add_argument('peer');a=p.parse_args()
 assert ipaddress.ip_address(a.bind).is_link_local and ipaddress.ip_address(a.peer).is_link_local
 with Server((a.bind,10812),Relay) as server:
  server.peer=a.peer;print('USB app storage relay ready; standard nbdkit backend.',flush=True);server.serve_forever()
