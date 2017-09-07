'''
Created on Aug 27, 2017

@author: arnon
'''

from concepts.sshtypes import RemoteWorker
import pickle
import sys
import struct

file = open("/var/log/eventor/eventor_concept_ssh_agent.log", "w")

def log(msg):
    print(msg, file=file)
    file.flush()

log("starting loop.")
while True:
    log("Trying to read stdin.")
    try:
        msgsize_raw = sys.stdin.buffer.read(4)
        msgsize = struct.unpack(">L", msgsize_raw)
        workload = sys.stdin.buffer.read(msgsize[0])
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
