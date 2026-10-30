#!/usr/bin/env python3
"""Offline stock Oscar command framing only; no UART, sensor report or I/O code."""
import struct

def checksum(*chunks):
 total=0
 for chunk in chunks:
  for offset in range(0,len(chunk)-1,2):total+=int.from_bytes(chunk[offset:offset+2],'little')
  if len(chunk)&1:total+=chunk[-1]
 return (~total)&0xffff

def encode_command(channel,command,payload=b''):
 if not 0<=channel<=255 or not 0<=command<=65535:raise ValueError('Invalid command identity')
 if not isinstance(payload,bytes) or len(payload)>114:raise ValueError('Command payload exceeds exact stock encoder bound')
 frame=bytearray(struct.pack('<4sBB4xHH',b'ICPA',channel,14+len(payload),0,command)+payload)
 struct.pack_into('<H',frame,10,checksum(frame))
 return bytes(frame)

def decode_command(frame):
 if not isinstance(frame,bytes) or not 14<=len(frame)<=128:raise ValueError('Invalid command frame size')
 if frame[:4]!=b'ICPA' or frame[5]!=len(frame) or any(frame[6:10]):raise ValueError('Unsupported command header')
 if checksum(frame):raise ValueError('Command checksum failed')
 return frame[4],struct.unpack_from('<H',frame,12)[0],frame[14:]
