'''
Created on Oct 31, 2016

@author: arnon
'''

from eventor.utils import get_event_id, is_require_op, op_to_lambda
from eventor.eventor_types import EventorError
from eventor.step import Step
from collections import OrderedDict
import logging
from eventor.dbschema import Task
from _ast import arg

module_logger=logging.getLogger(__name__)

def expr_to_str(*args):
    items=list()
    for arg in args:
        if type(arg) == str:
            result=arg
        elif isinstance(arg, Event):
            result=arg.id_
        elif type(arg) == tuple:
            result= "(" + expr_to_str(*arg) +")" 
        else:
            raise EventorError("unknown variable in logical operation: %s" % repr(arg))
        items.append(result)
            
    expr="(" + ") and (".join(items) + ")"
    return expr
    

def or_(*args):
    items=list()
    for arg in args:
        result= expr_to_str(arg)
        items.append(result)
            
    expr=" or ".join(items)
    return expr

class Event(object):
    """Event object used to reuse in user program.
        
        Event objects are created by Eventor.add_event programming interface or by the mechanism itself
    
        Attributes:
            N/A
            
        Methods:
            db_write: write event to db file
    
    """

    def __init__(self, name, expr=None):
        self.name=name
        self.expr=expr
        if expr:
            self.expr=expr_to_str(expr)
        self.id_=name #get_event_id()
                    
    def __repr__(self):
        expr=''
        if self.expr:
            expr=", %s" % self.expr
        return "Event(%s%s)" % (self.id_, expr)
        
    def __str__(self):
        return repr(self)
    
    def db_write(self, db):
        db.add_event(event_id=self.id_, name=self.name,)
    
    def trigger_(self, db, sequence):
        db.add_trigger(event_id=self.id_, sequence=sequence)
    
    def trigger_if_not_exists(self, db, sequence, recovery):
        added=db.add_trigger_if_not_exists(event_id=self.id_, sequence=sequence, recovery=recovery)
        return added
    
if __name__ == '__main__':
    e1=Event('E1')
    e2=Event('E2')
    e3=Event('E3')
    e4=Event('E4')
    
    expr=expr_to_str(or_(e1,e2),or_(e3,e4))
    print(expr, eval(expr, globals(), 
                     {'E0': True, 'E1': True, 'E2': False, 'E3': False, 'E4': True,}))
    
    expr=expr_to_str(e3,e4)
    print(expr, eval(expr, globals(), 
                     {'E0': True, 'E1': True, 'E2': False, 'E3': False, 'E4': True,}))
    
    expr=expr_to_str((e1,e2))
    print(expr, eval(expr, globals(), 
                     {'E0': True, 'E1': True, 'E2': False, 'E3': False, 'E4': True,}))
    