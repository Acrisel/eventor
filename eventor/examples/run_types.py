'''
Created on Sep 8, 2017

@author: arnon
'''

import collections
import acris  
from acris import virtual_resource_pool as rp

class StepResource(rp.Resource): pass

class Container(object):
    
    class IterGen(object):
        def __init__(self, l):
            self.l=l
            
        def __call__(self):
            return (x for x in self.l)

    def __init__(self, progname, loop=[1,], max_concurrent=1, iter_triggers=(), end_triggers=()):
        #self.ev=ev
        self.progname = progname
        self.iter_triggers = iter_triggers
        self.end_triggers = end_triggers
        if isinstance(loop, collections.Iterable):
            loop = Container.IterGen(loop)
        self.loop = loop
        self.loop_index = 0
        self.max_concurrent = max_concurrent
        self.concurrent_count = 0
        #self.initiating_sequence=None
        self.__name__ = Container.__name__
        
    def __call__(self, initial=False, eventor=None, logger=None): 
        #print('max_concurrent', config['max_concurrent'])
        #self.ev = eventor
        if initial:
            logger.debug('Container: initiating container at first call.')
            self.iter = acris.Mediator(self.loop())
            todos = 1
            #self.initiating_sequence=__eventor.get_task_sequence()
        else:
            todos, _ = eventor.count_todos() 
            self.concurrent_count -= 1
            logger.debug('Container: Counted todos: {}'.format(todos))
        
        if todos == 1 or initial and self.concurrent_count < self.max_concurrent:
            try:
                item = next(self.iter)
            except StopIteration:
                item = None
            logger.debug('Container: item: {}'.format(item))
            
            if item:
                self.loop_index += 1
                self.concurrent_count += 1
                logger.debug('Container: new index: {}'.format(self.loop_index))
                for trigger in self.iter_triggers:
                    eventor.trigger_event(trigger, str(self.loop_index))
                    #eventor.remote_trigger_event(trigger, self.loop_index,)
            else:
                for trigger in self.end_triggers:
                    eventor.trigger_event(trigger, str(self.loop_index))
                    #eventor.remote_trigger_event(trigger, self.loop_index,)
            
        return True
    
import os

def prog(progname, logger=None):
    func = print
    if logger:
        func=logger.info
    func("doing what %s is doing" % progname)
    func("EVENTOR_STEP_SEQUENCE: %s" % os.getenv("EVENTOR_STEP_SEQUENCE"))
    return progname

