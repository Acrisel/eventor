
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
from acris import virtual_resource_pool as vrp

appname = os.path.basename(__file__)


class StepResource(vrp.Resource):
    pass


def prog(progname):
    logger = logging.getLogger(os.getenv("EVENTOR_LOGGER_NAME"))
    logger.info("doing what %s is doing" % progname)
    logger.info("EVENTOR_STEP_SEQUENCE: %s" % os.getenv("EVENTOR_STEP_SEQUENCE"))
    return progname


rp1 = vrp.ResourcePool('rp1', resource_cls=StepResource, policy={'resource_limit': 2, }).load()

# ev=evr.Eventor(store=':memory:', logging_level=logging.INFO)
config = os.path.abspath('runly.conf')
ev = evr.Eventor(name=appname, config=config, config_tag='EVENTOR')

ev1s = ev.add_event('run_step1')
ev2s = ev.add_event('run_step2')
ev3s = ev.add_event('run_step3')

s1 = ev.add_step('s1', func=prog, kwargs={'progname': 'prog1'},
                 triggers={evr.STEP_SUCCESS: (ev2s,)},
                 acquires=[(rp1, 1)])
s2 = ev.add_step('s2', func=prog, kwargs={'progname': 'prog2'},
                 triggers={evr.STEP_SUCCESS: (ev3s,)},
                 acquires=[(rp1, 1)])
s3 = ev.add_step('s3', func=prog, kwargs={'progname': 'prog3'},
                 acquires=[(rp1, 1)])

ev.add_assoc(ev1s, s1)
ev.add_assoc(ev2s, s2)
ev.add_assoc(ev3s, s3)

ev.trigger_event(ev1s, 1)
ev.run()
ev.close()
