'''
Created on Aug 27, 2017

@author: arnon
'''

from concepts.sshtypes import RemoteWorker
import pickle
import sys
import struct

msgsize_raw = sys.stdin.buffer.read(4)
msgsize = struct.unpack(">L", msgsize_raw)
workload = sys.stdin.buffer.read(msgsize[0])

worker = pickle.loads(workload)

worker.run()
