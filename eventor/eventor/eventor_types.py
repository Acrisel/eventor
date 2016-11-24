'''
Created on Nov 23, 2016

@author: arnon
'''

from enum import Enum

class AssocType(Enum):
    event=1
    step=2
    
class TaskStatus(Enum):
    ready=1
    active=2
    fail=4
    complete=5