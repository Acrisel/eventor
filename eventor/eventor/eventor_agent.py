#!/usr/bin/env python
'''
Created on Aug 30, 2017

@author: arnon
'''

from eventor.engine import Eventor
# needed by pickle loads BEGIN ---<
from eventor.etypes import MemEventor
import acris
import collections
# >--- END
import pickle
#import dill
import sys
import struct
import importlib.util
import multiprocessing as mp
from threading import Thread
from acrilog import NwLogger as Logger
from acrilog import NwLoggerClientHandler
import logging
import pprint
from queue import Empty
import yaml
from copy import copy
import os

module_logger = None

class EventorAgentError(Exception): pass

level_formats = {logging.DEBUG:"[ %(asctime)-15s ][ %(host)s ][ %(processName)-11s ][ %(levelname)-7s ][ %(message)s ][ %(module)s.%(funcName)s(%(lineno)d) ]",
                'default':   "[ %(asctime)-15s ][ %(host)s ][ %(processName)-11s ][ %(levelname)-7s ][ %(message)s ]",
                }

#class EventorAgent(Eventor):
#    def __init__(self, memory=None, *args, **kwargs):
#        super().__init__(*args, **kwargs)
#        super().set_memory(memory)

RECOVER_ARGS_DIR = '/tmp'
RECOVER_ARGS_FILE = 'eventor_agent_args'

def new_recvoer_args_file(name=None):
    file = "{}.".format(name) if name else ""
    file = "{}{}.{}.dat".format(file, RECOVER_ARGS_FILE, os.getpid())
    file = os.path.join(RECOVER_ARGS_DIR, file)
    return file

def last_recvoer_args_file():
    files = filter(lambda x: os.path.isfile(x) and x.startswith(RECOVER_ARGS_FILE), os.listdir(RECOVER_ARGS_DIR))
    files = [os.path.join(RECOVER_ARGS_DIR, f) for f in files] # add path to each file
    files.sort(key=lambda x: os.path.getmtime(x))
    return files[-1] if len(files) > 0 else None

def cmdargs():
    import argparse

    filename = os.path.basename(__file__)
    progname = filename.rpartition('.')[0]

    parser = argparse.ArgumentParser(prog=progname, description="runs EventorAgent object.")
    subparsers = parser.add_subparsers(title='subcommands',
                                       description='valid subcommands',
                                       help='additional help')
    parser_act = subparsers.add_parser('action', aliases=['act'], help='perform new action')
    parser_rec = subparsers.add_parser('recover', aliases=['rec'], help='recover previous act')
    
    parser_act.set_defaults(run=True, recover=False)
    parser_rec.set_defaults(run=False, recover=True)
    
    parser_act.add_argument('--imports', type=str, required=False, dest='imports', nargs='*',
                        help="""import module before pickle loads.""")
    parser_act.add_argument('--host', type=str,
                        help="""Host on which this command was sent to.""")
    parser_act.add_argument('--ssh-server-host', type=str, dest='ssh_host',
                        help="""SSH Host to use for back channel.""")
    parser_act.add_argument('--log-info', type=str, dest='log_info',
                        help="""Logger info dictionary json coded.""")
    parser_act.add_argument('--file', type=str, required=False,
                        help="""File to store or recover memory. With --pipe, it would store memory into file. Without --pipe, it would recover memory from store""")
    parser_act.add_argument('--pipe', action='store_true',
                        help="""Indicates that memory should be read from STDIN. If --pipe not provided, --file must be.""")
    parser_act.add_argument('--debug', action='store_true',
                        help="""Invokes additional debug utilities, e.g., store args for recovery.""")
    
    parser_rec.add_argument('--file', type=str, required=False,
                        help="""File from which to restore previous args""")
    args = parser.parse_args()

    assert args.file is not None or args.pipe, "--pipe or --file must be provided."
    #argsd=vars(args)
    return args

def do_imports(imports):
    imports = imports_from_cmd(imports)
    module_logger.debug("Importing {}.".format(imports))
    for import_file, import_modules in imports:
        if not import_file:
            for module in import_modules:
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
            for module in import_modules:
                module_logger.debug("Importing %s from %s." % (module, import_file))
                try:
                    spec = importlib.util.spec_from_file_location(module, import_file)
                    spec_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(spec_module)
                    # sys.modules[import_module] = module # not needed for now
                except Exception as e:
                    module_logger.critical("Failed to import: %s %s;" % (import_module, import_file))
                    module_logger.exception(e)
                    # signal to parant via stdout
                    print('TERM')
                    print(e, file=sys.stderr)
                    return

def start_eventor(queue, logger_info, **kwargs):
    global module_logger
    module_logger = Logger.get_logger(logger_info, logger_info['name'])
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
    ''' Pipe listener wait for one message.  Once receive (DONE or TERM) it ends.
    '''
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

    module_logger.debug('Received message from remote parent: {}; passing to main process.'.format(msg))

    queue.put((msg, ''))

