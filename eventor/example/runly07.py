# -*- encoding: utf-8 -*-
##############################################################################
#
#    Acrisel LTD
#    Copyright (C) 2008- Acrisel (acrisel.com) . All Rights Reserved
#
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################

import eventor as evr
import logging
import collections
import queue
from enum import Enum
import acris.virtual_resource_pool as rp

logger=logging.getLogger(__name__)

class IterGen(object):
    def __init__(self, l):
        self.l=l
        
    def __call__(self):
        return (x for x in self.l)

def prog(progname):
    logger.info("doing what %s is doing" % progname)
    return progname


class Container(object):
    def __init__(self, ev, progname, loop=[1,], max_concurrent=1, iter_triggers=(), end_triggers=()):
        self.ev=ev
        self.progname=progname
        self.iter_triggers=iter_triggers
        self.end_triggers=end_triggers
        if isinstance(loop, collections.Iterable):
            loop=IterGen(loop)
        self.loop=loop
        self.loop_index=0
        self.max_concurrent=max_concurrent
        self.concurrent_count=0
        #self.initiating_sequence=None
        
    def __call__(self, do='next', ): 
        #print('max_concurrent', config['max_concurrent'])
        if do=='init':
            self.iter=self.loop()
            todos=1
            #self.initiating_sequence=self.ev.get_task_sequence()
        else:
            todos=self.ev.count_todos() 
            self.concurrent_count-=1
        
        if todos == 1 or do == 'init' and self.concurrent_count < self.max_concurrent:
            try:
                item=next(self.iter)
            except StopIteration:
                item=None
                
            if item:
                self.loop_index+=1
                self.concurrent_count+=1
                for trigger in self.iter_triggers:
                    self.ev.trigger_event(trigger, self.loop_index)
                    #self.ev.remote_trigger_event(trigger, self.loop_index,)
            else:
                for trigger in self.end_triggers:
                    self.ev.trigger_event(trigger, self.loop_index)
            
        return True
           

ev=evr.Eventor( logging_level=logging.INFO, ) #config={'sleep_between_loops': 1}) # store=':memory:',

ev0first=ev.add_event('s0_start')
ev0next=ev.add_event('s0_next')
ev0end=ev.add_event('s0_end')
ev00first=ev.add_event('s0_00_start')
ev00next=ev.add_event('s0_s00_next')
ev00end=ev.add_event('s0_s00_end')
ev1s=ev.add_event('s0_s00_s1_start')
ev1success=ev.add_event('s0_s00_s1_success')
ev2s=ev.add_event('s0_s00_s2_start', expr=(ev1success,))
ev2success=ev.add_event('s0_s00_s2_success')
ev3s=ev.add_event('s0_s00_s3_start', expr=(ev2success,))

class StepResource(rp.Resource): pass
rp1=rp.ResourcePool('RP1', resource_cls=StepResource, policy={'resource_limit': 2, }).load()                   
rp2=rp.ResourcePool('RP2', resource_cls=StepResource, policy={'resource_limit': 2, }).load()                   

metaprog1=Container(ev=ev, progname='s0', loop=[1,2,], max_concurrent=2, iter_triggers=(ev00first,), end_triggers=(ev0end,))
s0first=ev.add_step('s0_start', func=metaprog1, kwargs={'do': 'init', }, acquires=[(rp1, 1), ], releases=[], 
                    config={'max_concurrent': -1, 'task_construct': evr.Invoke})
s0next=ev.add_step('s0_next', func=metaprog1, config={'task_construct': evr.Invoke})
s0end=ev.add_step('s0_end', releases=[(rp1, 1), ], config={'task_construct': evr.Invoke})
  
metaprog2=Container(ev=ev, progname='00', loop=[1,2,], max_concurrent=2, iter_triggers=(ev1s,), end_triggers=(ev00end,))
s00first=ev.add_step('s0_s00_start', func=metaprog2, kwargs={'do': 'init', }, acquires=[(rp2, 1), ], releases=[], 
                     config={'max_concurrent': -1, 'task_construct': evr.Invoke,})
s00next=ev.add_step('s0_s00_next', func=metaprog2, config={'task_construct': evr.Invoke,})
s00end=ev.add_step('s0_s00_end', releases=[(rp2, 1),], config={'task_construct': evr.Invoke,}, triggers={evr.StepStatus.success: (ev0next,), })

s1=ev.add_step('s0.s00.s1', func=prog, kwargs={'progname': 'prog1'}, triggers={evr.StepStatus.success: (ev1success,),}) 
s2=ev.add_step('s0.s00.s2', func=prog, kwargs={'progname': 'prog2'}, triggers={evr.StepStatus.success: (ev2success,), })
s3=ev.add_step('s0.s00.s3', func=prog, kwargs={'progname': 'prog3'}, triggers={evr.StepStatus.complete: (ev00next,), })

ev.add_assoc(ev0first, s0first)
ev.add_assoc(ev0next, s0next)
ev.add_assoc(ev0end, s0end)
ev.add_assoc(ev00first, s00first)
ev.add_assoc(ev00next, s00next)
ev.add_assoc(ev00end, s00end)
ev.add_assoc(ev1s, s1)
ev.add_assoc(ev2s, s2)
#ev.add_assoc(ev00end, s0next)
ev.add_assoc(ev3s, s3)

ev.trigger_event(ev0first)
ev()