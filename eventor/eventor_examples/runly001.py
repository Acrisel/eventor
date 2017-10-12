#!/usr/bin/env python
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


logger=logging.getLogger(__name__)

def prog(progname):
    logger.info("doing what %s is doing" % progname)
    logger.info("EVENTOR_STEP_SEQUENCE: %s" % os.getenv("EVENTOR_STEP_SEQUENCE"))
    return progname
    

class MyEnventor(evr.Eventor):
    def __init__(self, ):
        db = 'pgdb2'
        config = os.path.abspath('runly.conf')
        super().__init__(name=__class__.__name__, config=config, store=db,)

    def construct_and_run(self):         
        ev1s = self.add_event('run_step1')
        ev2s = self.add_event('run_step2')
        ev3s = self.add_event('run_step3')
        
        s1 = self.add_step('s1', func=prog, kwargs={'progname': 'prog1'}, triggers={evr.StepStatus.success: (ev2s,),}) 
        s2 = self.add_step('s2', func=prog, kwargs={'progname': 'prog2'}, triggers={evr.StepStatus.success: (ev3s,), })
        s3 = self.add_step('s3', func=prog, kwargs={'progname': 'prog3'},)
        
        self.add_assoc(ev1s, s1)
        self.add_assoc(ev2s, s2)
        self.add_assoc(ev3s, s3)
    
        self.trigger_event(ev1s, 1)
        self.run()
        self.close()
    
if __name__ == '__main__':
    import multiprocessing as mp
    mp.freeze_support()
    mp.set_start_method('spawn')
    myeventor = MyEnventor()
    myeventor.construct_and_run()

