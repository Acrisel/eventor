'''
Created on Oct 19, 2016

@author: arnon
'''

from acris import Sequence
from logging.handlers import QueueListener
import inspect
import datetime
import os


def is_require_op(op):
    if op in ['or', 'and',]:
        return True
    return False

def op_to_lambda(op):
    return "lambda x,y: x {} y".format(op)

StepId=Sequence('_EventorStepId')
EventId=Sequence('_EventorEventId')

def rest_sequences():
    StepId.reset()
    EventId.reset()

def get_step_id():
    return "S%s" % StepId()

def get_event_id():
    return "E%s" % EventId()


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
            if record.levelno >= handler.level: # This check is not in the parent class
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
     File "/private/var/acrisel/sand/gradior/gradior/gradior/gradior/loop_task.py", line 41, in task_wrapper
    '''
    result=[ "File \"%s\", line %s, in %s\n    %s" % (frame.filename, frame.lineno, frame.function, frame.code_context[0].rstrip()) for frame in trace]
    return result


def calling_module(depth=2):
    frame_records = inspect.stack()[2]
    return frame_records.filename

def store_from_module(module, module_location=False):
    location=os.path.dirname(module)
    name=os.path.basename(module)
    
    parts=name.rpartition('.')
    if parts[0]:
        if parts[2] == 'py':
            module_runner_file=parts[0]
        else:
            module_runner_file=name
    else:
        module_runner_file=parts[2]
    filename='.'.join([module_runner_file, 'run.db'])  
    
    if module_location:
        filename=os.path.join(location, filename)
    else:
        filename=os.path.join(os.getcwd(), filename)  
    return filename



from types import FunctionType

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
                    decorated=decorator(name, value)
                    dct[attr] = decorated
                    #print('decorated', attr, decorated)
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
            start=datetime.datetime.now()
            result=f(*args, **kwargs)
            finish=datetime.datetime.now()
            print_func('exiting method: %s.%s, time span: %s' % (name, f.__name__, str(finish-start)))
            return result
        return wrapper
    return print_method_name

if __name__ == '__main__':

    meta_decorator=decorate_all(print_method(print))
    
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
     
    foo=Foo()
    foo.bar()   
    foo.bar()   
    
