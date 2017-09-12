'''
Created on Aug 27, 2017

@author: arnon
'''

import concepts.sshtypes as sshtypes
import pickle
import sys
import struct
import os
import logging

logger = logging.getLogger(__name__)

while True:
    logger.debug("Trying to read stdin.")
    try:
        msgsize_raw = sys.stdin.buffer.read(4)
        msgsize = struct.unpack(">L", msgsize_raw)
        workload = sys.stdin.buffer.read(msgsize[0])
        worker = pickle.loads(workload)
    except Exception as e:
        logger.error('Failed to read worker: %s' % e)
        print("TERM")
        break
    
    if not isinstance(worker, str): 
        worker.run()
    elif worker == 'TERM':
        logger.debug('Got TERM.')
        break
    else:
        print("Bad worker: " + repr(worker))
        
