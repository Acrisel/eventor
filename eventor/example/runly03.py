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
import math

logger=logging.getLogger(__name__)

logger.setLevel(logging.INFO)

def square(x):
    y=x*x/0
    return y

def square_root(x):
    y=math.sqrt(x)
    return y

def divide(x,y):
    z=x/y
    return z

def build_eventor(run_mode=evr.RunMode.restart):
    ev=evr.Eventor(run_mode=run_mode, logging_level=logging.DEBUG)
    
    ev1s=ev.add_event('run_step1')
    ev1d=ev.add_event('done_step1')
    ev2s=ev.add_event('run_step2')
    ev2d=ev.add_event('done_step2')
    ev3s=ev.add_event('run_step3', expr=(ev1d,ev2d)) 
    
    s1=ev.add_step('s1', func=square, kwargs={'x': 3}, 
                   triggers={evr.StepTriggers.at_success: (ev1d, ev2s,)}, 
                   recovery={evr.StepTriggers.at_failure: evr.StepReplay.rerun, 
                             evr.StepTriggers.at_success: evr.StepReplay.skip}) 
    s2=ev.add_step('s2', square_root, kwargs={'x': 9}, triggers={evr.StepTriggers.at_complete: (ev2d,), })
    s3=ev.add_step('s3', divide, kwargs={'x': 9, 'y': 3},)
    
    ev.add_assoc(ev1s, s1)
    ev.add_assoc(ev2s, s2)
    ev.add_assoc(ev3s, s3)
    ev.trigger_event(ev1s, 3)    
    return ev

# start regularly; it would fail in step 2
ev=build_eventor()
ev()

# rerun in recovery
ev=build_eventor(evr.RunMode.recover)
ev()

