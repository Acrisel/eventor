#!/usr/bin/env python
'''
Created on Aug 30, 2017

@author: arnon
'''

from eventor.lib.engine import Eventor
import pickle
import sys
import struct
import importlib.util
import multiprocessing as mp
from acrilog import SSHLogger as Logger
from acrilog import SSHLoggerClientHandler
import sshpipe as sp
import logging
import pprint
import yaml
from copy import copy
import os
import select

mlogger = None


class EventorAgentError(Exception):
    pass


level_formats = {logging.DEBUG: ("[ %(asctime)-15s ][ %(levelname)-7s ][ %(host)s ]"
                                 "[ %(processName)-11s ][ %(message)s ]"
                                 "[ %(module)s.%(funcName)s(%(lineno)d) ]"),
                 'default': ("[ %(asctime)-15s ][ %(levelname)-7s ][ %(host)s ]"
                             "[ %(processName)-11s ][ %(message)s ]"),
                 }

RECOVER_ARGS_DIR = '/tmp'
RECOVER_ARGS_FILE = 'eventor_agent_args'


def new_recvoer_args_file(name=None):
    file = "{}.".format(name) if name else ""
    file = "{}{}.{}.dat".format(file, RECOVER_ARGS_FILE, os.getpid())
    file = os.path.join(RECOVER_ARGS_DIR, file)
    return file


def last_recvoer_args_file():
    files = filter(lambda x: os.path.isfile(x) and x.startswith(RECOVER_ARGS_FILE), os.listdir(RECOVER_ARGS_DIR))
    files = [os.path.join(RECOVER_ARGS_DIR, f) for f in files]  # add path to each file
    files.sort(key=lambda x: os.path.getmtime(x))
    return files[-1] if len(files) > 0 else None


def cmdargs(args=None):
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
                            help=("File to store or recover memory. With --pipe, it would store"
                                  " memory into file. Without --pipe, it would recover memory from"
                                  " store"))
    parser_act.add_argument('--pipe', action='store_true',
                            help=("Indicates that memory should be read from STDIN. If --pipe not"
                                  " provided, --file must be."))
    parser_act.add_argument('--debug', action='store_true',
                            help="Invokes additional debug utilities, e.g., store args for recovery.")

    parser_rec.add_argument('--file', type=str, required=False,
                            help="""File from which to restore previous args""")
    pargs = parser.parse_args(args=args)

    assert pargs.file is not None or pargs.pipe, "--pipe or --file must be provided."

    return pargs


def do_imports(imports):
    imports = imports_from_cmd(imports)
    mlogger.debug("Importing {}.".format(imports))
    for import_file, import_modules in imports:
        if not import_file:
            for module in import_modules:
                mlogger.debug("Importing %s." % (module))
                try:
                    from importlib import import_module
                    import_module(module)
                except Exception as e:
                    mlogger.critical("Failed to import: %s." % (module))
                    mlogger.exception(e)
                    # signal to parent via stdout
                    print('TERM')
                    print(e, file=sys.stderr)
                    return
        else:
            for module in import_modules:
                mlogger.debug("Importing %s from %s." % (module, import_file))
                try:
                    spec = importlib.util.spec_from_file_location(module, import_file)
                    spec_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(spec_module)
                    # sys.modules[import_module] = module # not needed for now
                except Exception as e:
                    mlogger.critical("Failed to import: %s %s;" % (import_module, import_file))
                    mlogger.exception(e)
                    # signal to parant via stdout
                    print('TERM')
                    print(e, file=sys.stderr)
                    return


def start_eventor(queue, logger_info, **kwargs):
    global mlogger
    mlogger = Logger.get_logger(logger_info,)  # logger_info['name'])
    mlogger.debug('Starting EventorAgent:\n{}'.format(pprint.pformat(kwargs, indent=4)))
    try:
        eventor = Eventor(**kwargs)
    except Exception as e:
        mlogger.critical("Failed to start EventorAgent.")
        mlogger.exception(e)
        queue.put(('TERM', e))
        return

    mlogger.debug('Initiated EventorAgent object, going to run().')

    try:
        eventor.run()
    except Exception as e:
        mlogger.critical("Failed to run EventorAgent, passing TERM to main process.")
        mlogger.exception(e)
        queue.put(('TERM', e))
    else:
        mlogger.debug('EventorAgent finished: passing DONE to main process.')
        queue.put(('DONE', ''))


