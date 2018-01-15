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
import collections
import os

appname = os.path.basename(__file__)


class IterGen(object):
    def __init__(self, level):
        self.level = level

    def __call__(self):
        return (x for x in self.level)


def prog(progname):
    logger = logging.getLogger(os.getenv("EVENTOR_LOGGER_NAME"))
    logger.info("doing what %s is doing" % progname)
    return progname


class MetaProg(object):
    def __init__(self, ev, progname, loop=[1], triggers=()):
        self.ev = ev
        self.progname = progname
        self.triggers = triggers
        if isinstance(loop, collections.Iterable):
            loop = IterGen(loop)
        self.loop = loop
        self.loop_index = 0

    def __call__(self, initial=False):
        if initial:
            self.iter = self.loop()

        try:
            item = next(self.iter)
        except StopIteration:
            item = None
        if item:
            self.loop_index += 1
            for trigger in self.triggers:
                ev.remote_trigger_event(trigger, self.loop_index,)
        return True


ev = evr.Eventor(name=appname, config_tag='EVENTOR',
                 config={'EVENTOR': {'shared_db': True,
                                     'LOGGING': {'logging_level': logging.DEBUG}}})

ev0first = ev.add_event('run_s0first')
ev0next = ev.add_event('run_s0next')
ev1s = ev.add_event('run_s1')
ev2s = ev.add_event('run_s2')
ev3s = ev.add_event('run_s3')

metaprog = MetaProg(ev=ev, progname='', loop=[1, 2], triggers=(ev1s, ))
s0first = ev.add_step('s0first', func=metaprog, kwargs={'initial': True},
                      config={'task_construct': evr.Invoke})
s0next = ev.add_step('s0next', func=metaprog,
                     config={'task_construct': evr.Invoke})

s1 = ev.add_step('s1', func=prog, kwargs={'progname': 'prog1'},
                 triggers={evr.STEP_SUCCESS: (ev2s, )})
s2 = ev.add_step('s2', func=prog, kwargs={'progname': 'prog2'},
                 triggers={evr.STEP_SUCCESS: (ev3s, )})
s3 = ev.add_step('s3', func=prog, kwargs={'progname': 'prog3'},
                 triggers={evr.STEP_SUCCESS: (ev0next, )})

ev.add_assoc(ev0first, s0first)
ev.add_assoc(ev0next, s0next)
ev.add_assoc(ev1s, s1)
ev.add_assoc(ev2s, s2)
ev.add_assoc(ev3s, s3)

ev.trigger_event(ev0first)
ev.run()
ev.close()
