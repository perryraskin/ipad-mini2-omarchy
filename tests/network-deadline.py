#!/usr/bin/env python3
"""Transport fragments must not reset the total command deadline or cause retry."""
import importlib.util,pathlib,re,socket,types
p=pathlib.Path(__file__).resolve().parents[1]/'sessionlib.py'
spec=importlib.util.spec_from_file_location('session',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.config=lambda:{'interface':'fixture','host_ip':'169.254.1.1','device_ip':'169.254.1.2'}
clock=[0.0];m.time=types.SimpleNamespace(monotonic=lambda:clock[0])
class Fixture:
 def __init__(self,trickle=False):self.trickle=trickle;self.closed=False;self.sends=0;self.parts=[];self.timeout=5
 def setsockopt(self,*args):pass
 def bind(self,*args):pass
 def connect(self,*args):pass
 def settimeout(self,value):self.timeout=value
 def sendall(self,data):
  self.sends+=1
  marker=re.search(rb'DONE_[0-9a-f]+',data)[0]
  response=b'fixture result\n'+marker+b'\n'
  self.parts=[response[:4],response[4:15],response[15:]]
 def recv(self,size):
  delay=.4 if self.trickle else .1
  if delay>self.timeout:clock[0]+=self.timeout;raise socket.timeout('modeled deadline')
  clock[0]+=delay
  return b'x' if self.trickle else self.parts.pop(0)
 def close(self):self.closed=True
for trickle in (False,True):
 clock[0]=0;client=Fixture(trickle)
 m.socket=types.SimpleNamespace(socket=lambda:client,if_nametoindex=lambda _:1,IPPROTO_IP=0,TCP_NODELAY=1)
 try:
  result=m.network('read-only fixture command',timeout=1)
  assert not trickle and result=='fixture result'
 except (TimeoutError,socket.timeout):
  assert trickle and clock[0]<=1.00001
 else:assert not trickle
 assert client.closed and client.sends==1
client=Fixture()
def failed_send(data):client.sends+=1;raise BrokenPipeError('modeled lost connection')
client.sendall=failed_send
m.socket=types.SimpleNamespace(socket=lambda:client,if_nametoindex=lambda _:1,IPPROTO_IP=0,TCP_NODELAY=1)
try:m.network('uncertain command',timeout=1)
except BrokenPipeError:pass
else:raise AssertionError('Send failure was hidden')
assert client.closed and client.sends==1
print('PASS: fragmented ACK, total deadline, failure cleanup and no command replay')

# A refused TCP handshake is safe to retry: no command bytes were sent.
clock[0]=0;first=Fixture();second=Fixture();created=[]
def refused(*args):raise ConnectionRefusedError(m.errno.ECONNREFUSED,'listener respawning')
first.connect=refused
m.time=types.SimpleNamespace(monotonic=lambda:clock[0],sleep=lambda delay:clock.__setitem__(0,clock[0]+delay))
def new_socket():
 value=first if not created else second;created.append(value);return value
m.socket=types.SimpleNamespace(socket=new_socket,if_nametoindex=lambda _:1,IPPROTO_IP=0,TCP_NODELAY=1)
assert m.network('one execution only')=='fixture result'
assert first.closed and first.sends==0 and second.closed and second.sends==1 and len(created)==2
print('PASS: refused pre-send connection waits for listener, with one command execution')
