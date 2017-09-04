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
import importlib.util
import multiprocessing as mp
from threading import Thread


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
    parser.add_argument('--import-module', type=str, required=False, dest='import_module',
                        help="""import module before pickle loads.""")
    parser.add_argument('--import-file', type=str, required=False, dest='import_file',
                        help="""import file before pickle loads.""")
    args = parser.parse_args()  
    #argsd=vars(args)
    return args


def start_eventor(queue, **kwargs):
    try:
        eventor = EventorAgent(**kwargs)
    except Exception as e:
        raise Exception("Failed to start agent with (%s)" % repr(kwargs)[1:-1]) from e
    eventor.run()    
    queue.put('DONE')
    
    
def pipe_listener(queue):
    msgsize_raw = sys.stdin.buffer.read(4)
    msgsize = struct.unpack(">L", msgsize_raw)
    msg_pack = sys.stdin.buffer.read(msgsize[0])
    msg = pickle.loads(msg_pack)
    queue.put(msg)
    

def run():
    args = cmdargs()
    if args.import_module is not None:
        if args.import_file is None:
            from importlib import import_module
            import_module(args.import_module)
        else:
            spec = importlib.util.spec_from_file_location(args.import_module, args.import_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            # sys.modules[args.import_module] = module # not needed for now
    
    msgsize_raw = sys.stdin.buffer.read(4)
    msgsize = struct.unpack(">L", msgsize_raw)
    mem_pack = sys.stdin.buffer.read(msgsize[0])
    memory = pickle.loads(mem_pack)
    kwargs = memory.kwargs
    
    kwargs['host'] = args.host
    kwargs['memory'] = memory
    
    queue = mp.Queue()
    # start_eventor(**kwargs)
    kwargs['queue'] = queue
    agent = mp.Process(target=start_eventor, kwargs=kwargs, daemon=True)
    agent.start()
    
    # we set thread to Daemon so it would be killed when agent is gone
    plistener = Thread(target=pipe_listener, args=(queue,), daemon=True)
    plistener.start()
    
    while True:
        msg = queue.get()
        if not msg: continue
        if msg == 'DONE':
            # msg from child - eventor agent is done
            agent.join()
            break
        elif msg == 'TERM':
            # got message to quit, need to kill primo process and be done
            # Well since process is daemon, it will be killed when parent is done
            break
            
    

      

if __name__ == '__main__':
    import multiprocessing as mp
    mp.freeze_support()
    mp.set_start_method('spawn')
    run()