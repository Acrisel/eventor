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

appname = os.path.basename(__file__)


def prog(progname):
    mlogger = logging.getLogger(os.getenv("EVENTOR_LOGGER_NAME"))
    mlogger.info("doing what %s is doing" % progname)
    mlogger.info("EVENTOR_STEP_SEQUENCE: %s" % os.getenv("EVENTOR_STEP_SEQUENCE"))
    return progname


def build_flow(run_mode, run_id=None):
    ev = evr.Eventor(name=appname,
                     run_mode=run_mode,
                     run_id=run_id,
                     config={'LOGGING':
                             {'logging_level': logging.INFO}})

    ev1s = ev.add_event('run_step1')
    ev2s = ev.add_event('run_step2')
    ev3s = ev.add_event('run_step3')

    kwargs1 = {'progname': 'prog1'}
    kwargs2 = {'progname': 'prog1'}
    kwargs3 = {'progname': 'prog1'}

    s1 = ev.add_step('s1', func=prog, kwargs=kwargs1, triggers={evr.STEP_SUCCESS: (ev2s,)})
    s2 = ev.add_step('s2', func=prog, kwargs=kwargs2, triggers={evr.STEP_SUCCESS: (ev3s,)})
    s3 = ev.add_step('s3', func=prog, kwargs=kwargs3,)

    ev.add_assoc(ev1s, s1, delay=0)
    ev.add_assoc(ev2s, s2, delay=0)
    ev.add_assoc(ev3s, s3, delay=0)

    ev.trigger_event(ev1s, 1)
    return ev


if __name__ == '__main__':
    ev = build_flow(run_mode=evr.RUN_RESTART)
    ev.run()
