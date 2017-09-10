'''
Created on Sep 8, 2017

@author: arnon
'''

import collections
import acris  

class Container(object):
    
    class IterGen(object):
        def __init__(self, l):
            self.l=l
            
        def __call__(self):
            return (x for x in self.l)

    def __init__(self, progname, loop=[1,], iter_triggers=(), end_triggers=()):
        #self.ev=ev
        self.progname = progname
        self.iter_triggers = iter_triggers
        self.end_triggers = end_triggers
        if isinstance(loop, collections.Iterable):
            loop = Container.IterGen(loop)
        self.loop = loop
        self.loop_index = 0
        #self.initiating_sequence=None
        
    def __call__(self, initial=False, eventor=None): 
        #print('max_concurrent', config['max_concurrent'])
        #self.ev = eventor
        if initial:
            self.iter = acris.Mediator(self.loop())
            todos=1
            #self.initiating_sequence=__eventor.get_task_sequence()
        else:
            todos = eventor.count_todos() 
        
        if todos == 1 or initial:
            try:
                item = next(self.iter)
            except StopIteration:
                item = None
            if item:
                self.loop_index += 1
                for trigger in self.iter_triggers:
                    eventor.trigger_event(trigger, self.loop_index)
                    #eventor.remote_trigger_event(trigger, self.loop_index,)
            else:
                for trigger in self.end_triggers:
                    eventor.trigger_event(trigger, self.loop_index)
                    #eventor.remote_trigger_event(trigger, self.loop_index,)
            
        return True