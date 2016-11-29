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
    
    
class StepTriggers(Enum):
    at_ready=1
    at_active=2
    at_success=3
    at_failure=4
    at_complete=5
   
    
class StepReplay(Enum):
    rerun=1
    skip=2

class RunMode(Enum):  
    recover=1
    restart=2  
    
def step_status_to_trigger(status):
    value=status.value
    return StepTriggers(value)
    
class DbMode(Enum):
    write=1
    append=2
    
class LoopControl(Enum):
    stop=1
    pause=2
    start=3
    resume=4
    kill=5    