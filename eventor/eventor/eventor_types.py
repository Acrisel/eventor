'''
Created on Nov 23, 2016

@author: arnon
'''

from enum import Enum

class EventorError(Exception):
    pass

class AssocType(Enum):
    event=1
    step=2
    
    
class TaskStatus(Enum):
    ready=1     # triggered to run by events, waiting for resources
    staisfy=2   # resource satisfied, waiting to be activated
    active=3    # running
    success=4   # finished successfully
    failure=5   # failed to finish
    
    
class StepStatus(Enum):
    ready=1
    staisfy=2
    active=3
    success=4
    failure=5
    complete=6 # finished wither successfully or with failure
    
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
        
    def start(self,):
        return self.target(*self.args, **self.kwargs)
    
    def join(self):
        return