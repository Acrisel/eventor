#!/usr/bin/env python3
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
from eventor.examples.run_types import prog

logger = logging.getLogger(__file__)


def construct_and_run():
    # db = 'sqfile00'
    db = 'pgdb2'
    config = os.path.abspath('runly.conf')
    # because OSX adds /var -> /private/var
    if config.startswith('/private'):
        config = config[8:]
    # TODO: assume import_module is __file__ if not provided
    ev = evr.Eventor(name=os.path.basename(__file__), config=config, config_tag='EVENTOR', store=db)

    ev1s = ev.add_event('run_step1')
    ev2s = ev.add_event('run_step2')
    ev3s = ev.add_event('run_step3')

    host = 'ubuntud01_eventor'
    # host = 'ubuntud01'
    s1 = ev.add_step('s1', func=prog, kwargs={'progname': 'prog1'},
                     triggers={evr.STEP_SUCCESS: (ev2s,)})
    s2 = ev.add_step('s2', func=prog, kwargs={'progname': 'prog2'}, host=host,
                     triggers={evr.STEP_SUCCESS: (ev3s,)})
    s3 = ev.add_step('s3', func=prog, kwargs={'progname': 'prog3'})

    ev.add_assoc(ev1s, s1)
    ev.add_assoc(ev2s, s2)
    ev.add_assoc(ev3s, s3)

    ev.trigger_event(ev1s, '1')
    ev.run()
    # ev.close()


if __name__ == '__main__':
    # import multiprocessing as mp
    # mp.freeze_support()
    # mp.set_start_method('spawn')
    construct_and_run()
