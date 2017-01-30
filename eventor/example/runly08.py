
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
import os
import time

logger=logging.getLogger(__name__)

def prog(progname):
    logger.info("doing what %s is doing" % progname)
    logger.info("EVENTOR_STEP_SEQUENCE: %s" % os.getenv("EVENTOR_STEP_SEQUENCE"))
    return progname

def build_flow(run_mode):
    ev=evr.Eventor(run_mode=run_mode, logging_level=logging.INFO,)
    
    ev1s=ev.add_event('run_step1')
    ev2s=ev.add_event('run_step2')
    ev3s=ev.add_event('run_step3')
    
    s1=ev.add_step('s1', func=prog, kwargs={'progname': 'prog1'}, triggers={evr.StepStatus.success: (ev2s,),}) 
    s2=ev.add_step('s2', func=prog, kwargs={'progname': 'prog2'}, triggers={evr.StepStatus.success: (ev3s,), })
    s3=ev.add_step('s3', func=prog, kwargs={'progname': 'prog3'},)
    
    ev.add_assoc(ev1s, s1, delay=0)
    ev.add_assoc(ev2s, s2, delay=10)
    ev.add_assoc(ev3s, s3, delay=10)
    
    ev.trigger_event(ev1s, 1)
    return ev

ev=build_flow(run_mode=evr.RunMode.restart)
ev(max_loops=1)

for loop in range(4):
    delay=5 if loop in [1,2] else 15
    time.sleep(delay)
    ev=build_flow(run_mode=evr.RunMode.continue_)
    ev(max_loops=1)



