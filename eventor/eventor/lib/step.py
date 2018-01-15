'''
Created on Oct 19, 2016

@author: arnon
'''
import logging
import pprint
from .eventor_types import EventorError, TaskStatus

mlogger = logging.getLogger(__name__)


class Step(object):
    """A step in steps structure.

        Each step has unique id that identifies it within Steps.
        It

        A step is considered completed if it returns gradior.complete.
        step can also return gradior.failed or gradior.active.

        If step generate exception, it is considered gradior.FAILED. The exception is
        also registered and could be referenced.
    """

    def __init__(self, name=None, func=None, func_args=[], func_kwargs={}, host=[], triggers={}, acquires=None, releases=None, recovery={}, config={}, logger=None):
        '''
        Constructor
        '''
        global mlogger

        self.name = name
        self.id_ = name  # get_step_id()
        self.func = func
        self.func_args = func_args
        self.func_kwargs = func_kwargs
        self.triggers = triggers
        self.recovery = recovery
        self.config = config
        # self.pass_sequence=pass_sequence
        self.concurrent = 0
        self.acquires = acquires
        self.releases = releases if releases is not None else acquires
        self.host = host

        if func is not None and not callable(func):
            raise EventorError('Func must be callable: %s' % repr(func))

        self.path = None
        self.iter_path = None
        if logger is not None:
            mlogger = logger

    def __repr__(self):
        if hasattr(self.func, '__name__'):
            fname = self.func.__name__
        else:
            fname = self.func.__class__.__name__

        str_args = ", ".join([repr(arg) for arg in self.func_args])
        if str_args:
            str_args += ', '
        str_kwargs = ", ".join(["%s=%s" % (name, repr(value))
                                for name, value in self.func_kwargs.items()
                                if name != 'eventor'])

        # triggers=', '.join([pprint.pformat(t) for t in self.triggers])
        triggers = pprint.pformat(self.triggers)
        return "Step( name({}), func( {}({}{}) ), triggers({}))".format(self.name, fname, str_args, str_kwargs, triggers)

    def __str__(self):
        return repr(self)

    def _name(self, seq_path):
        result = '/'
        if self.name:
            result = "%s/%s" % (self.name, seq_path)
        return result

    def db_write(self, db):
        db.add_step(step_id=self.id_, name=self.name)

    def trigger_(self, db, sequence, host):
        mlogger.debug('[ Step {}/{} ] Adding as task to DB'.format(self.name, sequence,))
        db.add_task(event_id=self.id_, sequence=sequence, host=host, status=TaskStatus.ready)

    def trigger_if_not_exists(self, db, sequence, status, recovery=None):
        mlogger.debug('[ Step {}/{} ] Adding, if not already exists, as task to DB'.format(self.name, sequence))
        added = db.add_task_if_not_exists(step_id=self.id_, sequence=sequence, host=self.host,
                                          status=status, recovery=recovery)
        return added

    def __call__(self, seq_path=None, loop_value=None, logger=None, eventor=None):
        if logger is not None:
            mlogger = logger
        mlogger.debug('[ Step {} ] Starting: {}'.format(self._name(seq_path), repr(self)))
        if self.func is not None:
            func = self.func
            func_args = self.func_args
            func_kwargs = self.func_kwargs
            sequence_arg_name = self.config['sequence_arg_name']
            if sequence_arg_name:
                self.func_kwargs.update({sequence_arg_name: seq_path})
            pass_logger_to_task = self.config.get('pass_logger_to_task', False)
            if pass_logger_to_task:
                self.func_kwargs.update({'logger': mlogger})
            # if self.config['pass_resources']:
            #     self.func_kwargs.update({'eventor_task_resoures': resources})
            # stop_on_exception=self.config['stop_on_exception']
            str_args = ", ".join([repr(arg) for arg in func_args])
            if str_args:
                str_args += ', '
            str_kwargs = ", ".join(["{}={}".format(name, repr(value))
                                    for name, value in func_kwargs.items()])
            if eventor is not None:
                func_kwargs['eventor'] = eventor
            name = func.__name__ if hasattr(self.func, '__name__') else func.__class__.__name__
            mlogger.debug('[ Step {} ] running {}({}{}).'.format(self._name(seq_path), name,
                                                                 str_args, str_kwargs))
            result = func(*func_args, **func_kwargs)
        else:
            result = True
        # if 'eventor' in func_kwargs:
        #     del func_kwargs['eventor']
        mlogger.debug('[ Step {} ] Completed: {}'.format(self._name(seq_path), repr(self)))
        return result
