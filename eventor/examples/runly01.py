
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
"""

About
=========
:synopsis:     example use of grapior
:moduleauthor: Arnon Sela
:date:         Oct 18, 2016
:description:  use gradior dependencies and recovery
   
Outputs:
-------------------
N/A

Dependencies:
-------------------
N/A
      
**History:**
-------------------

:Author: Arnon Sela
:Modification:
   - Initial entry
:Date: Oct 18, 2016


API DOC:
===============     
"""

import eventor as evr
import logging
import examples.program as prog
import time


def construct_and_run():
    logger=logging.getLogger(__name__)
    
    logger.setLevel(logging.DEBUG)
    
    #ev=evr.Eventor(filename=':memory:')
    ev=evr.Eventor(logging_level=logging.INFO)
    
    ev1s=ev.add_event('run_step1')
    ev1d=ev.add_event('done_step1')
    ev2s=ev.add_event('run_step2')
    ev2d=ev.add_event('done_step2')
    ev3s=ev.add_event('run_step3', expr=(ev1d,ev2d)) 
    
    s1=ev.add_step('s1', func=prog.step1_create_data, kwargs={'outfile': 'source.txt'}, triggers={evr.StepStatus.complete: (ev1d, ev2s,),}) 
    s2=ev.add_step('s2', prog.step2_multiple_data, triggers={evr.StepStatus.complete: (ev2d,), })
    s3=ev.add_step('s3', prog.step3,)
    
    ev.add_assoc(ev1s, s1)
    ev.add_assoc(ev2s, s2)
    ev.add_assoc(ev3s, s3)
    
    ev.trigger_event(ev1s, 3)
    ev.loop_once()
    ev.loop_once()
    ev.loop_once()
    ev.loop_once()
    ev.loop_once()
    ev.loop_once()
    time.sleep(5)
    ev.loop_once()
    
    ev.close()

if __name__ == '__main__':
    import multiprocessing as mp
    mp.freeze_support()
    mp.set_start_method('spawn')
    construct_and_run()