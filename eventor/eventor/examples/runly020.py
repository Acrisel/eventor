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
import eventor.examples.program as prog
import os

appname = os.path.basename(__file__)
ev = evr.Eventor(name=appname,
                 run_mode=evr.RUN_RESTART,
                 config_tag='EVENTOR',
                 config={'EVENTOR':
                         {'shared_db': False,  # will be override to True by Eventor.
                          'LOGGING':
                          {'logging_level': logging.INFO}}})


ev1s = ev.add_event('run_step1')
ev1d = ev.add_event('done_step1')
ev2s = ev.add_event('run_step2')
ev2d = ev.add_event('done_step2')
ev3s = ev.add_event('run_step3', expr=(ev1d, ev2d))

s1 = ev.add_step('s1', func=prog.step1_create_data,
                 kwargs={'outfile': 'source.txt'},
                 triggers={evr.STEP_COMPLETE: (ev1d, ev2s,)},
                 recovery={evr.STEP_FAILURE: evr.STEP_RERUN,
                           evr.STEP_SUCCESS: evr.STEP_SKIP})
s2 = ev.add_step('s2', prog.step2_multiple_data,
                 kwargs={},
                 triggers={evr.STEP_COMPLETE: (ev2d, ), })
s3 = ev.add_step('s3', prog.step3, kwargs={})

ev.add_assoc(ev1s, s1)
ev.add_assoc(ev2s, s2)
ev.add_assoc(ev3s, s3)

ev.trigger_event(ev1s, 3)
ev.run()
ev.close()
