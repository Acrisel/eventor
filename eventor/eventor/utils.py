'''
Created on Oct 19, 2016

@author: arnon
'''

from threading import Lock
from acris import Sequence
import logging
from logging.handlers import QueueListener, QueueHandler
import os
import multiprocessing as mp
import inspect


def is_require_op(op):
    if op in ['or', 'and',]:
        return True
    return False

def op_to_lambda(op):
    return "lambda x,y: x {} y".format(op)

StepId=Sequence('StepId')
EventId=Sequence('EventId')

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
