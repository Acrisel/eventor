'''
Created on Aug 27, 2017

@author: arnon
'''

import pickle
import sys

# need to import objects that would be passed with in
from concepts.sshtypes import RemoteWorker

workload = sys.stdin.buffer.read()

worker = pickle.loads(workload)

worker.run()