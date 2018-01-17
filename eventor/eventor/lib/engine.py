'''
Created on Nov 23, 2016

@author: arnon
'''

import logging
from acrilib import Sequence, MergedChainedDict
from acrilog import SSHLogger as Logger
from acris import virtual_resource_pool as vrp
import multiprocessing as mp
from threading import Thread
from collections import namedtuple
import inspect
from enum import Enum
import os
import pickle
import queue
import time
from datetime import datetime
import signal
import yaml
from functools import reduce
from copy import deepcopy
from .step import Step
from .event import Event
from .delay import Delay
from .assoc import Assoc
from .dbapi import DbApi
from .utils import calling_module, traces, rest_sequences
from .utils import store_from_module, get_delay_id, port_is_open
# from eventor.utils import logger_process_lambda
from .eventor_types import Invoke, EventorError, TaskStatus, LoopControl
from .eventor_types import step_to_task_status, task_to_step_status
from .eventor_types import StepStatus, StepReplay, RunMode, DbMode
from eventor import __version__, __db_version__
from .dbschema import Task
from .conf_handler import merge_configs
from .etypes import MemEventor
import sshpipe as sp
from acrilib import get_hostname, get_ip_address, traced_method, expandmap
from .utils import decorate_all, print_method


# try:
#     from setproctitle import setproctitle
# except:
#     setproctitle = None
setproctitle = None

mlogger = None  # logging.getLogger(__file__)

# traced=traced_method(None, True)

RUN_ID_SEPARATOR = '-'


def get_unique_run_id():
    ip = get_ip_address()
    ips = ''.join(ip.split('.'))
    now = datetime.now().strftime("%Y%m%d%H%M%S")
    parts = [os.getpid(), ips, now]
    result = RUN_ID_SEPARATOR.join(map(str, parts))
    return result


class TaskAdminMsgType(Enum):
    result = 1
    update = 2


RemoteAgent = namedtuple("remoteHost", "proc stdin stdout")
TaskAdminMsg = namedtuple('TaskAdminMsg', ['msg_type', 'value', ])
TriggerRequest = namedtuple('TriggerRequest', ['type', 'value'])


class ResourceAllocationCallback(object):
    def __init__(self, notify_queue):
        self.q = notify_queue

    def __call__(self, resources=None):
        self.q.put(resources)


def task_wrapper(run_id=None, task=None, step=None, adminq=None, use_process=True, logger_info=None, eventor=None, config=None):
    '''
    Args:
        func: object with action method with the following signature:
            action(self, action, unit, group, sequencer)
        action: object with taskid, unit, group: id of the unit to pass
        sqid: sequencer id to pass to action '''
    global mlogger

    # only if in separate process, need to initiate logger
    logger_name = ''
    if use_process:
        logger_name = "{}.{}_{}".format(logger_info['name'], step.name, task.sequence)
        mlogger = Logger.get_logger(logger_info=logger_info, name=logger_name)

    # else:
    #    mlogger = Logger.get_logger(logger_info=logger_info, name="%s" %(logger_info['name'],))

    task.pid = os.getpid()
    envvar_prefix = config.get('envvar_prefix', 'EVENTOR_')
    os.environ['{}STEP_NAME'.format(envvar_prefix)] = str(step.name)
    os.environ['{}STEP_SEQUENCE'.format(envvar_prefix)] = str(task.sequence)
    os.environ['{}STEP_RECOVERY'.format(envvar_prefix)] = str(task.recovery)
    os.environ['{}LOGGER_NAME'.format(envvar_prefix)] = str(logger_name)

    if setproctitle is not None and use_process:
        run_id_s = "%s." % run_id if run_id else ''
        setproctitle("Eventor: {}{}.{}({})".format(run_id_s, step.name, task.id_, task.sequence))

    # Update task with PID
    update = TaskAdminMsg(msg_type=TaskAdminMsgType.update, value=task)
    try:
        adminq.put(update)
    except Exception as e:
        mlogger.critical('[ Task {}/{} ] Failed to update pid; aborting'
                         .format(step.name, task.sequence))
        mlogger.exception(e)
        raise

    mlogger.info('[ Task {}/{} ] Attempting to run'.format(step.name, task.sequence))

    try:
        # TODO: need to pass task resources.
        result = step(seq_path=task.sequence, logger=mlogger, eventor=eventor)
    except Exception as e:
        trace = inspect.trace()
        trace = traces(trace)
        task.result = (e, pickle.dumps(trace))
        task.status = TaskStatus.failure
    else:
        task.result = result
        task.status = TaskStatus.success

    result = TaskAdminMsg(msg_type=TaskAdminMsgType.result, value=task)
    mlogger.info('[ Task {}/{} ] Completed, status: {}'
                 .format(step.name, task.sequence, str(task.status)))
    adminq.put(result)
    return True


class EventorState(Enum):
    active = 1
    shutdown = 2
    # exit = 3


class RpCallback(object):
    def __init__(self, notify_queue, task_id=''):
        self.q = notify_queue
        self.task_id = task_id

    def __call__(self, ready=False):
        self.q.put(self.task_id)


class Memtask(object):
    def __init__(self, task, ):
        self.id_ = task.id_
        self.step_id = task.step_id
        self.sequence = task.sequence
        self.requestor = None
        self.fueled = False
        self.request_id = None


# This is to keep program artifacts as they are given for __repr__ purpoces
ProgramArtifacts = namedtuple('ProgramArtifacts', "events steps assocs")


def get_proc_constructor(task_construct,):
    if task_construct == 'process' or task_construct == mp.Process:
        task_constructor = mp.Process
    elif task_construct == 'thread' or task_construct == Thread:
        task_constructor = Thread
    elif task_construct == 'invoke' or task_construct == Invoke:
        task_constructor = Invoke
    else:
        task_constructor = None
    return task_constructor


def make_imports(import_file, import_module):
    imports = None
    import_module = import_module if import_module is not None else []
    import_file = import_file if import_file is not None else ''
    if len(import_module) > 0:
        imports = "%s:%s" % (import_file, ':'.join(import_module))
    return imports


