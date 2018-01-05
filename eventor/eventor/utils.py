'''
Created on Oct 19, 2016

@author: arnon
'''

from acrilib import Sequence
from logging.handlers import QueueListener
import inspect
import datetime
import os
import socket
from types import FunctionType
import yaml


def is_require_op(op):
    if op in ['or', 'and']:
        return True
    return False


def op_to_lambda(op):
    return "lambda x,y: x {} y".format(op)


StepId = Sequence('_EventorStepId')
EventId = Sequence('_EventorEventId')
DelayId = Sequence('_EventorDelayId')


def rest_sequences():
    StepId.reset()
    EventId.reset()
    DelayId.reset()


def get_step_id():
    return "S%s" % StepId()


def get_event_id():
    return "E%s" % EventId()


def get_delay_id():
    return "d%s" % DelayId()


def valid_step_name(name):
    return name.find('.') == -1


class CustomQueueListener(QueueListener):
    def __init__(self, queue, *handlers):
        super(CustomQueueListener, self).__init__(queue, *handlers)
        """
        Initialise an instance with the specified queue and
        handlers.
        """
        # Changing this to a list from tuple in the parent class
        self.handlers = list(handlers)

    def handle(self, record):
        """
        Override handle a record.

        This just loops through the handlers offering them the record
        to handle.

        :param record: The record to handle.
        """
        record = self.prepare(record)
        for handler in self.handlers:
            if record.levelno >= handler.level:  # This check is not in the parent class
                handler.handle(record)

    def addHandler(self, hdlr):
        """
        Add the specified handler to this logger.
        """
        if not (hdlr in self.handlers):
            self.handlers.append(hdlr)

    def removeHandler(self, hdlr):
        """
        Remove the specified handler from this logger.
        """
        if hdlr in self.handlers:
            hdlr.close()
            self.handlers.remove(hdlr)


def traces(trace):
    '''
     File "/private/var/acrisel/sand/gradior/gradior/gradior/gradior/loop_task.py",
     line 41, in task_wrapper
    '''
    result = ["File \"{}\", line {}, in {}\n    {}"
              .format(frame.filename, frame.lineno, frame.function,
                      frame.code_context[0].rstrip()) for frame in trace]
    return result


def calling_module(depth=2):
    frame_records = inspect.stack()[depth]
    return frame_records.filename


def store_from_module(module, module_location=False):
    location = os.path.dirname(module)
    name = os.path.basename(module)

    parts = name.rpartition('.')
    if parts[0]:
        if parts[2] == 'py':
            module_runner_file = parts[0]
        else:
            module_runner_file = name
    else:
        module_runner_file = parts[2]
    filename = '.'.join([module_runner_file, 'run.db'])

    if module_location:
        filename = os.path.join(location, filename)
    else:
        filename = os.path.join(os.getcwd(), filename)
    return filename


# check if an object should be decorated
def do_decorate(attr, value):
    # result = ('__' not in attr and
    result = (isinstance(value, FunctionType) and
              getattr(value, 'decorate', True))
    return result


# decorate all instance methods (unless excluded) with the same decorator
def decorate_all(decorator):
    class DecorateAll(type):
        def __new__(cls, name, bases, dct):
            for attr, value in dct.items():
                if do_decorate(attr, value):
                    decorated = decorator(name, value)
                    dct[attr] = decorated
                    # print('decorated', attr, decorated)
            return super(DecorateAll, cls).__new__(cls, name, bases, dct)
    return DecorateAll


# decorator to exclude methods
def dont_decorate(f):
    f.decorate = False
    return f


def print_method(print_func):
    def print_method_name(name, f):
        def wrapper(*args, **kwargs):
            print_func('entering method: %s.%s' % (name, f.__name__, ))
            start = datetime.datetime.now()
            result = f(*args, **kwargs)
            finish = datetime.datetime.now()
            print_func('exiting method: {}.{}, time span: {}'
                       .format(name, f.__name__, str(finish - start)))
            return result
        return wrapper
    return print_method_name


def port_is_open(host, port,):
    result = False
    try:
        s = socket.create_connection((host, port), 0.5)
    except socket.error:
        pass
    else:
        s.close()
        result = True
    return result


LOCAL_HOST = '127.0.0.1'


def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((LOCAL_HOST, 0))
    host, port = s.getsockname()
    s.close()
    return host, port


''' Left here for reference only
from acrilog import SSHLogger
def logger_process_lambda(logger_info):
    logger_info = deepcopy(logger_info)
    def internal(name=None):
        if name is not None:
            logger_info['name'] = name
        logger = NwLogger.get_logger(logger_info)
        return logger
    return internal
'''

if __name__ == '__main__':

    meta_decorator = decorate_all(print_method(print))

    class Foo(metaclass=meta_decorator):

        def __init__(self):
            pass

        def bar(self):
            pass

        @dont_decorate
        def baz(self):
            pass

        @classmethod
        def test(self):
            pass

    foo = Foo()
    foo.bar()
    foo.bar()
