#!/usr/bin/env python3
import sys
from sessionlib import network
try:print(network(sys.argv[1] if len(sys.argv)>1 else sys.stdin.read()),end='')
except Exception as e:sys.exit(str(e))
