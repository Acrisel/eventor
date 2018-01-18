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
from acris import virtual_resource_pool as rp
from eventor.examples.run_types import Container


appname = os.path.basename(__file__)


def prog(progname):
    logger = logging.getLogger(os.getenv("EVENTOR_LOGGER_NAME"))
    logger.info("doing what %s is doing" % progname)
    return progname


ev = evr.Eventor(name=appname)  # config={'sleep_between_loops': 1}) # store=':memory:',

ev0first = ev.add_event('s0_start')
ev0next = ev.add_event('s0_next')
ev0end = ev.add_event('s0_end')
ev00first = ev.add_event('s0_00_start')
ev00next = ev.add_event('s0_s00_next')
ev00end = ev.add_event('s0_s00_end')
ev1s = ev.add_event('s0_s00_s1_start')
ev1success = ev.add_event('s0_s00_s1_success')
ev2s = ev.add_event('s0_s00_s2_start', expr=(ev1success,))
ev2success = ev.add_event('s0_s00_s2_success')
ev3s = ev.add_event('s0_s00_s3_start', expr=(ev2success,))


class StepResource(rp.Resource):
    pass


rp1o = rp.ResourcePool('RP1', resource_cls=StepResource,
                       policy={'resource_limit': 2})
rp1 = rp1o.load()
rp2o = rp.ResourcePool('RP2', resource_cls=StepResource,
                       policy={'resource_limit': 2})
rp2 = rp2o.load()

metaprog1 = Container(progname='s0', loop=[1, 2],
                               max_concurrent=2,
                               iter_triggers=(ev00first,),
                               end_triggers=(ev0end,))
s0first = ev.add_step('s0_start', func=metaprog1,
                      kwargs={'initial': True},
                      acquires=[(rp1, 1)],
                      releases=[],
                      config={'max_concurrent': -1,
                              'task_construct': 'invoke',
                              'pass_logger_to_task': True})
s0next = ev.add_step('s0_next', func=metaprog1,
                     config={'task_construct': 'invoke',
                             'pass_logger_to_task': True})
s0end = ev.add_step('s0_end', releases=[(rp1, 1), ],
                    config={'task_construct': 'invoke',
                            'pass_logger_to_task': True})

metaprog2 = Container(progname='00', loop=[1, 2],
                               max_concurrent=2, iter_triggers=(ev1s,),
                               end_triggers=(ev00end,))
s00first = ev.add_step('s0_s00_start', func=metaprog2,
                       kwargs={'initial': True, },
                       acquires=[(rp2, 1), ], releases=[],
                       config={'max_concurrent': -1,
                               'task_construct': 'invoke',
                               'pass_logger_to_task': True})
s00next = ev.add_step('s0_s00_next', func=metaprog2,
                      config={'task_construct': 'invoke',
                              'pass_logger_to_task': True})
s00end = ev.add_step('s0_s00_end', releases=[(rp2, 1)],
                     config={'task_construct': 'invoke',
                             'pass_logger_to_task': True},
                     triggers={evr.STEP_SUCCESS: (ev0next,)})

s1 = ev.add_step('s0.s00.s1', func=prog, kwargs={'progname': 'prog1'},
                 triggers={evr.StepStatus.success: (ev1success,), })
s2 = ev.add_step('s0.s00.s2', func=prog, kwargs={'progname': 'prog2'},
                 triggers={evr.STEP_SUCCESS: (ev2success,), })
s3 = ev.add_step('s0.s00.s3', func=prog, kwargs={'progname': 'prog3'},
                 triggers={evr.STEP_COMPLETE: (ev00next,), })

ev.add_assoc(ev0first, s0first)
ev.add_assoc(ev0next, s0next)
ev.add_assoc(ev0end, s0end)
ev.add_assoc(ev00first, s00first)
ev.add_assoc(ev00next, s00next)
ev.add_assoc(ev00end, s00end)
ev.add_assoc(ev1s, s1)
ev.add_assoc(ev2s, s2)
ev.add_assoc(ev3s, s3)

ev.trigger_event(ev0first)
ev.run()
ev.close()
