#!/usr/bin/env python
'''
Created on Aug 30, 2017

@author: arnon
'''

from eventor.engine import Eventor
from eventor.etypes import MemEventor
import pickle
#import dill
import sys
import struct


class EventorAgent(Eventor):
    def __init__(self, memory=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        super().set_memory(memory)


def cmdargs():
    import argparse
    import os
    
    filename = os.path.basename(__file__)
    progname = filename.rpartition('.')[0]
    
    parser = argparse.ArgumentParser(description="%s runs EventorAgent object" % progname)
    parser.add_argument('host', type=str, 
                        help="""Host on which this command was sent to.""")
    parser.add_argument('--import', type=str, required=False, dest='import_module',
                        help="""import file before pickle loads.""")
    args = parser.parse_args()  
    #argsd=vars(args)
    return args


def run():
    args = cmdargs()
    if args.import_module is not None:
        from importlib import import_module
        import_module(args.import_module)
    
    msgsize_raw = sys.stdin.buffer.read(4)
    msgsize = struct.unpack(">L", msgsize_raw)
    mem_pack = sys.stdin.buffer.read(msgsize[0])
    memory = pickle.loads(mem_pack)
    kwargs = memory.kwargs
    
    kwargs['host'] = args.host
    kwargs['memory'] = memory
    
    try:
        eventor = EventorAgent(**kwargs)
    except Exception as e:
        raise Exception("Failed to start agent with (%s)" % repr(kwargs)[1:-1]) from e
    eventor.run()

      

if __name__ == '__main__':
    import multiprocessing as mp
    mp.freeze_support()
    mp.set_start_method('spawn')
    run()