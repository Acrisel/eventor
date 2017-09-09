'''
Created on Sep 8, 2017

@author: arnon
'''

import collections
from acris import Mediator


class IterGen(object):
    def __init__(self, l):
        self.l=l
        
    def __call__(self):
        return (x for x in self.l)


class Container(object):
    def __init__(self, ev, progname, loop=[1,], iter_triggers=(), end_triggers=()):
        self.ev=ev
        self.progname=progname
        self.iter_triggers=iter_triggers
        self.end_triggers=end_triggers
        if isinstance(loop, collections.Iterable):
            loop=IterGen(loop)
        self.loop=loop
        self.loop_index=0
        #self.initiating_sequence=None
        
    def __call__(self, initial=False, ): 
        #print('max_concurrent', config['max_concurrent'])
        if initial:
            self.iter=Mediator(self.loop())
            todos=1
            #self.initiating_sequence=self.ev.get_task_sequence()
        else:
            todos=self.ev.count_todos() 
        
        if todos ==1 or initial:
            try:
                item=next(self.iter)
            except StopIteration:
                item=None
            if item:
                self.loop_index+=1
                for trigger in self.iter_triggers:
                    self.ev.trigger_event(trigger, self.loop_index)
                    #self.ev.remote_trigger_event(trigger, self.loop_index,)
            else:
                for trigger in self.end_triggers:
                    self.ev.trigger_event(trigger, self.loop_index)
                    #self.ev.remote_trigger_event(trigger, self.loop_index,)
            
        return True
