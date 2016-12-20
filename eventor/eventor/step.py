'''
Created on Oct 19, 2016

@author: arnon
'''
import logging
import pprint

from .eventor_types import EventorError, TaskStatus
#from .utils import decorate_all, print_method_name

module_logger=logging.getLogger(__name__)

#class Step(metaclass=decorate_all(print_method_name)):
class Step(object):
    """A step in steps structure.  
       
        Each step has unique id that identifies it within Steps.
        It 
       
        A step is considered completed if it returns gradior.complete.
        step can also return gradior.failed or gradior.active.
       
        If step generate exception, it is considered gradior.FAILED.  The exception is
        also registered and could be referenced.   
    """

    def __init__(self, name=None, func=None, func_args=[], func_kwargs={}, triggers={}, acquires=None, releases=None, recovery={}, config={}):
        '''
        Constructor
        '''
        
        self.name=name
        self.id_=name #get_step_id()
        self.func=func
        self.func_args=func_args
        self.func_kwargs=func_kwargs
        self.triggers=triggers
        self.recovery=recovery
        self.config=config
        #self.pass_sequence=pass_sequence
        self.concurrent=0
        self.acquires=acquires
        self.releases=releases if releases is not None else acquires
        
        if func is not None and not callable(func):
            raise EventorError('func must be callable: %s' % repr(func))
        
        self.path=None
        self.iter_path=None
        
    def __repr__(self):
        if hasattr(self.func, '__name__'):
            fname=self.func.__name__
        else:
            fname=self.func.__class__.__name__
        
        #triggers=', '.join([pprint.pformat(t) for t in self.triggers])
        triggers=pprint.pformat(self.triggers)
        return "Step( name({}), func({}), triggers({}))".format(self.name, fname, triggers)
    
    def __str__(self):
        return repr(self)
          
    def db_write(self, db):
        db.add_step(step_id=self.id_, name=self.name)
    
    def trigger_(self, db, sequence):
        db.add_task(event_id=self.id_, sequence=sequence,status=TaskStatus.ready)
    
    def trigger_if_not_exists(self, db, sequence, status, recovery=None):
        added=db.add_task_if_not_exists(step_id=self.id_, sequence=sequence, status=status, recovery=recovery)
        return added
    
    def __call__(self, seq_path=None, loop_value=None,):
        module_logger.debug('[ Step %s/%s ] Starting: %s' % (self.name, seq_path, repr(self) ))
        if self.func is not None:
            func=self.func
            func_args=self.func_args
            func_kwargs=self.func_kwargs
            sequence_arg_name=self.config['sequence_arg_name']
            if sequence_arg_name:
                self.func_kwargs.update({sequence_arg_name: seq_path})
            #if self.config['pass_resources']:
            #    self.func_kwargs.update({'eventor_task_resoures': resources})
            #stop_on_exception=self.config['stop_on_exception']
            result=func(*func_args, **func_kwargs)
        else:
            result=True
        module_logger.debug('[ Step %s/%s ] Completed: %s' % (self.name, seq_path, repr(self) ))
        return result
