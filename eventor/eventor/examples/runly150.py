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
import os
from eventor.examples.run_types import prog, Container


logger = logging.getLogger(__name__)


def construct_and_run():
    db = 'pgdb2'
    config = os.path.abspath('runly.conf')
    if config.startswith('/private'):
        config = config[8:]   
    ev = evr.Eventor(name=os.path.basename(__file__), logging_level=logging.DEBUG, config=config, config_tag='EVENTOR', store=db, shared_db=False, import_module=["examples.run_types", ],)
    
    ev0first = ev.add_event('s0_start')
    ev0next = ev.add_event('s0_next')
    ev00first = ev.add_event('s0_00_start')
    ev00next = ev.add_event('s0_s00_next')
    ev1s = ev.add_event('s0_s00_s1_start')
    ev1success = ev.add_event('s0_s00_s1_success')
    ev2s = ev.add_event('s0_s00_s2_start', expr=(ev1success,))
    ev2success = ev.add_event('s0_s00_s2_success')
    ev3s = ev.add_event('s0_s00_s3_start', expr=(ev2success,))
    
    # on invoke, Eventor will pass itself as kwargs.
    metaprog = Container(progname='S0', loop=[1,2,], iter_triggers=(ev00first,))
    s0first = ev.add_step('s0_start', func=metaprog, kwargs={'initial': True, }, config={'max_concurrent': -1, 'task_construct': 'invoke', 'pass_logger_to_task': True})
    s0next = ev.add_step('s0_next', func=metaprog, config={'task_construct': 'invoke', 'pass_logger_to_task': True})
    
    metaprog = Container(progname='S00', loop=[1,2,], iter_triggers=(ev1s,), end_triggers=(ev0next,))
    
    #s00first=ev.add_step('s0_s00_start', func=metaprog, kwargs={'initial': True}, config={'task_construct': threading.Thread})
    #s00next=ev.add_step('s0_s00_next', func=metaprog, config={'task_construct': threading.Thread})
    s00first = ev.add_step('s0_s00_start', func=metaprog, kwargs={'initial': True}, config={'max_concurrent': -1, 'task_construct': 'invoke', 'pass_logger_to_task': True})
    s00next = ev.add_step('s0_s00_next', func=metaprog, config={'task_construct': 'invoke', 'pass_logger_to_task': True})
    
    s1 = ev.add_step('s0.s00.s1', func=prog, kwargs={'progname': 'prog1'}, triggers={evr.StepStatus.success: (ev1success,),}, host='ubuntud01_eventor') 
    s2 = ev.add_step('s0.s00.s2', func=prog, kwargs={'progname': 'prog2'}, triggers={evr.StepStatus.success: (ev2success,), })
    
    s3 = ev.add_step('s0.s00.s3', func=prog, kwargs={'progname': 'prog3'}, triggers={evr.StepStatus.complete: (ev00next,), })
    
    ev.add_assoc(ev0first, s0first)
    ev.add_assoc(ev0next, s0next)
    ev.add_assoc(ev00first, s00first)
    ev.add_assoc(ev00next, s00next)
    ev.add_assoc(ev1s, s1)
    ev.add_assoc(ev2s, s2)
    ev.add_assoc(ev3s, s3)
    
    ev.trigger_event(ev0first, '0')
    #print(ev.program_repr())
    ev.run()
    ev.close()
    
if __name__ == '__main__':
    import multiprocessing as mp
    mp.freeze_support()
    mp.set_start_method('spawn')
    construct_and_run()