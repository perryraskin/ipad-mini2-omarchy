#!/usr/bin/env python3
"""USB-peer-only SOCKS5 web access while native Wi-Fi is being developed."""
import argparse,ipaddress,select,socket,socketserver,struct

def receive(sock,n):
    data=b''
    while len(data)<n:
        chunk=sock.recv(n-len(data))
        if not chunk:raise EOFError
        data+=chunk
    return data

class Proxy(socketserver.BaseRequestHandler):
    def handle(self):
        if self.client_address[0]!=self.server.peer:return
        client=self.request
        client.settimeout(20)
        try:
            version,count=receive(client,2)
            methods=receive(client,count)
            if version!=5 or 0 not in methods:
                client.sendall(b'\x05\xff');return
            client.sendall(b'\x05\x00')
            version,command,reserved,kind=receive(client,4)
            if version!=5 or command!=1 or reserved:raise ValueError('CONNECT required')
            if kind==1:host=socket.inet_ntop(socket.AF_INET,receive(client,4))
            elif kind==4:host=socket.inet_ntop(socket.AF_INET6,receive(client,16))
            elif kind==3:host=receive(client,receive(client,1)[0]).decode('ascii')
            else:raise ValueError('Invalid address type')
            port=struct.unpack('!H',receive(client,2))[0]
            if port not in (80,443):raise ValueError('Web ports only')
            # Resolve on the Mac: the iPad does not yet have working DNS/Wi-Fi.
            addresses=socket.getaddrinfo(host,port,type=socket.SOCK_STREAM)
            upstream=None
            for family,kind,proto,_,address in addresses:
                if not ipaddress.ip_address(address[0]).is_global:continue
                candidate=socket.socket(family,kind,proto);candidate.settimeout(15)
                try:candidate.connect(address);upstream=candidate;break
                except OSError:candidate.close()
            if upstream is None:raise OSError('No reachable public web address')
            with upstream:
                client.sendall(b'\x05\x00\x00\x01'+b'\x00'*6)
                while True:
                    ready,_,_=select.select([client,upstream],[],[],180)
                    if not ready:return
                    for source in ready:
                        data=source.recv(65536)
                        if not data:return
                        (upstream if source is client else client).sendall(data)
        except (OSError,EOFError,ValueError,UnicodeError):
            try:client.sendall(b'\x05\x01\x00\x01'+b'\x00'*6)
            except OSError:pass

class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address=True
    daemon_threads=True

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bind');parser.add_argument('peer');parser.add_argument('--port',type=int,default=1080)
    args=parser.parse_args()
    assert ipaddress.ip_address(args.bind).is_link_local
    assert ipaddress.ip_address(args.peer).is_link_local
    with Server((args.bind,args.port),Proxy) as server:
        server.peer=args.peer
        print('USB web proxy ready; only the configured iPad peer can connect.',flush=True)
        server.serve_forever()
