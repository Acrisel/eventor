'''
Created on Oct 19, 2016

@author: arnon
'''
from inspect import isfunction
import logging

from .dbapi import DbApi
from .utils import get_step_id
from .eventor_types import EventorError, StepTriggers, TaskStatus

module_logger=logging.getLogger(__name__)

class Step(object):
    """A step in steps structure.  
       
        Each step has unique id that identifies it within Steps.
        It 
       
        A step is considered completed if it returns gradior.complete.
        step can also return gradior.failed or gradior.active.
       
        If step generate exception, it is considered gradior.FAILED.  The exception is
        also registered and could be referenced.   
    """

    def __init__(self, name=None, func=None, func_args=[], func_kwargs={}, triggers={}, recovery={}, config={}):
        '''
        Constructor
        '''
        
        self.name=name
        self.id=get_step_id()
        self.func=func
        self.func_args=func_args
        self.func_kwargs=func_kwargs
        self.triggers=triggers
        self.recovery=recovery
        self.config=config
        
        if not callable(func):
            raise EventorError('func must be callable: %s' % repr(func))
        
        self.path=None
        self.iter_path=None
        
    def __repr__(self):
        if hasattr(self.func, '__name__'):
            fname=self.func.__name__
        else:
            fname=self.func.__class__.__name__
            
        return "Step( name({}), func({}),)".format(self.name, fname,)
    
    def __str__(self):
        return repr(self)
          
    def db_write(self, db):
        db.add_step(step_id=self.id, name=self.name)
    
    def trigger_(self, db, sequence):
        db.add_task(event_id=self.id, sequence=sequence)
    
    def trigger_if_not_exists(self, db, sequence, status=TaskStatus.ready, recovery=None):
        added=db.add_task_if_not_exists(step_id=self.id, sequence=sequence, status=status, recovery=recovery)
        return added
    
    def __call__(self, seq_path=None, loop_value=None):
        module_logger.debug('Running step [%s]: %s' % (seq_path, repr(self) ))
        func=self.func
        func_args=self.func_args
        func_kwargs=self.func_kwargs
        #stop_on_exception=self.config['stop_on_exception']
        result=func(*func_args, **func_kwargs)
        module_logger.debug('Completed [%s]: %s' % (seq_path, repr(self) ))
        return result