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
import eventor_examples.program as prog

logger = logging.getLogger(__name__)

logger.setLevel(logging.INFO)

ev = evr.Eventor(run_mode=evr.RunMode.restart, config={'EVENTOR': {'shared_db': False, 'LOGGING': {'logging_level': logging.DEBUG}}}, config_tag='EVENTOR')
#ev = evr.Eventor(run_mode=evr.EVR_RESTART, config={'shared_db': True, 'LOGGING': {'logging_level': logging.INFO}})

ev1s = ev.add_event('run_step1')
ev1d = ev.add_event('done_step1')
ev2s = ev.add_event('run_step2')
ev2d = ev.add_event('done_step2')
ev3s = ev.add_event('run_step3', expr=(ev1d, ev2d))

s1 = ev.add_step('s1', func=prog.step1_create_data, kwargs={'outfile': 'source.txt'},
                 triggers={evr.STP_COMPLETE: (ev1d, ev2s,)},
                 recovery={evr.STP_FAILURE: evr.STP_RERUN,
                           evr.STP_SUCCESS: evr.STP_SKIP})
s2 = ev.add_step('s2', prog.step2_multiple_data, triggers={evr.STP_COMPLETE: (ev2d, ), })
s3 = ev.add_step('s3', prog.step3,)

ev.add_assoc(ev1s, s1)
ev.add_assoc(ev2s, s2)
ev.add_assoc(ev3s, s3)

ev.trigger_event(ev1s, 3)
ev.run()
ev.close()