def pull_from_pipe(queue=None,):
    ''' Pipe listener wait for one message.  Once receive (DONE or TERM) it ends.
    '''
    global mlogger

    def set_result(msg, e):
        if queue is not None:
            queue.put((msg, e))
            return
        else:
            return (msg, e)

    # in this case, whiting for possible termination message from server
    try:
        msgsize_raw = sys.stdin.buffer.read(4)
    except Exception as e:
        mlogger.critical('Failed to read STDIN.')
        mlogger.exception(e)
        return set_result('TERM', e)
    try:
        msgsize = struct.unpack(">L", msgsize_raw)
    except Exception as e:
        mlogger.critical('Failed pickle loads message size from STDIN; received: %s' % hex(msgsize_raw))
        mlogger.exception(e)
        return set_result('TERM', e)
    try:
        msg_pack = sys.stdin.buffer.read(msgsize[0])
    except Exception as e:
        mlogger.critical('Failed to read STDIN.')
        mlogger.exception(e)
        return set_result('TERM', e)
    try:
        msg = pickle.loads(msg_pack)
    except Exception as e:
        mlogger.critical('Failed pickle loads message from STDIN.')
        mlogger.exception(e)
        return set_result('TERM', e)

    mlogger.debug('Received message from remote parent: {}; passing to main process.'.format(msg))

    return set_result(msg, '')


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
        mlogger.debug("Agent is not alive! terminating.")
        print('TERM')
        print("Agent aborted unexpectedly.", file=sys.stderr)
        return False
    return True


def logger_remote_handler(logger_queue, log_info_recv, ssh_host,):
    try:
        remote_logger_handler = SSHLoggerClientHandler(logger_info=log_info_recv, ssh_host=ssh_host)
    except Exception as e:
        raise EventorAgentError("Failed to create SSHLoggerClientHandler on: {}; {}"
                                .format(ssh_host), repr(e))

    listener = logging.handlers.QueueListener(logger_queue, remote_logger_handler)
    listener.start()
    return listener


class EventorAgentQueueHandler(logging.handlers.QueueHandler):
    def __init__(self, queue):
        super(EventorAgentQueueHandler, self).__init__(queue)
        self.emitter = open("/var/log/eventor/eventor_agent_queue_handler_records.log", 'w')
        self.count = 0

    def emit(self, record):
        self.count += 1
        self.emitter.write("{}: \n".format(repr(record.__dict__)))
        logging.handlers.QueueHandler.emit(self, record)

    def __del__(self):
        self.emitter.close()


class SSHPipeEventorAgent(sp.SSHPipeHandler):
    ''' SSHPipeSocketHandler modeled over logging.handlers.SocketHandler
    '''

    def __init__(self, agent_args, *args, **kwargs):
        super(sp.SSHPipeHandler, self).__init__(*args, **kwargs)
        self.agent_args = agent_args
        self.mlogger.debug("EventorAgent params:\n{}.".format(self.args))

    def atstart(self, receieved):
        args = self.agent_args
        log_info, imports, host, ssh_host, pipe, file = \
        args.log_info, args.imports, args.host, args.ssh_host, args.pipe, args.file

    def atexit(self, received):
        # if self.file is not None:
        #     self.file.close()
        super(sp.SSHPipeHandler, self).atexit(received)
        self.mlogger.debug("Closed handlers.")

    def handle(self, received):
        """
        Send a pickled string to the socket.

        This function allows for partial sends which can happen when the
        network is busy.
        """
        # self.file.write(str(received))
        self.emit(received)
        self.mlogger.debug("Emitted record to socket: {}.".format(received))


def run(args):
    client = SSHPipeEventorAgent(args)
    client.service_loop()