class Eventor(object):
    """Eventor manages events and steps that needs to be taken when raised.

    Eventor provides programming interface to create events, steps and associations among them.
    It provides means to raise events, and a service that would perform steps
    according to those events.

    Attributes:
        controlq: mp queue is used to control endless eventor loop

    Methods:
        add_event: adds event into the system
        add_step: adds step into the system
        add_assoc: associates event with step
        run: run eventor processing; eventor will return when no work is left to be done.

    """

    config_defaults = {
        'workdir': '/tmp',
        'debug': False,
        'task_construct': 'process',  # or 'thread'
        'envvar_prefix': 'EVENTOR_',
        'max_concurrent': -1,
        'stop_on_exception': True,
        'sleep_between_loops': 0.25,
        'sequence_arg_name': None,  # 'eventor_task_sequence'
        'day_to_keep_db': 5,
        'remote_method': 'ssh',
        'pass_logger_to_task': False,
        # TODO: (arnon) need to solve dbapi overide of logging when using shared_db False
        'shared_db': False,
        'ssh_config': os.path.expanduser('~/.ssh/config'),
        'ssh_host': get_hostname(),
        'ssh_port': 22,
        'DATABASES': {'dialect': 'sqlite', 'query': {'cache': 'shared'}},
        'LOGGING': {
            'logdir': os.path.expanduser('~/log/eventor'),
            'datefmt': '%Y-%m-%d,%H:%M:%S.%f',
            'logging_level': logging.INFO,
            'level_formats': {
                logging.DEBUG: ("[ %(asctime)-15s ][ %(levelname)-7s ][ %(host)s ]"
                                "[ %(processName)-11s ][ %(message)s ]"
                                "[ %(module)s.%(funcName)s(%(lineno)d) ]"),
                'default': ("[ %(asctime)-15s ][ %(levelname)-7s ][ %(host)s ]"
                            "[ %(processName)-11s ][ %(message)s ]"),
                },
            'consolidate': False,
            'console': True,
            'file_prefix': None,
            'file_suffix': None,
            'file_mode': 'a',
            'maxBytes': 0,
            'backupCount': 0,
            'encoding': 'utf8',
            'delay': False,
            'when': 'h',
            'interval': 1,
            'utc': False,
            'atTime': 86400,  # number of seconds in a day
        },
    }

    # TODO: (Arnon) build db cleanup subprocess using day_to_keep_db

    recovery_defaults = {
        StepStatus.ready: StepReplay.rerun,
        StepStatus.allocate: StepReplay.rerun,
        StepStatus.fueled: StepReplay.rerun,
        StepStatus.active: StepReplay.rerun,
        StepStatus.failure: StepReplay.rerun,
        StepStatus.success: StepReplay.skip, }

    # TODO: (Arnon) SSH HOST as server to send logging to.

    def __init__(self, name='', store='', run_mode=RunMode.restart, recovery_run=None, host=None, remotes=[], run_id='', config={}, config_tag=None, memory=None, import_module=None, import_file=None,listener_q=None):
        """initializes steps object

        Args:
            name (str): human readable identifying Eventor among other eventors
            store (path): file in which Eventor data would be stored and managed for reply/restart
                if the value is blank, filename will be based on calling module
                if the value is :memory:, an in-memory temporary structures will be used

            run_mode: (RunMode) set Eventor to operate in recovery, restart, or continue
            recovery_run (int): since 'store' maintain historical runs, recovery can engage any
                previous run.  recovery_run, if provided, will tell Eventor which run to recover.
                If not provided, latest run is assumed.
            host: hostname or ip address for steps with not specified host;
            if none, current THIS host will be used.
            remotes: hint to Eventor for remote host associated with hidden steps
            (steps that will be deposit on-the-fly).
            shared_db: (boolean) if set, indicates that the database used is by multiple
                programs or instances thereof. 
            run_id: (str) if shared_db, run_id must be unique program execution among all programs
                    sharing.  If not provided and shared_db is set, unique run_id
                    will be generated.
                    When in recovery, and shared_db is set, run_id must be provided to identify the
                    program and its run to be recovered.
            listener_q: (mp.queue) Termination messages from initiator can be sent
                    through this queue.
            import file: a file path from which to import modules
            import module: list of modules to load

            config: configuration parameters to be used in operating eventor.
            can be file with YAML style configuration or a dictionary
                parameters can include the following keys:
                - workdir=/tmp,
                - debug=False
                - task_construct=mp.Process,
                - stop_on_exception=True,
                - sleep_between_loops=1
                - ssh_config: provides alternative to ~/.ssh/config
                - ssh_host: name of SSH config (~/.ssh/config) Host to use for SSH back channel
                - databases: if config is provided,
                    it will try to fetch store or name as code for database.
                    if both not provided, will try default database code.
                    if not found, will treat store and name as above.

                    DATABASES:
                        default:
                            dialect:  postgresql
                            drivername :  psycopg2
                            username: mydatabaseuser
                            password: mydatabasepass
                            host:     localhost
                            port:     5433
                            database: postgres
                            schema:   eventor

                        playfile:
                            dialect: sqlite
                            file: /var/database/alchemy/schema.db

                - hosts: mapping of tag -> hostname/ip.
                    tag can then be used in add_step() instead of full qualifying name.

                    HOSTS:
                        mainhost: 192.168.1.71
                        process:  192.168.1.70

                - logging:
                    LOGGING:
                        logdir: /var/log/eventor
                        logging_level: INFO
                        consolidate: False
                        console: True
                        file_prefix: None
                        file_suffix: None
                        file_mode: 'a'
                        maxBytes: 0
                        backupCount: 0
                        encoding: 'utf8'
                        delay: False
                        when: 'h'
                        interval: 1
                        utc: False
                        atTime: 86400, # number of seconds in a day
        Returns:
            new object

        Raises:
            N/A
        """
        global mlogger

        # store input arguments
        eventor_kwargs = locals()
        del eventor_kwargs['self']

        if not name:
            name = calling_module()
            name = os.path.basename(name)
        self.name = name  # .replace('.', '_')
        self.remotes = remotes

        if import_file is not None and import_module is None:
            raise EventorError("Import_file is provided but not import_module.")
        # TODO: (Arnon) implement calling module
        imports = make_imports(import_file, import_module)
        self.imports = [imports] if imports else []

        # fetches configuration according to config_tag.
        # _config_tag will be set by 'EVENTOR_CONFIG_TAG' environment variable, if not provided.
        self.__config = merge_configs(config, Eventor.config_defaults, config_tag,
                                      envvar_config_tag='EVENTOR_CONFIG_TAG', )

        '''
        if config_tag is None:
            config_tag = os.environ.get('EVENTOR_CONFIG_TAG', '')

        if isinstance(config, str):
            frame = inspect.stack()[1]
            module = inspect.getsourcefile(frame[0])
            config_path = os.path.join(os.path.dirname(module), config)
            if os.path.isfile(config_path):
                config = config

        rootconfig = getrootconf(conf=config, root=config_tag, case_sensative=False)
        defaults = expandmap(Eventor.config_defaults)
        # defaults = dict([(name, expandvars(value, os.environ)) for name,
        #     value in Eventor.config_defaults.items()])
        self.__config = MergedChainedDict(rootconfig, defaults, submerge=True)
        '''

        self.debug = self.__config['debug']
        # HOSTS configuration mapping of host tags to host names
        hosts_root_name = os.environ.get('EVENTOR_CONFIG_HOSTS_TAG', 'HOSTS')
        # self.hosts = rootconfig.get(hosts_root_name, {})
        self.hosts = self.__config.get(hosts_root_name, {})
        if host is None:
            self.host = get_hostname()
        else:
            # try to see if provided host is mapped in configuration
            self.host = self.hosts.get(host, host)

        self.ssh_config = self.__config.get('ssh_config',)
        self.ssh_port = self.__config.get('ssh_port', 22)
        self.ssh_host = self.__config.get('ssh_host', self.host)

        self.__memory = MemEventor() if memory is None else memory
        self.__is_server = memory is None
        if self.__is_server:
            self.__memory.kwargs.update(eventor_kwargs)

        self.__tasks = dict()

        # TODO: (arnon) Issue with shared_db=False due to SQLite overide logging parameters.
        self.shared_db = self.__config.get('shared_db', False)
        # self.shared_db = True

        self.run_id = run_id if run_id is not None else ''
        assert isinstance(self.run_id, str), "run_id must be string; but found {}.".format(type(run_id).__name__)
        if self.shared_db and not self.run_id:
            if run_mode != RunMode.restart:
                raise EventorError("When shared_db is set in restart, run_id must be provided.")
            # in this case we need to produce unique run_id on this cluster
            self.run_id = get_unique_run_id()
            self.__memory.kwargs['run_id'] = self.run_id

        self.__set_logger(memory)

        # TODO: (Arnon) in case of Sequent, depth is 3 and not 2 as default.
        #     Need to find way to drive calling module.

        # Since SSHLogger started, need to close if exception occurs.
        try:
            self.__calling_module = calling_module()
            self.store = store

            self.__task_proc = dict()
            self.__state = EventorState.active
            self.__run_mode = run_mode
            self.__recovery_run = recovery_run
            self._session_cycle_loop = False

            mlogger.info("Process PID: {}; run_id: {}.".format(os.getpid(), repr(self.run_id),))
            mlogger.debug("Process is server: {}.".format(self.__is_server))
            mlogger.debug("Logger info: {}.".format(self.__logger_info))
            rest_sequences()
            self.__setup_db_connection(create=self.__is_server)

            self.__program_artifacts = ProgramArtifacts(dict(), dict(), list())

            self.__listener_q = listener_q
        except Exception:
            self.close()
            raise

    def _pdebug(self, msg):
        if getattr(self, 'pdebug', False):
            return
        with open("/tmp/eventor.info.{}.txt".format(os.getpid()), 'a') as info:
            info.write(msg + '\n')

    def __set_logger(self, memory):
        global mlogger

        logging_config = self.__config.get('LOGGING')

        # TODO: (Arnon) get to logging configuration (as in Database)
        # TODO: (Arnon) drive encoding from parameter
        # TODO: (Arnon) log name needs to be driven by calling
        logger_name = "{}{}".format(self.name, "-{}"
                                    .format(self.run_id.replace("@", "-")) if self.run_id else '')

        self._pdebug("server" if self.__is_server else "client")

        if self.__is_server:
            self.__logger_params = {
                'name': logger_name,
                }
            self.__logger_params.update(logging_config)
            self.__logger = Logger(**self.__logger_params)
            self.__logger.start()
            self.__logger_info = self.__logger.logger_info()
            self._pdebug("logger: {}".format(logger_name))
            self._pdebug("logger: {}".format(self.__logger_info))
            mlogger = Logger.get_logger(logger_info=self.__logger_info, name=logger_name)
            # mlogger.debug('Logger listens on port {}.'.format(self.__logger.port))
        else:
            # agent needs two log handlers. One is logging back into the server.
            # The other is local log service.
            # Logger.get_logger will add logger handler that would start

            self._pdebug("logger: {}".format(logger_name))
            self._pdebug("logger: {}".format(memory.logger_info))
            mlogger = Logger.get_logger(logger_info=memory.logger_info, name=logger_name)
            self.__logger_info = memory.logger_info
            self.__logger_info['name'] = logger_name
            self.__logger = None

    def __get_dbapi(self, create=True):
        filename = store_from_module(self.__calling_module)
        db_mode = DbMode.write if self.__run_mode == RunMode.restart else DbMode.append
        try:
            self.db = DbApi(config=self.__config, modulefile=filename, shared_db=self.shared_db,
                            run_id=self.run_id, userstore=self.store, mode=db_mode, create=create,
                            echo=False, logger=mlogger)
        except Exception:
            raise

    def get_logger(self):
        global mlogger
        return mlogger

    def add_remote(self, remotes):
        mlogger.debug('Adding remote: {}.'.format(remotes))
        if isinstance(remotes, str):
            self.remotes.append(remotes)
        elif isinstance(remotes, list):
            self.remotes.extend(remotes)
        else:
            raise EventorError('Expecting remotes of type str or list, but got: {}'
                               .format(type(remotes).__name__))

    def __setup_db_connection(self, create=True):
        global mlogger

        self.__get_dbapi(create=create)
        if self.__run_mode == RunMode.restart and self.__is_server:
            self.__write_info()
        else:
            self.__read_info(run_mode=self.__run_mode, recovery_run=self.__recovery_run)

    def __repr__(self):
        steps = '\n'.join([repr(step) for step in self.__memory.steps.values()])
        events = '\n'.join([repr(event) for event in self.__memory.events.values()])
        assocs = '\n'.join([repr(assoc) for assoc in self.__memory.assocs.values()])
        result = ("Steps( name( {} ) events( {} ) steps( {} ) assocs( {} )  )"
                  .format(self.name, events, steps, assocs))
        return result

    def __str__(self):
        steps = '\n    '.join([str(step) for step in self.__memory.steps.values()])
        events = '\n    '.join([str(event) for event in self.__memory.events.values()])
        assocs = '\n    '.join([str(assoc) for assoc in self.__memory.assocs.values()])
        result = ("Steps( name( {} )\n    events( \n    {}\n   )\n    steps( \n    {}\n   )\n"
                  "    assocs( \n    {}\n   )  )".format(self.name, events, steps, assocs))
        return result

    def program_repr(self):
        prog = list()
        for name, value in self.__program_artifacts.events.items():
            text = "%s = add_event(%s, expr=%s)" % (name, repr(name), repr(value))
            prog.append(text)

        signature = ['func', 'args', 'kwargs', 'triggers', 'host', 'acquires', 'releases',
                     'recovery', 'config', 'import_file', 'import_module']
        for name, values in self.__program_artifacts.steps.items():
            args = list()
            for title, arg in zip(signature, values):
                args.append("{}={}".format(title, repr(arg)))
            text = "{} = add_step({}, {})".format(name, repr(name), ', '.join(args))
            prog.append(text)

        signature = ['event', 'assocs', 'delay']
        for values in self.__program_artifacts.assocs:
            items = dict(zip(signature, values))
            assocs = ["{}({})"
                      .format(type(assoc).__name__, repr(assoc.name)) for assoc in items['assocs']]
            args = "{}, {}, delay={}".format(items['event'].name,
                                             ', '.join(assocs), repr(items['delay']))
            text = "add_assoc(%s)" % (args)
            prog.append(text)
        return '\n'.join(prog)

    def _name(self, seq_path):
        result = '/'
        if self.name:
            result = "{}{}".format(self.name, "/{}".format(seq_path) if seq_path else '')
        return result

    def __write_info(self, run_file=None):
        self.__recovery = 0
        info = {'app_version': __version__,
                'db_version': __db_version__,
                'program': self.__calling_module,
                'recovery': self.__recovery,
                }
        self.db.write_info(**info)
        self.__previous_tasks = None
        self.__previous_delays = None

    def __read_info(self, run_mode=None, recovery_run=None):
        self.__info = self.db.read_info()
        recovery = recovery_run
        if recovery is None:
            previous_recovery = self.__info['recovery']
        if self.__run_mode == RunMode.recover:
            recovery = str(int(previous_recovery) + 1)
            self.db.update_info(recovery=recovery)
        else:
            recovery = previous_recovery
        self.__recovery = recovery
        # self.previous_triggers=self.db.get_trigger_map(recovery=recovery)
        self.__previous_tasks = self.db.get_task_map(recovery=previous_recovery)
        self.__previous_delays = self.db.get_delay_map(recovery=previous_recovery)

    def __convert_trigger_at_complete(self, triggers):
        at_compete = triggers.get(StepStatus.complete)
        if at_compete:
            del triggers[StepStatus.complete]
            at_fail = triggers.get(StepStatus.failure, list())
            at_success = triggers.get(StepStatus.success, list())
            at_fail.extend(at_compete)
            at_success.extend(at_compete)
            triggers[StepStatus.failure] = at_fail
            triggers[StepStatus.success] = at_success
        return triggers

    def __convert_recovery_at_complete(self, recovery):
        at_compete = recovery.get(StepStatus.complete)
        if at_compete is not None:
            del recovery[StepStatus.complete]
            at_fail = recovery.get(StepStatus.failure, at_compete)
            at_success = recovery.get(StepStatus.success, at_compete)
            recovery[StepStatus.failure] = at_fail
            recovery[StepStatus.success] = at_success
        return recovery

    def add_event(self, name, expr=None):
        """add a event to Eventor object

        Args:
            name: (string) unique identifier provided by caller
            expr:

        returns:
            new event that was added to Eventor; this event can be used further in assoc method
        """
        self.__program_artifacts.events[name] = expr

        try:
            event = self.__memory.events[name]
        except Exception:
            pass
        else:
            if expr == event.expr:
                return event

        event = Event(name, expr=expr, logger=mlogger)
        self.__memory.events[event.id_] = event
        mlogger.debug('add_event: {}'.format(repr(event)))
        return event

    def get_step(self, name):
        return self.__memory.steps.get(name, None)

    def add_step(self, name, func=None, args=(), kwargs={}, triggers={}, host=None, acquires=None, releases=None, recovery={}, config={}, import_file=None, import_module=None):
        """add a step to steps object

        config parameters can include the following keys:
            - stop_on_exception=True
            - sequence_arg_name=None : when set, corresponding name will be used as keyword
                argument to passed sequence to step
            #- pass_resources=False: when set, eventor_task_resources keyword argument will
                be passed to step

        Args:
            name: (string) unique identifier
            func: (callable) if provided, will be called when step is activated;
                otherwise its nope step.
            func_args: args to pass step when executing.
            func_kwargs: keyword args to pass step when executing.
            config: additional dict of keywords configuration.
            triggers: set of events to trigger once step processing is done.
            host: host on which step should run on.
            acquires: list of resources to acquire before starting.
            releases: list of resources to release once done;
                defaults to acquires. if not provided.
            recovery: instructions on how to deal with
                default: {TaskStatus.failure: StepReplay.rerun,
                          TaskStatus.success: StepReplay.skip}

        returns:
            new step that was added to Eventor; this step can be used further in assoc method

        raises:
            EventorError: if func is not callable
        """
        try:
            artifact_name = func.__name__
        except AttributeError:
            try:
                artifact_name = type(func).__name__
            except Exception:
                artifact_name = name

        self.__program_artifacts.steps[name] = (artifact_name, args, kwargs, triggers, host,
                                                acquires, releases, recovery, config,
                                                import_file, import_module)

        if import_file is not None and import_module is None:
            raise EventorError("Import_file is provided but not import_module.")
        # TODO: (Arnon) implement calling module
        imports = make_imports(import_file, import_module)
        if imports:
            self.imports.append(imports)

        try:
            step = self.__memory.steps[name]
        except Exception:
            pass
        else:
            mlogger.debug('add_step: already found in memory: skipping {}'.format(repr(step)))
            return step

        triggers = self.__convert_trigger_at_complete(triggers)
        recovery = self.__convert_recovery_at_complete(recovery)
        recovery = MergedChainedDict(recovery, Eventor.recovery_defaults)
        recovery =\
            dict([(step_to_task_status(status), replay) for status, replay in recovery.items()])

        config = MergedChainedDict(config, self.__config, os.environ,)
        # try to see if provided host is mapped in configuration
        host = host if self.hosts.get(host, host) is not None else self.host
        step = Step(name=name, func=func, func_args=args, func_kwargs=kwargs, host=host,
                    acquires=acquires, releases=releases, config=config, triggers=triggers,
                    recovery=recovery, logger=mlogger)
        found = self.__memory.steps.get(step.id_)
        if found is not None:
            raise EventorError("Step with similar name already defined: {}".format(step.id_))
        self.__memory.steps[step.id_] = step
        mlogger.debug('add_step: {}'.format(repr(step)))
        return step

    def __delay_func(self, sequence, recovery, activated=None, active=True, delay_id=None, seconds=None):
        ''' Inserts delay into Delay table to be picked up by delay_loop
        '''
        delay = self.db.add_delay_update_if_not_exists(delay_id=delay_id, sequence=sequence,
                                                       seconds=seconds, recovery=recovery,
                                                       active=active, activated=activated)
        mlogger.debug('add_delay_if_not_exists: {}'.format(repr(delay)))
        return True

    def __get_start_delay_task(self, delay_id, seconds,):
        ''' checks Delay table `
        '''
        def delay_func(sequence, recovery, activated=None, active=True):
            ''' Inserts delay into Delay table to be picked up by delay_loop
            '''
            delay = self.db.add_delay_update_if_not_exists(delay_id=delay_id, sequence=sequence,
                                                           seconds=seconds, recovery=recovery,
                                                           active=active, activated=activated)
            mlogger.debug('add_delay_if_not_exists: %s' % (repr(delay)))
            return True
        return delay_func

    def add_assoc(self, event, *assocs, delay=0):
        """add a assoc to Eventor object

        Associates event with one or more objects of steps and events.

        When delay is provided, Eventor will activated assocs only after delay
        seconds passed after event was triggered.

        Delay supports ':memory:' store only if Eventor is called with negative
        max_loops (default). Otherwise, the information pertaining the delay
        may not be maintained.

        Args:
            event: an event object return from add_event()
            assocs: list of either step or event objects returned from add_step()
                or add_event() respectively
            delay: seconds to wait before activating assocs once event had been triggered.

        returns:
            N/A

        raises:
            EnventorError: if event is not of event type or obj is not instance of Event or Step
        """
        self.__program_artifacts.assocs.append((event, assocs, delay))

        if delay > 0:
            # since we have to delay, we need to create a Delay hidden task in
            # between event and assocs.
            delay_id = "_evr_delay_{}_{}".format(event.name, get_delay_id())
            delay_event = self.add_event(delay_id)
            delay_step = self.add_step(delay_id, func=None,)
            self.add_assoc(event, delay_step)
            self.add_assoc(delay_event, *assocs)
            mlogger.debug("Adding delayed assoc:\n    {}: {}.\n    {}: {}."
                          .format(event, delay_step, delay_event, repr(assocs)))
            self.__memory.delays[delay_id] = Delay(delay_id=delay_id, func=None, seconds=delay,
                                                   event=delay_event)

        else:
            try:
                objs = self.__memory.assocs[event.id_]
            except KeyError:
                objs = list()
                self.__memory.assocs[event.id_] = objs

            for obj in assocs:
                assoc = Assoc(event, obj)
                objs.append(assoc)
                mlogger.debug('add_assoc: {}'.format(repr(assoc)))

    def trigger_event(self, event, sequence=0, db=None):
        """Activates event

            Activate event by registering it in trigger table.

            If Sequence is provided, it will be used as trigger sequence for this event.
            This is done to allow multiple triggers for the same event.

            If sequence is not provided, one will assigned to this trigger.

            Sequence creates association with derived steps or events associated with
            the event triggered.

            Args:
                event: (Event) object returned from add_event()
                sequence: (str) object uniquely identifying this trigger among other triggers of
                the same event

            Returns:
                N/A

            Raises:
                EventorError

        """

        if not db:
            db = self.db
        try:
            added = event.trigger_if_not_exists(db=db, sequence=sequence, recovery=self.__recovery)
        except Exception as e:
            mlogger.critical("Failed to trigger event: {}({}); run_id: {}."
                             .format(event.name, sequence, self.run_id))
            mlogger.exception(e)
            added = False
        return added

    def remote_trigger_event(self, event, sequence=0,):
        trigger_request = TriggerRequest(type='event', value=(event, sequence))
        self.__requestq.put(trigger_request)

    def trigger_step(self, step, sequence):
        """Activates step

            Activate step by registering it in task table are 'ready'.  Task loop will pick it up
            for processing.

            Args:
                step: (Step) object returned from add_step()
                sequence: (str) object uniquely identifying this trigger among other triggers of
                the same event

            Returns:
                N/A

            Raises:
                EventorError

        """

        task = step.trigger_if_not_exists(self.db, sequence, status=TaskStatus.ready,
                                          recovery=self.__recovery)
        if task:
            self.__triggers_at_task_change(task)
        return task is not None

    def __loop_trigger_request(self):
        ''' Loop trigger table for triggers not acted upon.
        '''

        # loop continuously until queue is empty.
        result = False
        while True:
            try:
                request = self.__requestq.get_nowait()
            except queue.Empty:
                return result
            if request.type == 'event':
                event, sequence = request.value
                self.trigger_event(event, sequence)
                mlogger.debug('[ Event {}/{} ] Triggering event'.format(event.id_, sequence))
                result = True

    def __assoc_loop(self, event, sequence):
        ''' Fetches event associations and trigger them.

        If association is an event:
            trigger the event

        If association is a step:
            register task
            trigger event - task running.

        '''
        assoc_events = list()
        assoc_steps = list()
        try:
            assocs = self.__memory.assocs[event.id_]
        except KeyError:
            assocs = []

        for assoc in assocs:
            assoc_obj = assoc.assoc_obj
            if isinstance(assoc_obj, Event):
                # trigger event
                mlogger.debug('[ Event {}/{} ] Processing event association to event: {}.'
                              .format(event.id_, sequence, repr(assoc_obj)))
                self.trigger_event(assoc_obj, sequence)
                assoc_events.append(sequence)
            elif isinstance(assoc_obj, Step):
                # Check if there is previous task for this step
                mlogger.debug('[ Event {}/{} ] Processing event association to'
                              ' step: {}.'
                              .format(event.id_, sequence, repr(assoc_obj)))
                self.trigger_step(assoc_obj, sequence)
                assoc_steps.append(sequence)

            else:
                msg = ("[ Event {}/{} ] Unknown assoc object in association:"
                       " {}."
                       .format(event.id_, sequence, repr(assoc)))
                mlogger.debug(msg)
                raise EventorError(msg)

        return list(set(assoc_events)), list(set(assoc_steps))

    def __loop_event(self):
        loop_seq = Sequence('EventLoop')
        self.loop_id = loop_seq()
        mlogger.debug("Going to fetch events: {}: recovery: {}"
                      .format(self.name, self.__recovery, ))
        # first pick up requests and move to act
        # this step is needed so automated requests will not impact
        # the process as it is processing.
        # requests not picked up in current loop, will be picked by the next.
        triggers = self.db.get_trigger_iter(recovery=self.__recovery)
        trigger_db = dict()

        event_seqs = list()
        step_seqs = list()

        # need to rearrange per iteration
        for trigger in triggers:
            try:
                trigger_map = trigger_db[trigger.sequence]
            except KeyError:
                trigger_map = dict()
                trigger_db[trigger.sequence] = trigger_map

            # print('trigger %s[%s]' % (trigger.event_id, trigger.iteration) )
            trigger_map[trigger.event_id] = True

            if not trigger.acted:
                assoc_events, assoc_steps = \
                    self.__assoc_loop(self.__memory.events[trigger.event_id],
                                      trigger.sequence)
                event_seqs.extend(assoc_events)
                step_seqs.extend(assoc_steps)
                self.db.acted_trigger(trigger)

        for sequence, trigger_map in trigger_db.items():
            for event in self.__memory.events.values():
                if not event.expr:
                    continue

                try:
                    result = eval(event.expr, globals(), trigger_map)
                except Exception:
                    result = False

                mlogger.debug("[ Event {}/{} ] Eval expr: {} = {}\n    {}"
                              .format(event.id_, sequence, event.expr, result,
                                      trigger_map))

                if result:  # and self.act:
                    # TODO: do we need to raise event.
                    added = self.trigger_event(event, sequence,)
                    if added:
                        mlogger.debug('[ Event %s/%s] Triggered event (%s ):\n'
                                      '    {}' % (event.id_, sequence,
                                                  repr(event)))
                        event_seqs.append(sequence)

        return list(set(event_seqs)), list(set(step_seqs))

    def __log_error(self, task, stop_on_exception):
        logutil = mlogger.error if stop_on_exception else mlogger.warning
        err_exception, pickle_trace = task.result
        err_trace = pickle.loads(pickle_trace)

        logutil('Exception in run_action: \n    {}'.format(task,))
        logutil("%s" % (repr(err_exception), ))
        trace = '\n'.join([line.rstrip() for line in err_trace])
        if trace:
            logutil("%s" % (trace, ))

    def __apply_task_result(self, task):
        # Before task state is updated in DB, triggers are evaluated.
        # This is so in distributed operation, when task is handled by agent,
        # master will continue to find work TODO.
        # Otherwise, there may be a gap between task set to success and trigger
        # added as a result.
        # if nested catches this gap, it will see no work to do and abort its
        # loops.
        if task.status in [TaskStatus.success, TaskStatus.failure]:
            self.__release_task_resources(task)
        triggered = self.__triggers_at_task_change(task)
        mlogger.debug('[ Task {}/{} ] applying task update to db\n    {}'
                      .format(task.step_id, task.sequence, repr(task), ))
        try:
            self.db.update_task(task=task)
        except Exception as e:
            mlogger.critical("[ Task {}/{} ] Failed to update task; run_id: {}"
                             .format(task.step_id, task.sequence, task.run_id))
            mlogger.exception(e)
            self.__state = EventorState.shutdown
            return []
        '''
        if task.status in [TaskStatus.success, TaskStatus.failure]:
            self.__release_task_resources(task)
        triggered = self.__triggers_at_task_change(task)
        '''
        return triggered

    def __play_result(self, act_result,):
        mlogger.debug('Result collected: \n    {}'.format(repr(act_result)))
        stop_on_exception = self.__config['stop_on_exception']

        result = True
        istask = isinstance(act_result.value, Task)
        mlogger.debug('Received {}({}) to play (istask: {})'
                      .format(type(act_result.value).__name__,
                              repr(act_result.value), istask))
        if istask:
            task = act_result.value
            if act_result.msg_type == TaskAdminMsgType.result:
                delay_task = task.step_id.startswith('_evr_delay_')
                if not delay_task:
                    try:
                        proc = self.__task_proc[task.id_]
                    except KeyError:
                        mlogger.debug('[ Task {}/{} ] Failed to get task id {}'
                                      ' from task_proc table (keys: {})'
                                      .format(task.step_id, task.sequence,
                                              task.id_,
                                              list(self.__task_proc.keys())))
                        raise
                    mlogger.debug('[ Task {}/{} ] applying result, process:'
                                  ' {}, is_allive: {}.'
                                  .format(task.step_id,
                                          task.sequence,
                                          repr(proc), proc.is_alive()))

                    if not isinstance(proc, Invoke):
                        exitcode = ""
                        if hasattr(proc, exitcode):
                            exitcode = " (exitcode=%s)" % proc.exitcode
                        mlogger.debug('[ Task {}/{} ] Joining exit code: {}.'
                                      .format(task.step_id, task.sequence,
                                              exitcode))
                        while proc.is_alive():
                            proc.join(0.05)
                        mlogger.debug('[ Task {}/{} ] Joined.'
                                      .format(task.step_id, task.sequence,))
                    # TODO: (Arnon) find why delete causing issue with Example 180
                step = self.__memory.steps[task.step_id]
                step.concurrent -= 1
                triggered = self.__apply_task_result(task)
                mlogger.debug('[ Task {}/{} ] triggered: {}, stop_on_exception: {},'
                              ' task.status: {}'
                              .format(task.step_id, task.sequence, repr(triggered),
                                      repr(stop_on_exception), repr(task.status)))
                shutdown = (len(triggered) == 0 or stop_on_exception) and\
                    task.status == TaskStatus.failure
                mlogger.debug('[ Task {}/{} ] shutdown: {}'
                              .format(task.step_id, task.sequence, shutdown))
                if task.status == TaskStatus.failure:
                    self.__log_error(task, shutdown)
                    if len(triggered) == 0:
                        self.__state = EventorState.shutdown

                # if shutdown:
                #    mlogger.info("Stopping running processes")

                    result = False
            elif act_result.msg_type == TaskAdminMsgType.update:
                try:
                    self.db.update_task(task=task)
                except Exception as e:
                    mlogger.critical("[ Task {}/{} ] Failed to update task; run_id: {}."
                                     .format(task.step_id, task.sequence, task.run_id))
                    mlogger.exception(e)
                    self.__state = EventorState.shutdown
                    result = False
                # TODO: stop running processes
        else:
            # TODO: need to deal with action
            mlogger.debug('Skip play result; act_result value type not matched: {}.'
                          .format(repr(type(act_result.value))))

        return result

    def __collect_results(self,):
        ''' Collect results from task wrapper queues.

        There are two queues for the different types of process constructs.
        multiprocess.Process: adminq_mp
        threading.Thread and Invoke: adminq_th
        '''

        iterate_mp = iterate_th = iterate_in = True
        result_mp = result_th = result_in = False
        while iterate_mp or iterate_th or iterate_in:
            mlogger.debug('Trying to read result queue')

            try:
                act_result = self.__adminq_mp.get_nowait()
            except queue.Empty:
                act_result = None
                iterate_mp = False
                result_mp = False
            else:
                mlogger.debug("Going to play Process result: {}".format(repr(act_result)))
                result_mp = self.__play_result(act_result)

            try:
                act_result = self.__adminq_th.get_nowait()
            except queue.Empty:
                act_result = None
                iterate_th = False
                result_th = False
            else:
                mlogger.debug("Going to play Thread result: {}".format(repr(act_result)))
                result_th = self.__play_result(act_result)

            try:
                act_result = self.__adminq_in.get_nowait()
            except queue.Empty:
                act_result = None
                iterate_in = False
                result_in = False
            else:
                mlogger.debug("Going to play Invoke result: {}".format(repr(act_result)))
                result_in = self.__play_result(act_result)

        # TODO: (Arnon) Validate that Th and Pr needs to be combined without Invoke
        result = result_mp or result_th
        mlogger.debug('Collected and played result: {}, thread: {}, process: {}, invoke: {}'
                      .format(result, result_th, result_mp, result_in))

        return result

    def __triggers_at_task_change(self, task):
        step = self.__memory.steps[task.step_id]
        status = task_to_step_status(task.status)
        triggers = step.triggers.get(status, [])
        mlogger.debug("[ Task {}/{} ] Found triggers for task status {}: {}"
                      .format(task.step_id, task.sequence, status, repr(triggers)))
        triggered = list()
        for event in triggers:
            result = event.trigger_if_not_exists(self.db, task.sequence, self.__recovery)
            if result:
                triggered.append((event.id_, task.sequence))
                mlogger.debug("[ Task {}/{} ] Triggered post task: {}/{}"
                              .format(task.step_id, task.sequence, repr(event.id_), task.sequence))

        return triggered

    def __get_admin_queue(self, task_construct):
        if task_construct == 'process':  # mp.Process:
            result = self.__adminq_mp
        elif task_construct == 'thread':
            result = self.__adminq_th
        else:  # invoke
            result = self.__adminq_in
        return result

    def __initiate_delay(self, task, previous_task=None):
        ''' Runs delay function associated with task to register delay in delay table
        '''
        delay = self.__memory.delays[task.step_id]
        mlogger.debug("Initiating delay: {} (previous = {})"
                      .format(delay.delay_id, repr(previous_task)))
        active = True
        activated = datetime.utcnow()

        if previous_task is not None:
            prev_delay = self.__previous_delays[task.sequence][task.step_id]
            # in recovery, we continue with when delay was registered
            # we set it as active regardless to its previous state.
            # this will cause delay_loop to pick i up.
            active = True  # prev_delay.active
            activated = prev_delay.activated
            mlogger.debug("Fetched delay from previous: active: {}, activated: {}"
                          .format(active, activated))

        try:
            result = self.__delay_func(activated=activated, active=active, sequence=task.sequence,
                                       recovery=task.recovery, delay_id=delay.delay_id,
                                       seconds=delay.seconds)
        except Exception as e:
            task.status = TaskStatus.failure
            mlogger.critical('Exception in task execution: \n    {}'.format(task,))
            mlogger.exception(e)
            mlogger.info("Stopping running processes")
            self.__state = EventorState.shutdown

        if result:
            task.status = TaskStatus.success

        result = TaskAdminMsg(msg_type=TaskAdminMsgType.result, value=task)
        adminq = self.__adminq_th
        adminq.put(result)

    def __validate_process_kwargs(self, kwds, task):
        result = True
        for name, value in kwds.items():
            try:
                pickle.dumps(value)
            except Exception as e:
                mlogger.critical("Cannot pickle kwarg {} of type {}, "
                                 "object name: {}."
                                 .format(name, type(value).__name__,
                                         getattr(value, 'name', 'N/A')))
                mlogger.exception(e)
                if hasattr(value, '__dict__'):
                    for subname, subvalue in value.__dict__.items():
                        try:
                            pickle.dumps(subvalue)
                        except Exception as sube:
                            mlogger.critical("Cannot pickle name {} of type {}."
                                             .format(subname,
                                                     type(subvalue).__name__))
                            mlogger.exception(sube)
                            break
                self.__get_dbapi(create=False)
                self.__update_task_status(task, TaskStatus.failure)
                # TODO: (Arnon) if there are already processes running, finish will
                #  fail since it is not joining/killing those processes
                result = False

        return result

    def __initiate_task(self, task, previous_task=None):
        ''' Playing synchronous action.

        Algorithm:
            1. Set action state to active.
            2. Launch a thread to perform action (use thread pool).

        Args:
            task: (Task) task to run
            previous_task: (Task), will be populated if in recovery and an instance of task exists.
        '''
        step = self.__memory.steps[task.step_id]
        mlogger.debug("Initiating task: {}({})".format(task.id_, task.step_id))
        step_recovery = StepReplay.rerun
        if previous_task:
            step_recovery = step.recovery[previous_task.status]

        if step_recovery == StepReplay.rerun:
            # on rerun, act as before - just run the task

            max_concurrent = step.config['max_concurrent']
            task_construct = step.config['task_construct']
            adminq = self.__get_admin_queue(task_construct=task_construct)
            # TODO: add join when synchronous
            use_process = task_construct == 'process'  # mp.Process
            kwds = {'run_id': self.run_id,
                    'task': task,
                    'step': self.__memory.steps[task.step_id],
                    'adminq': adminq,
                    'use_process': use_process,
                    'logger_info': self.__logger_info,
                    'config': self.__config,
                    }
            if max_concurrent < 0 or step.concurrent < max_concurrent:  # no-limit
                try:
                    self.__update_task_status(task, TaskStatus.active)
                except Exception as e:
                    mlogger.critical("[ Task {}/{} ] Failed to update task; run_id: {}"
                                     .format(task.step_id, task.sequence, task.run_id))
                    mlogger.exception(e)
                    self.__state = EventorState.shutdown
                    return None
                triggered = self.__triggers_at_task_change(task)

                mlogger.debug('[ Task {}/{} ] Going to construct ({}) and run task:\n    {}'
                              .format(task.step_id, task.sequence, task_construct, repr(task),))

                # TODO: (Arnon) make configuration flag to pass Eventor on invoke.
                if task_construct == 'invoke':
                    # If Invoke, we also pass eventor to task.
                    # Since Invoke, contects remains in current process,
                    # Therefore task can use eventor to add events and tasks.
                    kwds['eventor'] = self

                # prepare to pickle
                if use_process:
                    self.db.close()
                    self.db = None
                    logger_ = self.__logger
                    self.__logger = None

                    # test pickle of kwargs to process
                    if __debug__:
                        pass_debug = self.__validate_process_kwargs(kwds, task)
                        if not pass_debug:
                            return
                    # end test of kwargs

                task_constructor = get_proc_constructor(task_construct)
                if task_constructor is None:
                    mlogger.critical('[ Task {}/{} ] Failed to get task constructor for {}'
                                     .format(task.step_id, task.sequence, task_construct,))
                    self.__state = EventorState.shutdown
                    task.status = TaskStatus.failure
                    if use_process:
                        self.__get_dbapi(create=False)
                    self.__update_task_status(task, TaskStatus.failure)
                    return

                try:
                    proc = task_constructor(target=task_wrapper, kwargs=kwds)
                except Exception as e:
                    mlogger.critical("[ Task {}/{} ] Failed to construct process using {}."
                                     .format(task.step_id, task.sequence, task_construct,))
                    mlogger.exception(e)
                    self.__state = EventorState.shutdown
                    task.status = TaskStatus.failure
                    if use_process:
                        self.__get_dbapi(create=False)
                    self.__update_task_status(task, TaskStatus.failure)
                    return

                if use_process:
                    proc_id = "{}-".format(self.run_id) if self.run_id else ''
                    proc.name = '{}Task-{}({})'.format(proc_id, step.name, task.sequence)
                step.concurrent += 1

                try:
                    proc.start()
                except Exception as e:
                    step.concurrent -= 1
                    if use_process:
                        self.__get_dbapi(create=False)
                    task.status = TaskStatus.failure
                    self.__update_task_status(task, TaskStatus.failure)
                    mlogger.critical('[ Task {}/{} ] Exception in task execution: \n    {}'
                                     .format(task.step_id, task.sequence, task,))
                    mlogger.exception(e)
                    mlogger.info("Stopping running processes.")
                    self.__state = EventorState.shutdown
                else:
                    mlogger.debug('[ Task {}/{} ] Started: \n    {}'
                                  .format(task.step_id, task.sequence, task,))
                    self.__task_proc[task.id_] = proc
                    if use_process:
                        self.__get_dbapi(create=False)
                finally:
                    if use_process:
                        self.__logger = logger_
            else:
                mlogger.debug('[ Task {}/{} ] Delaying run (max_concurrent: {}, concurrent: {})'
                              ' and run task:\n    {}.'
                              .format(task.step_id, task.sequence, max_concurrent, step.concurrent,
                                      repr(task),))
        else:
            # TODO: make sure htis works
            # on skip
            mlogger.debug('[ Step {}/{} ] Skipping task in recovery mode'
                          .format(task.step_id, task.sequence))
            task.status = TaskStatus.success
            triggered = self.__apply_task_result(task,)

        return triggered

    def __loop_awating_resource_allocation(self):
        while True:
            mlogger.debug("Trying to receive resources")
            try:
                task_id = self.__rp_notify.get_nowait()
            except queue.Empty:
                break

            memtask = self.__tasks.get(task_id, None)
            step = self.__memory.steps[memtask.step_id]
            mlogger.debug("Received resources for task {}.".format(step.name, ))

            memtask.resources = self.__requestors.get(memtask.request_id)
            self.__update_task_status(memtask, TaskStatus.fueled)

    def __update_task_status(self, task, status):
        self.db.update_task_status(task=task, status=status)

    def __release_task_resources(self, task):
        step = self.__memory.steps[task.step_id]
        mlogger.debug("Releasing task resources {}: {}.".format(step.name, step.releases))
        if step.releases is not None:
            self.__requestors.put_requested(step.releases)

    def __allocate_resources_for_task(self, task, previous_task=None):
        ''' Request resources for task.

        When satisfied, change status to .
        '''
        step = self.__memory.steps[task.step_id]

        memtask = self.__tasks.get(task.id_, None)
        if memtask is None:
            mlogger.debug("Initiating new memtask for resource allocation {}: {}."
                          .format(step.name, step.acquires, ))
            memtask = Memtask(task)
            self.__tasks[task.id_] = memtask
        # need to allocate resources from all requested pools.
        # requests uses callback as a method to request all resources
        # once all resources are collected, task is satisfied.

        # ResourceAllocationCallback(self.__resource_notification_queue)

        if not memtask.fueled:
            # not requested resources yet
            rp_callback = RpCallback(self.__rp_notify, task_id=task.id_)
            mlogger.debug("Going to reserve resources {}: {}.".format(step.name, step.acquires, ))
            memtask.request_id = self.__requestors.reserve(request=step.acquires,
                                                           callback=rp_callback)
            self.__update_task_status(memtask, TaskStatus.allocate)

    def __loop_task(self,):
        ''' evaluate ready tasks to initiate.

        loop_task will do its work only if eventor state is active.
        '''
        loop_seq = Sequence('_EventorTaskLoop')
        self.loop_id = loop_seq()

        # all items are pulled so active can also be monitored for timely end
        # There is no need to check status.
        # Loops will end if there is nothing to do.
        # if self.__state==EventorState.active:

        # there are two routes.  One for server. The other is agent
        # agent takes only tasks for their hosts.
        mlogger.debug("Going to fetch tasks: {}: recovery: {}.".format(self.name, self.__recovery))
        query_host = self.host if not self.__is_server else None
        tasks = self.db.get_task_iter(host=query_host, recovery=self.__recovery,
                                      status=[TaskStatus.ready, TaskStatus.allocate,
                                              TaskStatus.fueled, TaskStatus.active])
        for task in tasks:
            step = self.__memory.steps[task.step_id]
            try:
                previous_task = self.__previous_tasks[task.sequence][task.step_id]
            except (KeyError, TypeError):
                previous_task = None

            mlogger.debug("Evaluating task: {}, step: {}".format(repr(task), repr(step)))
            ready_to_launch = task.status == TaskStatus.fueled or\
                (task.status == TaskStatus.ready and not step.acquires)
            launch_here = self.host == task.host
            task_is_a_delay = task.step_id.startswith('_evr_delay_')
            if self.__is_server:
                if ready_to_launch:
                    if not task_is_a_delay:
                        if launch_here:
                            mlogger.debug("No delay, initiate task: {}.".format(task.id_, ))
                            self.__initiate_task(task, previous_task)
                    else:
                        mlogger.debug("Delayed task, initiate delay for task: {}."
                                      .format(task.id_))
                        self.__initiate_delay(task, previous_task)
                elif task.status == TaskStatus.ready:
                    # task.status == TaskStatus.ready and has resources to satisfy
                    mlogger.debug("Ready task need to be fueled: {}.".format(task.id_, ))
                    self.__allocate_resources_for_task(task, previous_task)
                elif TaskStatus.allocate:
                    # TODO: check if expired - if so, halt
                    mlogger.debug("Task allocated resource: {}.".format(task.id_, ))
                else:  # active
                    # TODO: check run time allowance passed - if so, halt
                    pass
            else:  # task is agent
                if not task_is_a_delay:
                    mlogger.debug("No delay, initiate task: {}.".format(task.id_, ))
                    self.__initiate_task(task, previous_task)

        result = self.__collect_results()

        return result

    def __process_delay(self, db_delay):
        ''' checks Delay table
        '''
        try:
            delay = self.__memory.delays[db_delay.delay_id]
        except Exception:
            mlogger.error("Delay {} not found in Delays: {}."
                          .format(db_delay.delay_id, repr(list(self.__memory.delays.keys()))))
            raise
        event = delay.event
        mlogger.debug("Triggering delayed event: {}({})".format(db_delay.delay_id, repr(event)))
        self.trigger_event(event=event, sequence=db_delay.sequence,)

    def __loop_delay(self,):
        ''' evaluate delays; act when matured.

        loop_delay will scan active delays.  When mature, raise its associated event.
        '''
        loop_seq = Sequence('_EventorDelayLoop')
        self.loop_id = loop_seq()

        count = 0
        # all items are pulled so active can also be monitored for timely end
        mlogger.debug("Going to fetch delays: {}: recovery: {}."
                      .format(self.name, self.__recovery))
        delays = self.db.get_delay_iter(recovery=self.__recovery,)
        now = datetime.utcnow()

        for delay in delays:
            if not delay.active:
                continue
            age = (now-delay.activated).total_seconds()
            mlogger.debug("Delay age: {} = {}.".format(delay.delay_id, age))
            if age >= delay.seconds:
                # delay is done, raise proper event.
                self.__process_delay(delay)
                self.db.deactivate_delay(delay)
            else:
                count += 1

        mlogger.debug("Count of active delays: {}".format(count,))
        return count

    def loop_once(self, ):
        ''' run single iteration over triggers to see if other events and
        associations needs to be launched.

        loop event: to see if new triggers matured
        loop task: to see if there is anything to run
        '''
        result_loop_trigger = False

        if self.__is_server:
            self.__loop_delay()
            self.__loop_event()
        result_loop_task = self.__loop_task()
        if self.__is_server:
            result_loop_trigger = self.__loop_trigger_request()
        self.__loop_awating_resource_allocation()

        mlogger.debug("Loop once result tasks: {}, triggers {}"
                      .format(result_loop_task, result_loop_trigger,))
        return result_loop_task + result_loop_trigger

    def __check_control(self):
        loop = True
        if not self.__controlq.empty():
            msg = self.__controlq.get()
            if msg:
                loop = msg not in [LoopControl.stop]
        return loop

    def count_todos(self, sequence=None, with_delayeds=True):
        stop_on_exception = self.__config['stop_on_exception']
        mlogger.debug('[ Step {} ] Counting TODOs; state: {}, recovery: {}.'
                      .format(self._name(sequence), self.__state, self.__recovery))
        todo_triggers = 0
        task_to_count = [TaskStatus.active, TaskStatus.fueled,
                         TaskStatus.allocate, TaskStatus.ready]

        # count triggers
        if self.__state == EventorState.active or not stop_on_exception:
            todo_triggers = self.db.count_trigger_ready(sequence=sequence,
                                                        recovery=self.__recovery)
        else:
            task_to_count = [TaskStatus.active, ]

        # count tasks
        try:
            active_and_todo_tasks = self.db.count_tasks(status=task_to_count,
                                                        sequence=sequence,
                                                        recovery=self.__recovery)
        except Exception as e:
            mlogger.critical("[ Step {} ] Failed to count TODOs in count_todos(); run_id: {}."
                             .format(self._name(sequence), self.run_id))
            mlogger.exception(e)
            self.__state = EventorState.shutdown
            return 0
        total_todo = todo_triggers + active_and_todo_tasks
        result = total_todo
        active_delays = 0
        # count delay:
        if with_delayeds:
            active_delays, min_delay = self.db.count_active_delays(sequence=sequence,
                                                                   recovery=self.__recovery)
            total_todo += active_delays
            result = (total_todo, min_delay)

        mlogger.debug('[ Step {} ] Total TODOs: {} (triggers: {}, tasks: {}, delays: {})'
                      .format(self._name(sequence), total_todo, todo_triggers,
                              active_and_todo_tasks, active_delays))

        return result

    def count_todos_like(self, sequence):
        ''' Counts items that are about to be in process, or in process.

        Args:
            sequence: (str) the sequence prefix to search for

        Returns:
            Count of in process
        '''
        stop_on_exception = self.__config['stop_on_exception']

        mlogger.debug('[ Step {} ] Counting TODOs like: {}; state: {}, recovery: {}'
                      .format(self._name(sequence), sequence, self.__state, self.__recovery))
        todo_triggers = 0
        task_to_count = [TaskStatus.active, TaskStatus.fueled,
                         TaskStatus.allocate, TaskStatus.ready]
        # If step (mega-step) is active, needs to add triggers ready.
        # else, we need to take only those tasks that are active.
        if self.__state == EventorState.active or not stop_on_exception:
            todo_triggers = self.db.count_trigger_ready_like(sequence=sequence,
                                                             recovery=self.__recovery)
        else:
            # since step is not active, we are interested only with active steps
            # with in this mega-step.
            task_to_count = [TaskStatus.active]

        active_and_todo_tasks = self.db.count_tasks_like(status=task_to_count, sequence=sequence,
                                                         recovery=self.__recovery)
        active_delays, min_delay = self.db.count_active_delays(sequence=sequence,
                                                               recovery=self.__recovery)
        total_todo = todo_triggers + active_and_todo_tasks + active_delays
        mlogger.debug('[ Step {} ] Total TODOs: {} (triggers: {}, tasks: {})'
                      .format(self._name(sequence), total_todo, todo_triggers,
                              active_and_todo_tasks))

        return (total_todo, min_delay)

    def loop_cycle(self,):
        ''' loops until there is no triggers or tasks. If there are active delays,
        they will be left for next cycle.

        Each loop is consist from:
            1. one processing log,
            2. check if there is still work to do,
            3. sleep give CPU a break
            4. check if forced to stop

        '''
        mlogger.debug('Starting loop cycle')
        sleep_loop = self.__config['sleep_between_loops']
        loop = True
        self.db.set_thread_synchronization(True)

        while loop:
            result = self.loop_once()
            # count ready triggers only if state is active
            # count ready tasks only if active
            total_todo = self.count_todos(with_delayeds=False)
            work = total_todo > 0 or result
            loop = (work or not self.__is_server) and not self.__term and self.__agent_loop
            if loop:
                loop = self.__check_control()
                if loop:
                    time.sleep(sleep_loop)
                    loop = self.__check_control()
                if not loop and not self._session_cycle_loop:
                    mlogger.info('Processing stopped')
            else:
                pass

        return result

    def loop_session(self):
        ''' loops until there is no work to do

        Each loop is consist from:
            1. one processing log,
            2. check if there is still work to do,
            3. sleep give CPU a break
            4. check if forced to stop

        '''
        mlogger.debug('Starting loop session')
        sleep_loop = self.__config['sleep_between_loops']
        loop = True
        self.db.set_thread_synchronization(True)
        self._session_cycle_loop = True

        while loop:
            result = self.loop_cycle()
            # count ready triggers only if state is active
            # count ready tasks only if active
            total_todo, min_delay = self.count_todos()
            work = total_todo > 0 or result
            loop = (work or not self.__is_server) and not self.__term and self.__agent_loop
            if loop:
                loop = self.__check_control()
                if loop:
                    # min_delay may be negative in recovery mode.
                    min_delay = max(0, min_delay)
                    sleep_time = sleep_loop if min_delay is None else min_delay
                    if sleep_loop != sleep_time:
                        mlogger.debug('Making a time delay sleep: {}'.format(sleep_time))
                    time.sleep(sleep_time)  # time.sleep(sleep_loop)
                    loop = self.__check_control()

        result = self.__state != EventorState.shutdown
        finished = 'finished' if not self.__term else 'terminated'
        human_result = "incomplete" if total_todo > 0 else "success" if result else 'failure'
        mlogger.info('Processing {} with: {}'.format(finished, human_result))

        return result

    def loop_session_stop(self):
        self.__controlq.put(LoopControl.stop)

    def get_step_sequence(self):
        result = os.environ.get('EVENTOR_STEP_SEQUENCE', '')
        return result

    def get_step_name(self):
        result = os.environ.get('EVENTOR_STEP_NAME', '')
        return result

    def get_task_status(self, task_names, sequence,):
        result = {}
        try:
            result = self.db.get_task_status(task_names=task_names, sequence=sequence,
                                             recovery=self.__recovery, host=self.host)
        except Exception as e:
            mlogger.critical("Failed to get task status in get_task_status(); run_id: {}."
                             .format(self.run_id))
            mlogger.exception(e)
            self.__state = EventorState.shutdown
        return result

    def __logger_process_lambda(self,):
        logger_info = deepcopy(self.__logger_info)

        def internal(name=None):
            if name is not None:
                logger_info['name'] = name
            logger = Logger.get_logger(logger_info)
            return logger
        return internal

    def __start_agent(self, host, mem_pack, parentq):
        ''' start agent in remote host using ssh.

        Args:
            host: address of remote host
            mem_pack: pickled message to send to remote host
            parentq: to send back problems by child process
        '''

        kwargs = list()
        for imports in self.imports:
            kwargs.append(("--imports", imports))

        kwargs.extend([('--host', host),
                       ('--ssh-server-host', self.ssh_host),
                       ('--log-info', '"{}"'.format(yaml.dump(self.__logger_info))),
                       ])
        if self.debug:
            work = self.__config['workdir']
            file = "{}{}.dat".format(self.__logger_info['name'], "_{}"
                                     .format(self.run_id) if self.run_id else '')
            work_file = os.path.join(work, file)
            kwargs.append(('--file', work_file))

        args = ['--pipe']
        if self.debug:
            args.append('--debug')
        kw = reduce(lambda x, y: x + list(y), kwargs, list())
        # kw = ["{} {}".format(name, value) for name, value in kwargs]
        # cmd = "{} act {} {}".format(agentpy, ' '.join(args), " ".join(kw))
        # cmd = [agentpy, "act", ' '.join(args), " ".join(kw)]
        cmd = ['eventor_agent.py', "act"] + args + kw
        mlogger.debug('Agent command: {}: {}.'.format(host, cmd))
        sshname = "{}.sshagent.log".format(self.__logger_params['name'])

        try:
            sshagent = sp.SSHTunnel(host, cmd, name=sshname, logger=mlogger)
            sshagent.start(wait=0.2)
        except Exception as e:
            mlogger.exception(e)
            response = sshagent.response()
            mlogger.critical("EventorAgent failed to start: {}; response: {}."
                             .format(host, response))
            return None

        mlogger.debug('Agent process started: {}:{}.'.format(host, sshagent.pid()))
        if not sshagent.is_alive():
            response = sshagent.response()
            mlogger.critical('Agent process terminated unexpectedly: {}; response: {}'
                             .format(host, response))
            sshagent.join()
            return None
        # this is parent
        try:
            sshagent.send(mem_pack, pack=False,)
        except Exception as e:
            mlogger.error("Failed to send workload to {}.".format(host))
            mlogger.exception(e)
            return None
        mlogger.debug('Sent workload to: {}.'.format(host,))
        if not sshagent.is_alive():
            mlogger.critical('Agent process terminated after send: {}.'.format(host,))
            return None
        mlogger.debug('Agent process checked okay: {}.'.format(host,))
        return sshagent  # RemoteAgent(proc=agent, stdin=pipe_write, stdout=None)

    def __get_ssh_hostname(self, host, ssh_config):
        try:
            ssh_hostname = ssh_config.get(host, 'Hostname',)
        except Exception:
            return None

        if ssh_hostname is not None:
            return ssh_hostname
        ssh_host = ssh_config.get('default', {})
        ssh_hostname = ssh_host.get('Hostname', host)
        return ssh_hostname

    def __get_ssh_config_file(self):
        ssh_config_file = self.__config.get('ssh_config', None)
        if ssh_config_file is not None:
            if os.path.isfile(ssh_config_file):
                return ssh_config_file
            else:
                raise EventorError("SSH configuration file {} not found.".format(ssh_config_file))
        else:
            default_ssh_config = os.path.expanduser("~/.ssh/config")
            if os.path.isfile(default_ssh_config):
                return default_ssh_config
        return None

    def __check_remote_hosts(self, hosts):
        ssh_config_file = self.__get_ssh_config_file()
        ssh_config = {}
        if ssh_config_file is not None:
            ssh_config = sp.load()
            mlogger.debug("Using SSH configuration file {}.".format(ssh_config_file,))

        not_accessiable = list()
        # check ssh port is accessible
        for host in hosts:
            hostname = self.__get_ssh_hostname(host, ssh_config)
            mlogger.debug("Checking access to host: {}, hostname: {}.".format(host, hostname))
            accessiable = port_is_open(hostname, self.ssh_port)
            if not accessiable:
                not_accessiable.append(host)
        if len(not_accessiable) > 0:
            msg = "SSH port is closed: {}.".format(", ".join(not_accessiable))
            mlogger.critical(msg)
            raise EventorError(msg)

    def __listent_to_remote(self, parentq, wait=0.25):
        agent_count = len(self.__agents)
        mlogger.debug('Listening to agents: {}.'.format(repr(self.__agents)))
        while agent_count > 0:
            for host, agent in list(self.__agents.items()):
                if not agent.is_alive():
                    agent.close()
                    response = agent.response()
                    returncode, stdout, stderr = response
                    stderr = '' if not stderr else '\n'+stderr

                    if stdout == 'DONE':
                        mlogger.debug('Agent finished {}.'.format(repr(response)))
                    elif stdout == 'TERM':
                        mlogger.critical('Agent terminated. Returncode: {}; Error: {}'
                                         .format(repr(returncode,), stderr))
                        self.__state = EventorState.shutdown
                    elif returncode > 0:
                        # finished for unknown reason
                        mlogger.critical('Agent aborted. Returncode: {}; Output: {}; Error: {}'
                                         .format(repr(returncode), stdout, stderr))
                        self.__state = EventorState.shutdown
                    else:
                        # finished for unknown reason
                        mlogger.debug('Agent exited. Returncode: {}; Output: {}; Error: {}'
                                      .format(repr(returncode), stdout, stderr))
                    del self.__agents[host]

            agent_count = len(self.__agents)
            if agent_count > 0:
                time.sleep(wait)

    def __term_agents(self, msg, join=True):
        mlogger.debug('Sending {} to agents: {}.'.format(msg, ", ".join(self.__agents.keys())))
        for host, agent in list(self.__agents.items()):
            mlogger.debug('Sending {} to {}'.format(msg, host,))
            try:
                response = agent.close(msg)
            except Exception as e:
                mlogger.error('Failed to sent {} to {}'.format(msg, host,))
                mlogger.exception(e)
            else:
                mlogger.debug('SSH agent terminated {}; {}'.format(host, response))

    def __exit_gracefully(self, signum=None, frame=None):
        mlogger.debug('Caught termination signal; terminating {}'
                      .format(", ".join(self.__agents.keys())))
        self.__term_agents('TERM')

    def __start_remote_agents(self, hosts):
        # prepare to pickle
        self.db.close()
        self.db = None
        logger_ = self.__logger
        self.__logger = None

        self.__agents = dict()

        signal.signal(signal.SIGHUP, self.__exit_gracefully)
        signal.signal(signal.SIGINT, self.__exit_gracefully)
        signal.signal(signal.SIGTERM, self.__exit_gracefully)

        mem_pack = pickle.dumps(self.__memory)

        # restore after pickle
        self.__logger = logger_

        self.__check_remote_hosts(hosts)

        parentq = mp.Queue()

        for host in hosts:
            agent = self.__start_agent(host, mem_pack, parentq)
            if agent is not None:
                self.__agents[host] = agent

        parentq_listner = Thread(target=self.__listent_to_remote, args=(parentq,), daemon=True)
        parentq_listner.start()

        started = True
        if len(self.__agents) < len(hosts):
            # not all agents came up; send TERM to rest
            # TODO: (Arnon) Need to build test case for partial failure to start remote agents
            for agent in list(self.__agents):
                if agent.is_alive():  # still alive!
                    agent.send("TERM", pickle_msg=True,)

            started = False

        self.__get_dbapi(create=False)

        return started

    def __listener_to_parent(self, listener_q):
        while True:
            msg = listener_q.get()
            if not msg:
                continue
            mlogger.debug('Received msg on listener_q: {}'.format(msg))
            if msg in ['STOP', 'FINISH']:
                self.__agent_loop = False
                break

    def run(self,  max_loops=-1):
        ''' loops events structures to execute raise events and execute tasks.

        Run, do two things:
        1. if prime (not agent): start agent on all remote hosts (seek from Steps.)
        2. run local loops.

        Args:
            max_loops: number of loops to run.  If positive, limits number of loops.
                 defaults to negative, which would run loops until there are no events to raise and
                 no task to run.

        '''
        # TODO: (Arnon) remote the use of __term; use self.__state = EventorState.shutdown instead
        self.__term = False
        self.__agent_loop = True
        if setproctitle is not None:
            run_id = "{}.".format(self.run_id) if self.run_id else ''
            setproctitle("eventor: {}".format(run_id,))

        self.__agents = dict()
        if self.__is_server:
            # start agents, if this is not already one
            self.remotes = list(set(self.remotes) - set([self.host]))
            hosts = set([step.host for step in self.__memory.steps.values()] + self.remotes)
            hosts.remove(self.host)

            # we dont need to pass remotes to agents
            self.__memory.kwargs['remotes'] = None

            mlogger.debug('Remote hosts in program: {}; hidden remotes: {}.'
                          .format(hosts, self.remotes))
            if len(hosts) > 0:
                # start_remote_agents will fill __agents dict.
                started = self.__start_remote_agents(hosts)
                if not started:
                    mlogger.critical('Processing terminated due to failure to start agents.')
                    return False

        if self.__listener_q is not None:
            # need to start listener for termination
            listener_th = Thread(target=self.__listener_to_parent, args=(self.__listener_q,),
                                 daemon=True)
            listener_th.start()
        else:
            listener_th = None

        self.__controlq = mp.Queue()
        self.__adminq_mp_manager = mp_manager = mp.Manager()
        self.__adminq_mp = mp_manager.Queue()
        self.__adminq_th = queue.Queue()
        self.__adminq_in = queue.Queue()
        self.__requestors = vrp.Requestors()
        self.__rp_notify = queue.Queue()
        self.__requestq = queue.Queue()

        if max_loops < 0:
            result = self.loop_session()
        else:
            result = None
            for _ in range(max_loops):
                # mlogger.debug('Starting loop cycle')
                result = self.loop_cycle()
            human_result = "success" if result else 'failure'
            total_todo, _ = self.count_todos(with_delayeds=True)
            mlogger.info('Processing finished with: {} (outstanding tasks: {})'
                         .format(human_result, total_todo))

        # wait for agents, if this is not already one
        if self.__is_server:
            for host, agent in list(self.__agents.items()):
                msg = 'FINISH'
                mlogger.debug('Sending {} to child: {}'.format(msg, host))
                agent.close(msg=msg)
                mlogger.debug('Agent process finished: {}:{}; '.format(host, agent.pid))
        elif self.__listener_q is not None:
            self.__listener_q.put('FINISH')
            listener_th.join()

        if self.__logger is not None:
            self.__logger.stop()
            self.__logger = None
        return result

    def __del__(self):
        self.close()

    def close(self):
        ''' closes open artifacts like MPlogger etc.
        '''
        if hasattr(self, '__logger'):
            if self.__logger is not None:
                try:
                    self.__logger.stop()
                except AttributeError:
                    pass
