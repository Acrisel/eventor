
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

def construct_and_run(): 
    #db = 'sqfile00'
    db = 'pgdb2'
    config=os.path.abspath('example00.conf')
    # because OSX adds /var -> /private/var
    if config.startswith('/private'):
        config = config[8:]
    ev = evr.Eventor(name=os.path.basename(__file__), logging_level=logging.DEBUG, config=config, store=db, shared_db=True, import_module="examples.runly10")
    
    ev1s=ev.add_event('run_step1')
    ev2s=ev.add_event('run_step2')
    ev3s=ev.add_event('run_step3')
    
    s1=ev.add_step('s1', func=prog, kwargs={'progname': 'prog1'}, triggers={evr.StepStatus.success: (ev2s,),}) 
    s2=ev.add_step('s2', func=prog, kwargs={'progname': 'prog2'}, host='192.168.1.100', triggers={evr.StepStatus.success: (ev3s,), })
    s3=ev.add_step('s3', func=prog, kwargs={'progname': 'prog3'},)
    
    ev.add_assoc(ev1s, s1)
    ev.add_assoc(ev2s, s2)
    ev.add_assoc(ev3s, s3)

    ev.trigger_event(ev1s, 1)
    ev.run()
    ev.close()
    
if __name__ == '__main__':
    import multiprocessing as mp
    mp.freeze_support()
    mp.set_start_method('spawn')
    construct_and_run()

