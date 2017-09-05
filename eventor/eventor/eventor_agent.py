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
from acrilog import MpLogger
import logging
import pprint

module_logger = None

level_formats = {logging.DEBUG:"[ %(asctime)-15s ][ %(processName)-11s ][ %(levelname)-7s ][ %(message)s ][ %(module)s.%(funcName)s(%(lineno)d) ]",
                'default':   "[ %(asctime)-15s ][ %(processName)-11s ][ %(levelname)-7s ][ %(message)s ]",
                }


#class EventorAgent(Eventor):
#    def __init__(self, memory=None, *args, **kwargs):
#        super().__init__(*args, **kwargs)
#        super().set_memory(memory)


def cmdargs():
    import argparse
    import os
    
    filename = os.path.basename(__file__)
    progname = filename.rpartition('.')[0]
    
    parser = argparse.ArgumentParser(description="%s runs EventorAgent object" % progname)
    parser.add_argument('--import-module', type=str, required=False, dest='import_module',
                        help="""import module before pickle loads.""")
    parser.add_argument('--import-file', type=str, required=False, dest='import_file',
                        help="""import file before pickle loads.""")
    parser.add_argument('host', type=str, 
                        help="""Host on which this command was sent to.""")
    parser.add_argument('log', type=str, 
                        help="""Logger name to use.""")
    parser.add_argument('logdir', type=str, 
                        help="""Logger outout directory.""")
    args = parser.parse_args()  
    #argsd=vars(args)
    return args


def start_eventor(queue, logger_info, **kwargs):
    global module_logger
    module_logger = MpLogger.get_logger(logger_info, logger_info['name'])
    module_logger.debug('Starting EventorAgent:\n%s' % pprint.pformat(kwargs, indent=4))
    try:
        eventor = Eventor(**kwargs)
    except Exception as e:
        raise Exception("Failed to start EventorAgent.") from e
    
    module_logger.debug('Initiated EventorAgent object, about to run().')
    
    try:
        eventor.run()  
    except Exception as e:
        module_logger.critical("Failed to run EventorAgent, passing TERM to main process.")
        module_logger.exception(e)
        queue.put('TERM')
        return
    
    module_logger.debug('EventorAgent finished: passing DONE to main process.')  
    queue.put('DONE')
    
    
def pipe_listener(queue,):
    global module_logger
    # in this case, whiting for possible termination message from server
    msgsize_raw = sys.stdin.buffer.read(4)
    msgsize = struct.unpack(">L", msgsize_raw)
    msg_pack = sys.stdin.buffer.read(msgsize[0])
    msg = pickle.loads(msg_pack)
    module_logger('Received message from remote parent: %s; passing to main process.' % msg)
    queue.put(msg)
    

def run():
    global module_logger
    args = cmdargs()
    mplogger = MpLogger(name=args.log+'.agent', logging_level=logging.DEBUG, level_formats=level_formats, datefmt='%Y-%m-%d,%H:%M:%S.%f', logdir=args.logdir, encoding='utf8')
    module_logger = mplogger.start()
    module_logger.debug("Starting agent: %s" % args)
    if args.import_module is not None:
        if args.import_file is None:
            try:
                from importlib import import_module
                import_module(args.import_module)
            except Exception as e:
                module_logger.critical("Failed to import: %s;" % (args.import_module))
                module_logger.exception(e)
                # signal to parant via stdout
                print('TERM')
                return
        else:
            try:
                spec = importlib.util.spec_from_file_location(args.import_module, args.import_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                # sys.modules[args.import_module] = module # not needed for now
            except Exception as e:
                module_logger.critical("Failed to import: %s %s;" % (args.import_module, args.import_file))
                module_logger.exception(e)
                # signal to parant via stdout
                print('TERM')
                return
    
    module_logger.debug("Fetching workload.")
    msgsize_raw = sys.stdin.buffer.read(4)
    msgsize = struct.unpack(">L", msgsize_raw)
    mem_pack = sys.stdin.buffer.read(msgsize[0])
    
    try:
        memory = pickle.loads(mem_pack)
    except Exception as e:
        module_logger.critical("Failed to pickle loads workload.")
        module_logger.exception(e)
        # signal to parant via stdout
        print('TERM')
        return
        
    logger_info = mplogger.logger_info()
    kwargs = memory.kwargs.copy()
    memory.logger_info = logger_info
    kwargs['host'] = args.host
    kwargs['memory'] = memory
    module_logger.debug("Starting Eventor subprocess on remote host.") #:\n%s" % pprint.pformat(kwargs, indent=4))
    
    queue = mp.Queue()
    
    
    #start_eventor(queue, logger_info, **kwargs)
    #return
    #module_logger = None
    try:
        agent = mp.Process(target=start_eventor, args=(queue, logger_info), kwargs=kwargs, daemon=False)
        agent.start()
    except Exception as e:
        #module_logger = MpLogger.get_logger(logger_info, logger_info['name'])
        module_logger.critical("Failed to start Eventor process.")
        module_logger.exception(e)
        # signal to parant via stdout
        print('TERM')
        return
    
    #module_logger = MpLogger.get_logger(logger_info, logger_info['name'])
    module_logger.debug("Eventor subprocess pid: %s" % agent.pid)
    
    # we set thread to Daemon so it would be killed when agent is gone
    try:
        plistener = Thread(target=pipe_listener, args=(queue,), daemon=True)
        plistener.start()
    except Exception as e:
        module_logger.critical("Failed to queue listener thread.")
        module_logger.exception(e)
        # signal to parant via stdout
        print('TERM')
        return
    
    module_logger.debug("Starting control pipe listener.")
    
    # wait for remote parent or from child Eventor 
    if not agent.is_alive():
        module_logger.debug("agent is not alive! terminating.")
        print('TERM')
        return
    
    while True:
        msg = queue.get()
        if not msg: continue
        module_logger.debug("Pulled message from control queue: %s" % (msg,))
        if msg == 'DONE':
            # msg from child - eventor agent is done
            agent.join()
            break
        elif msg == 'TERM':
            # got message to quit, need to kill primo process and be done
            # Well since process is daemon, it will be killed when parent is done
            print('TERM')
            break
    
      

if __name__ == '__main__':
    mp.freeze_support()
    mp.set_start_method('spawn')
    run()
    