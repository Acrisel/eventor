'''
Created on Nov 23, 2016

@author: arnon
'''

from enum import Enum
from acris.threaded import threaded

class EventorError(Exception):
    pass

class AssocType(Enum):
    event=1
    step=2
    
    
class TaskStatus(Enum):
    ''' Eventor internal task states
    '''
    ready=1     # triggered to run by events, waiting for resources
    allocate=2  # resource allocation, waiting for allocation of resources
    fueled=3   # resource satisfied, waiting to be activated
    active=4    # running
    success=5   # finished successfully
    failure=6   # failed to finish
    
    
class StepStatus(Enum):
    ''' Programmer Step interface 
    '''
    ready=1
    allocate=2
    fueled=3
    active=4
    success=5
    failure=6
    complete=7 # finished wither successfully or with failure
    
def task_to_step_status(status):
    value=status.value
    result=StepStatus(value)
    return result

def step_to_task_status(status):  
    '''
    This assumes that complete status was already converted to failure and success
    '''
    value=status.value
    result=TaskStatus(value)
    return result
    
class StepReplay(Enum):
    rerun=1
    skip=2

class RunMode(Enum):  
    recover=1
    restart=2  
    
class DbMode(Enum):
    write=1
    append=2
    read=3
    
class LoopControl(Enum):
    stop=1
    pause=2
    start=3
    resume=4
    kill=5  
    
class Invoke(object):
    def __init__(self, target, args=(), kwargs={}):
        self.target=target
        self.args=args
        self.kwargs=kwargs
        self.is_alive_flag=False
        
    def start(self,):
        self.is_alive_flag=True
        result=self.target(*self.args, **self.kwargs)
        self.is_alive_flag=False
        return result
    
    def join(self):
        return
    
    @threaded
    def is_alive(self):
        return self.is_alive_flag