def initiate_logger(log_info):
    global mlogger
    log_info_recv = yaml.load(log_info)
    handler_kwargs = log_info_recv['handler_kwargs']
    logger_info_local = copy(log_info_recv)
    del logger_info_local['port']
    del logger_info_local['handler_kwargs']

    logger_kwargs = {}
    logger_kwargs.update(logger_info_local)
    logger_kwargs.update(handler_kwargs)
    logger_queue = mp.Queue()
    queue_handler = logging.handlers.QueueHandler(logger_queue)
    logger = Logger(console=False, handlers=[queue_handler], **logger_kwargs)
    logger.start()

    logger_info = logger.logger_info()
    mlogger = Logger.get_logger(logger_info=logger_info)

    return logger, logger_info_local, logger_queue, log_info_recv, logger_info


def run_eventor(args):
    ''' Runs EventorAgent in remote host.

    Args:
        log_info
        imports
        host
        file
        pipe
    '''
    global mlogger

    run, recovery = args.run, args.recover

    if run:
        log_info, imports, host, ssh_host, pipe, file, debug = \
            args.log_info, args.imports, args.host, args.ssh_host, args.pipe, args.file, args.debug
    else:  # recovery:
        # this is recovery: read args from file
        file = args.file
        with open(file, 'rb') as f:
            args = pickle.load(f)
            memory = pickle.load(f)
            # Dont take pipe, and file from arg store
            log_info, imports, host, ssh_host, debug = \
                args.log_info, args.imports, args.host, args.ssh_host, args.debug

    logger, logger_info_local, logger_queue, log_info_recv, logger_info = initiate_logger(log_info)

    mlogger.debug("Starting agent: {}.".format(args))

    # In case of debug, store arguments.
    # but, also, it is not recovery (pipe is provided)
    if debug and not recovery and file:
        file = new_recvoer_args_file(file)
        try:
            with open(file, 'wb') as f:
                pickle.dump(args, f)
        except Exception as e:
            mlogger.exception(e)
            mlogger.debug("Failed to store args.")
            close_run(logger=logger, msg="TERM", err=e)
            return

        mlogger.debug("Stored agent args: {}".format(file))

    mlogger.debug('Local logger:\n{}'.format(logger_info_local))
    mlogger.debug('Module logger:\n{}'.format(log_info))

    try:
        dipatcher_to_remote_logger = logger_remote_handler(logger_queue, log_info_recv=log_info_recv, ssh_host=ssh_host,)  # logdir=handler_kwargs['logdir'])
    except Exception as e:
        mlogger.exception(e)
        mlogger.debug("Failed to to create remote logger on: {}.".format(ssh_host))
        close_run(logger=logger, msg="TERM", err=e)
        return

    mlogger.debug('Started logger_remote_handler: {}.'.format(ssh_host))

    if imports is not None:
        do_imports(imports)

    if run:
        mlogger.debug("Fetching workload. from pipe.")

        memory, e = pull_from_pipe()
        if e:
            mlogger.critical("Failed to get Eventor memory from pipe.")
            close_run(dipatcher_to_remote_logger, logger, msg='TERM', err=e)
            return

        # store memory into file
        if not recovery and file and debug:
            mlogger.debug("Storing workload to {}.".format(file))
            try:
                with open(file, 'ab') as file:
                    pickle.dump(memory, file)
            except Exception as e:
                mlogger.critical("Failed to pickle dump workload to {}.".format(file))
                mlogger.exception(e)
                close_run(dipatcher_to_remote_logger, logger, msg='TERM', err=e)
                return
    '''
    else:
        mlogger.debug("Fetching workload from file.")
        try:
            with open(file, 'rb') as file:
                memory = pickle.load(file)
        except Exception as e:
            mlogger.critical("Failed to pickle load workload from {}.".format(file))
            mlogger.exception(e)
            close_run(dipatcher_to_remote_logger, logger, msg='TERM', err=e)
            return
    '''
            
    mlogger.debug("Memory received:\n{}".format(pprint.pformat(memory, indent=4, )))

    try:
        kwargs = memory.kwargs.copy()
        # change logger_info to this agent logger info.
        memory.logger_info = logger_info
        kwargs['host'] = host
        kwargs['memory'] = memory
    except Exception as e:
        mlogger.critical("Failed get kwargs from received memory.")
        mlogger.exception(e)
        close_run(dipatcher_to_remote_logger, logger, msg='TERM', err=e)
        return

    mlogger.debug("Starting Eventor subprocess on remote host.") #:\n%s" % pprint.pformat(kwargs, indent=4))

    child_q = mp.Queue()
    eventor_listener_q = mp.Queue()
    kwargs['listener_q'] = eventor_listener_q

    try:
        agent = mp.Process(target=start_eventor, args=(child_q, logger_info,), kwargs=kwargs, daemon=False)
        agent.start()
    except Exception as e:
        mlogger.critical("Failed to start Eventor process.")
        mlogger.exception(e)
        close_run(dipatcher_to_remote_logger, logger, msg='TERM', err=e)
        return

    mlogger.debug("Eventor subprocess pid: {}".format(agent.pid))

    # wait for remote parent or from child Eventor
    if not check_agent_process(agent):
        mlogger.debug("Agent process is dead, exiting. pid: {}".format(agent.pid))
        close_run(dipatcher_to_remote_logger, logger, )  # msg='TERM', err=error)
        return

    mlogger.debug("Starting EventorAgent select loop.")
    loop_is_active = True
    while loop_is_active:
        rselected, _, _ = select.select([child_q._reader, sys.stdin],[],[])
        mlogger.debug("Returned from select: {}.".format(repr(rselected)))

        for ioitem in rselected:
            if ioitem == sys.stdin:
                result = pull_from_pipe()
                mlogger.debug("Received from select remote parent: {}.".format(result))
                if result:
                    # received FINISH, STOP, or QUIT message from parent
                    loop_is_active = False
            elif ioitem == child_q._reader:
                result = child_q.get(timeout=0.5)
                mlogger.debug("Received from select local Eventor: {}.".format(result))
                if result:
                    agent.join()
                    loop_is_active = False

    msg, error = result
    mlogger.debug("Pulled message from control queue: message: {}; error: {}.".format(msg, error,))
    if msg == 'DONE':
        # msg from child - eventor agent is done
        mlogger.debug("Joining with Eventor process after: {}.".format(msg))
        agent.join()
        close_run(dipatcher_to_remote_logger, logger, )
    elif msg == 'TERM':
        # TODO: need to change message from parent to STOP - not TERM
        # got message to quit, need to kill primo process and be done
        # Well since process is daemon, it will be killed when parent is done
        eventor_listener_q.put('STOP')
        mlogger.debug("Joining with Eventor process after: {}.".format(msg))
        agent.join()
        close_run(dipatcher_to_remote_logger, logger, msg='TERM', err=error)
        # TODO(Arnon): how to terminate listener that is listening
    elif msg in ['STOP', 'FINISH']:
        # TODO: need to change message from parent to STOP - not TERM
        # got message to quit, need to kill primo process and be done
        # Well since process is daemon, it will be killed when parent is done
        eventor_listener_q.put('STOP')
        mlogger.debug("Joining with Eventor process after: {}.".format(msg))
        agent.join()
        result = child_q.get(timeout=0.5)
        mlogger.debug("Eventor process joint result: {}.".format(result))
        close_run(dipatcher_to_remote_logger, logger, msg='DONE', err=error)


def close_run(listener=None, logger=None, msg=None, err=None):
    global mlogger

    if msg is not None:
        print(msg)
    if err is not None:
        print(err, file=sys.stderr)

    mlogger.debug("Closing EventorAgent dipatcher_to_remote_logger.")
    if listener:
        listener.stop()

    mlogger.debug("Closing EventorAgent logger.")
    if logger:
        logger.stop()


'''
def recover_eventor(args):
    file = args.file
    if file is None:
        file = last_recvoer_args_file()
    if file is not None:
        with open(file, 'rb') as f:
            saved_args = pickle.load(f)
        run_eventor(saved_args)
    else:
        raise EventorAgentError("Trying to run in recovery, but no recovery file found.")
'''

if __name__ == '__main__':
    # mp.freeze_support()
    # mp.set_start_method('spawn')
    
    
    args = cmdargs()
    '''
    if args.run:
        run_eventor(args)
    else:
        recover_eventor(args)
    '''
    run_eventor(args)
    '''
    args = cmdargs(['rec', '--file', 'myfile'])
    print(args)
    '''
    
