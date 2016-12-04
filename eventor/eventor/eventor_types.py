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
    ready=1
    active=2
    success=3
    failure=4
    
    
class StepStatus(Enum):
    ready=1
    active=2
    success=3
    failure=4
    complete=5
    
def task_to_step_status(status):
    value=status.value
    result=StepStatus(value)
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
    
class LoopControl(Enum):
    stop=1
    pause=2
    start=3
    resume=4
    kill=5    