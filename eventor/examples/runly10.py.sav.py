
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

start_event= s1= s2= s3=None

def prog(progname):
    logger.info("doing what %s is doing" % progname)
    logger.info("EVENTOR_STEP_SEQUENCE: %s" % os.getenv("EVENTOR_STEP_SEQUENCE"))
    return progname

def construct_client(run_id='', scope=None):
    global start_event, s1, s2, s3
    ev = evr.Eventor(logging_level=logging.DEBUG, run_id=run_id, config='example00.conf', store='pgdb1', shared_db=True)
    
    start_event = ev1s = ev.add_event('run_step1')
    ev2s = ev.add_event('run_step2')
    ev3s = ev.add_event('run_step3')
    
    s1 = ev.add_step('s1', func=prog, kwargs={'progname': 'prog1'}, triggers={evr.StepStatus.success: (ev2s,),}) 
    s2 = ev.add_step('s2', func=prog, kwargs={'progname': 'prog2'}, triggers={evr.StepStatus.success: (ev3s,),})
    s3 = ev.add_step('s3', func=prog, kwargs={'progname': 'prog3'},)
    
    ev.add_assoc(ev1s, s1)
    ev.add_assoc(ev2s, s2)
    ev.add_assoc(ev3s, s3)
    
    if scope is not None and len(scope) >0:
        ev.add_scope(scope)
    
    return ev

def construct_server():
    global start_event, s1, s2, s3
    #run_id = evr.get_unique_run_id()
    ev = construct_client()
    ev.add_scope([s1, s3])
    ev.trigger_event(start_event, 1)
    return ev
    
def submit_client(run_id):
    sshcmd("192.168.1.97", "%s --run_id %s" % (__file__, run_id), user="arnon", check=False)
    
if __name__ == '__main__':
    import multiprocessing as mp
    import argparse
    mp.freeze_support()
    mp.set_start_method('spawn')

    parser = argparse.ArgumentParser(description="""runs Eventor program""")
    parser.add_argument('--run-id', type=str, default='', dest='run_id', help='run_id to run')
    args=parser.parse_args()
    
    from examples.sshcmd import sshcmd
    from threading import Thread
    if not args.run_id:
        ev = construct_server()
        run_id = ev.run_id
        t=Thread(target=submit_client, args=(run_id,))
        t.start()
        ev.run()
        ev.close()
        t.join()
    else:
        ev=construct_client(args.run_id, scope=[s2])
        ev.run()
        ev.close()
