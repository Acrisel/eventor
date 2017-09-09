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
    parser.add_argument('--import-module', type=str, required=False, dest='import_module', nargs='*',
                        help="""import module before pickle loads.""")
    parser.add_argument('--import-file', type=str, required=False, dest='import_file',
                        help="""import file before pickle loads.""")
    parser.add_argument('--host', type=str, 
                        help="""Host on which this command was sent to.""")
    parser.add_argument('--log', type=str, 
                        help="""Logger name to use.""")
    parser.add_argument('--logdir', type=str, 
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
    
    module_logger.debug('Initiated EventorAgent object, going to run().')
    
    try:
        eventor.run()  
    except Exception as e:
        module_logger.critical("Failed to run EventorAgent, passing TERM to main process.")
        module_logger.exception(e)
        queue.put(('TERM', e))
    else:
        module_logger.debug('EventorAgent finished: passing DONE to main process.')  
        queue.put(('DONE', ''))
    
    
def pipe_listener(queue,):
    global module_logger
    # in this case, whiting for possible termination message from server
    try:
        msgsize_raw = sys.stdin.buffer.read(4)
    except Exception as e:
        module_logger.critical('Failed to read STDIN.')
        module_logger.exception(e)
        queue.put(('TERM', e))
        return
    try:
        msgsize = struct.unpack(">L", msgsize_raw)
    except Exception as e:
        module_logger.critical('Failed pickle loads message size from STDIN; received: %s' % hex(msgsize_raw))
        module_logger.exception(e)
        queue.put(('TERM', e))
        return
    try:
        msg_pack = sys.stdin.buffer.read(msgsize[0])
    except Exception as e:
        module_logger.critical('Failed to read STDIN.')
        module_logger.exception(e)
        queue.put(('TERM', e))
        return
    try:
        msg = pickle.loads(msg_pack)
    except Exception as e:
        module_logger.critical('Failed pickle loads message from STDIN.')
        module_logger.exception(e)
        queue.put(('TERM', e))
        return
        
    module_logger('Received message from remote parent: %s; passing to main process.' % msg)
    queue.put((msg, ''))
    

def run():
    global module_logger
    args = cmdargs()
    mplogger = MpLogger(name=args.log+'.agent', logging_level=logging.DEBUG, console=False, level_formats=level_formats, datefmt='%Y-%m-%d,%H:%M:%S.%f', logdir=args.logdir, encoding='utf8')
    module_logger = mplogger.start()
    module_logger.debug("Starting agent: %s" % args)
    
    if args.import_module is not None:
        if args.import_file is None:
            for module in args.import_module:
                module_logger.debug("Importing %s." % (module))
                try:
                    from importlib import import_module
                    import_module(module)
                except Exception as e:
                    module_logger.critical("Failed to import: %s." % (module))
                    module_logger.exception(e)
                    # signal to parent via stdout
                    print('TERM')
                    print(e, file=sys.stderr)
                    return
        else:
            for module in args.import_module:
                module_logger.debug("Importing %s from %s." % (module, args.import_file))
                try:
                    spec = importlib.util.spec_from_file_location(module, args.import_file)
                    spec_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(spec_module)
                    # sys.modules[args.import_module] = module # not needed for now
                except Exception as e:
                    module_logger.critical("Failed to import: %s %s;" % (args.import_module, args.import_file))
                    module_logger.exception(e)
                    # signal to parant via stdout
                    print('TERM')
                    print(e, file=sys.stderr)
                    return
    
    module_logger.debug("Fetching workload.")
    try:
        msgsize_raw = sys.stdin.buffer.read(4)
        #msgsize_raw = sys.stdin.read(4)
        msgsize = struct.unpack(">L", msgsize_raw)
    except Exception as e:
        module_logger.critical("Failed to read size of workload.")
        module_logger.exception(e)
        print('TERM')
        print(e, file=sys.stderr)
        return
    
    try:
        mem_pack = sys.stdin.buffer.read(msgsize[0])
        #mem_pack = sys.stdin.read(msgsize[0])
        memory = pickle.loads(mem_pack)
    except Exception as e:
        module_logger.critical("Failed to pickle loads workload.")
        module_logger.exception(e)
        # signal to parant via stdout
        print('TERM')
        print(e, file=sys.stderr)
        return
    
    module_logger.debug("Memory received:\n%s" % pprint.pformat(memory, indent=4, ))
    logger_info = mplogger.logger_info()
    
    try:
        kwargs = memory.kwargs.copy()
        memory.logger_info = logger_info
        kwargs['host'] = args.host
        kwargs['memory'] = memory
    except Exception as e:
        module_logger.critical("Failed get kwargs from received  memory.")
        module_logger.exception(e)
        # signal to parant via stdout
        print('TERM')
        print(e, file=sys.stderr)
        return
        
    module_logger.debug("Starting Eventor subprocess on remote host.") #:\n%s" % pprint.pformat(kwargs, indent=4))
    
    queue = mp.Queue()
    
    # we set thread to Daemon so it would be killed when agent is gone
    try:
        listener = Thread(target=pipe_listener, args=(queue,), daemon=True)
        listener.start()
    except Exception as e:
        module_logger.critical("Failed to queue listener thread.")
        module_logger.exception(e)
        # signal to parent via stdout
        print('TERM')
        print(e, file=sys.stderr)
        return
    
    try:
        agent = mp.Process(target=start_eventor, args=(queue, logger_info), kwargs=kwargs, daemon=False)
        agent.start()
    except Exception as e:
        #module_logger = MpLogger.get_logger(logger_info, logger_info['name'])
        module_logger.critical("Failed to start Eventor process.")
        module_logger.exception(e)
        # signal to parant via stdout
        print('TERM')
        print(e, file=sys.stderr)
        return
    
    #module_logger = MpLogger.get_logger(logger_info, logger_info['name'])
    module_logger.debug("Eventor subprocess pid: %s" % agent.pid)
    
    module_logger.debug("Starting control pipe listener.")
    
    # wait for remote parent or from child Eventor 
    if not agent.is_alive():
        module_logger.debug("Agent is not alive! terminating.")
        print('TERM')
        print(e, file=sys.stderr)
        return
    
    while True:
        msg = queue.get()
        if not msg: continue
        msg, error = msg
        module_logger.debug("Pulled message from control queue: %s; %s" % (msg,error,))
        if msg == 'DONE':
            # msg from child - eventor agent is done
            module_logger.debug("Joining with eventor process.")
            agent.join()
            module_logger.debug("Eventor process joint.")
            break
        elif msg == 'TERM':
            # got message to quit, need to kill primo process and be done
            # Well since process is daemon, it will be killed when parent is done
            print('TERM')
            print(error, file=sys.stderr)
            break
    
    module_logger.debug("Closing stdin.")
    #sys.stdin.close()
      

if __name__ == '__main__':
    mp.freeze_support()
    mp.set_start_method('spawn')
    run()
    