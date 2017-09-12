'''
Created on Aug 27, 2017

@author: arnon
'''

import concepts.sshtypes as sshtypes
import pickle
import sys
import struct
import os

file = open("/var/log/eventor/eventor_concept_ssh_agent.log", "w")

def log(msg):
    print(msg, file=file)
    file.flush()

log("starting loop: %s." % os.getpid())

while True:
    log("Trying to read stdin.")
    try:
        msgsize_raw = sys.stdin.buffer.read(4)
        msgsize = struct.unpack(">L", msgsize_raw)
        log("Received message size: %s." % msgsize)
        workload = sys.stdin.buffer.read(msgsize[0])
        log("Received message .")
        worker = pickle.loads(workload)
    except Exception as e:
        log('Failed to read worker: %s' % e)
        break
    if not isinstance(worker, str): 
        log('Got worker.')
        worker.run()
        log('Worker done.')
    elif worker == 'TERM':
        log('Got TERM.')
        break
    else:
        log('Got %s.' % worker)
        print(worker)
        
file.close()