def imports_from_cmd(imports_str):
    imports = dict()

    for import_str in imports_str:
        import_file, _, import_modules_str = import_str.partition(':')
        import_modules = import_modules_str.split(':')
        file_modules = imports.get(import_file, list())
        file_modules.extend(import_modules)
        imports[import_file] = file_modules
    imports = [(import_file, set(modules)) for import_file, modules in imports.items() if modules]
    return imports


def check_agent_process(agent,):
    if not agent.is_alive():
        agent.join()
        module_logger.debug("Agent is not alive! terminating.")
        print('TERM')
        print("Agent aborted unexpectedly.", file=sys.stderr)
        return False
    return True


def logger_remote_handler(remote_logger_queue, log_info_recv, ssh_host,):
    #log_info_recv['name'] = '{}_eventor_sshagent'.format(log_info_recv['name'])
    remote_logger_handler = NwLoggerClientHandler(log_info_recv, ssh_host=ssh_host,) # logger=module_logger, logdir=logdir)
    #module_logger.addHandler(remote_logger_handler)
    listener = logging.handlers.QueueListener(remote_logger_queue, remote_logger_handler)
    listener.start()
    return listener


def run(args, ):
    ''' Runs EventorAgent in remote host.

    Args:
        log_info
        imports
        host
        file
        pipe
    '''
    global module_logger

    log_info, imports, host, ssh_host, pipe, file = args.log_info, args.imports, args.host, args.ssh_host, args.pipe, args.file
    
    log_info_recv = yaml.load(log_info) #[1:-1])

    # TODO: pass other logging attributes
    logger_name = log_info_recv['name']
    #logging_level = log_info_recv['logging_level']
    #logdir = log_info['logdir']
    #datefmt = log_info['datefmt']
    handler_kwargs = log_info_recv['handler_kwargs']
    

    logger_info_local = copy(log_info_recv)
    del logger_info_local['port']
    del logger_info_local['handler_kwargs']

    logger = Logger(console=False, **logger_info_local, **handler_kwargs)
    logger.start()
    
    logger_info = logger.logger_info()
    module_logger = Logger.get_logger(logger_info=logger_info, name=logger_name)
    
    module_logger.debug("Starting agent: {}".format(args))
    if args.debug:
        file = new_recvoer_args_file(file)
        try:
            with open(file, 'wb') as f:
                pickle.dump(args, f)
        except Exception as e:
            module_logger.critical("Failed to store args.")
            module_logger.exception(e)
            print('TERM')
            print(e, file=sys.stderr)
            return
        module_logger.debug("Stored agent args: {}".format(file))
    
    module_logger.debug('Local logger:\n{}'.format(logger_info_local))
    module_logger.debug('Module logger:\n{}'.format(log_info))
    
    remote_logger_queue = mp.Queue()
    queue_handler = logging.handlers.QueueHandler(remote_logger_queue)
    module_logger.addHandler(queue_handler)
    #remote_logger_handler = NwLoggerClientHandler(log_info_recv, ssh_host=ssh_host, logger=module_logger, logdir=handler_kwargs['logdir'])
    #module_logger.addHandler(remote_logger_handler)
    logger_remote_listener = logger_remote_handler(remote_logger_queue, log_info_recv=log_info_recv, ssh_host=ssh_host,) # logdir=handler_kwargs['logdir'])
    
    if imports is not None:
        do_imports(imports)
        
    if pipe:
        module_logger.debug("Fetching workload. from pipe")
        try:
            msgsize_raw = sys.stdin.buffer.read(4)
            #msgsize_raw = sys.stdin.read(4)
            msgsize = struct.unpack(">L", msgsize_raw)
        except Exception as e:
            module_logger.critical("Failed to read size of workload.")
            module_logger.exception(e)
            #print('TERM')
            #print(e, file=sys.stderr)
            close_run(logger_remote_listener, logger, msg='TERM', err=e)
            return

        try:
            mem_pack = sys.stdin.buffer.read(msgsize[0])
            memory = pickle.loads(mem_pack)
        except Exception as e:
            module_logger.critical("Failed to pickle loads workload.")
            module_logger.exception(e)
            # signal to parant via stdout
            #print('TERM')
            #print(e, file=sys.stderr)
            close_run(logger_remote_listener, logger, msg='TERM', err=e)
            return

        # store memory into file
        if file:
            module_logger.debug("Storing workload to {}.".format(file))
            try:
                with open(file, 'wb') as file:
                    pickle.dump(memory, file)
            except Exception as e:
                module_logger.critical("Failed to pickle dump workload to {}.".format(file))
                module_logger.exception(e)
                # signal to parant via stdout
                #print('TERM')
                #print(e, file=sys.stderr)
                close_run(logger_remote_listener, logger, msg='TERM', err=e)
                return
    else:
        module_logger.debug("Fetching workload from file.")
        try:
            with open(file, 'rb') as file:
                memory = pickle.load(file)
        except Exception as e:
            module_logger.critical("Failed to pickle load workload from {}.".format(file))
            module_logger.exception(e)
            # signal to parant via stdout
            #print('TERM')
            #print(e, file=sys.stderr)
            close_run(logger_remote_listener, logger, msg='TERM', err=e)
            return

    module_logger.debug("Memory received:\n{}".format(pprint.pformat(memory, indent=4, )))
    logger_info = logger.logger_info()

    try:
        kwargs = memory.kwargs.copy()
        # change logger_info to this agent logger info.
        memory.logger_info = logger_info
        kwargs['host'] = host
        kwargs['memory'] = memory
    except Exception as e:
        module_logger.critical("Failed get kwargs from received memory.")
        module_logger.exception(e)
        # signal to parant via stdout
        #print('TERM')
        #print(e, file=sys.stderr)
        close_run(logger_remote_listener, logger, msg='TERM', err=e)
        return

    module_logger.debug("Starting Eventor subprocess on remote host.") #:\n%s" % pprint.pformat(kwargs, indent=4))

    child_q = mp.Queue()

    module_logger.debug("Starting control pipe listener.")
    # we set thread to Daemon so it would be killed when agent is gone
    try:
        listener = Thread(target=pipe_listener, args=(child_q,), daemon=True)
        listener.start()
    except Exception as e:
        module_logger.critical("Failed to queue listener thread.")
        module_logger.exception(e)
        # signal to parent via stdout
        #print('TERM')
        #print(e, file=sys.stderr)
        close_run(listener, logger, msg='TERM', err=e)
        return

    eventor_listener_q = mp.Queue()

    kwargs['listener_q'] = eventor_listener_q

    try:
        agent = mp.Process(target=start_eventor, args=(child_q, logger_info,), kwargs=kwargs, daemon=False)
        agent.start()
    except Exception as e:
        #module_logger = MpLogger.get_logger(logger_info, logger_info['name'])
        module_logger.critical("Failed to start Eventor process.")
        module_logger.exception(e)
        # signal to parant via stdout
        #print('TERM')
        #print(e, file=sys.stderr)
        close_run(logger_remote_listener, logger, msg='TERM', err=e)
        return

    #module_logger = MpLogger.get_logger(logger_info, logger_info['name'])
    module_logger.debug("Eventor subprocess pid: {}".format(agent.pid))

    # wait for remote parent or from child Eventor
    if not check_agent_process(agent):
        module_logger.debug("Agent process is dead, exiting.".format(agent.pid))
        close_run(logger_remote_listener, logger, ) #msg='TERM', err=error)
        return

    while True:
        try:
            msg = child_q.get(timeout=0.5)
        except Empty:
            msg = None
            if not check_agent_process(agent):
                # since agent is gone - nothing to do.
                module_logger.debug("Empty queue, agent process is dead, exiting.".format(agent.pid))
                close_run(logger_remote_listener, logger, ) # msg='TERM', err=error)
                return
        if not msg: continue
        msg, error = msg
        module_logger.debug("Pulled message from control queue: {}; {}.".format(msg,error,))
        if msg == 'DONE':
            # msg from child - eventor agent is done
            module_logger.debug("Joining with Eventor process.")
            agent.join()
            listener.join()
            module_logger.debug("Eventor process joint after DONE.")
            close_run(logger_remote_listener, logger, ) #msg='TERM', err=error)
            break
        elif msg == 'TERM':
            # TODO: need to change message from parent to STOP - not TERM
            # got message to quit, need to kill primo process and be done
            # Well since process is daemon, it will be killed when parent is done
            eventor_listener_q.put('STOP')
            agent.join()
            listener.join()
            #print('TERM')
            #print(error, file=sys.stderr)
            close_run(logger_remote_listener, logger, msg='TERM', err=error)
            # TODO(Arnon): how to terminate listener that is listening
            break
        elif msg in ['STOP', 'FINISH']:
            # TODO: need to change message from parent to STOP - not TERM
            # got message to quit, need to kill primo process and be done
            # Well since process is daemon, it will be killed when parent is done
            eventor_listener_q.put('STOP')
            module_logger.debug("Joining with Eventor process.")
            agent.join()
            listener.join()
            module_logger.debug("Eventor process joint after {}.".format(msg))
            #print('DONE')
            close_run(logger_remote_listener, logger, msg='DONE', err=None)
            break

    #module_logger.debug("Closing stdin.")
    #sys.stdin.close()
    #logger.stop()
    #listener.stop()
    
def close_run(listener, logger, msg=None, err=None):
    global module_logger
    module_logger.debug("Closing stdin.")
    
    if msg is not None:
        print(msg)
    if err is not None:
        print(err, file=sys.stderr)
    
    logger.stop()
    listener.stop()
    
def recover(args):
    file = args.file
    if file is None:
        file = last_recvoer_args_file()
    if file is not None:
        with open(file, 'rb') as f:
            args = pickle.load(f)
        run(args)
    else:
        raise EventorAgentError("Trying to run in recovery, but no recovery file found.")

if __name__ == '__main__':
    mp.freeze_support()
    mp.set_start_method('spawn')
    args = cmdargs()
    if args.run:
        run(args)
    else:
        recover(args)
