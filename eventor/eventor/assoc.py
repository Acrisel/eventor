'''
Created on Oct 31, 2016

@author: arnon
'''

from .step import Step
import logging
#from .dbschema import Assoc as AssocDb
from .event import Event
from .eventor_types import EventorError

module_logger=logging.getLogger(__name__)


class Assoc(object):
    
    def __init__(self, event, assoc_obj):
        if not isinstance(event, Event):
            raise EventorError('event argument must be Event, but found %s' % type(event))
        if not isinstance(assoc_obj, (Event, Step)):
            raise EventorError('assoc_obj argument must be Event or Step, but found %s' % type(assoc_obj))
        
        self.event=event
        self.assoc_obj=assoc_obj
                    
    def __repr__(self):
        return "Assoc(%s, %s)" % (repr(self.event), repr(self.assoc_obj))
        
    def __str__(self):
        return "Assoc(%s, %s)" % (str(self.event), str(self.assoc_obj))

    #def db_write(self, db):
    #    db.add_assoc(event_id=self.event.id, obj_type=type(self.assoc_obj), obj_id=self.assoc_obj.id)