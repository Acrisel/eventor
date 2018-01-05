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


def prog(progname, success=True):
    logger = logging.getLogger(os.getenv("EVENTOR_LOGGER_NAME"))
    logger.info("{} doing what %s is doing: {}".format(progname, success))
    logger.info("EVENTOR_STEP_SEQUENCE: %s" % os.getenv("EVENTOR_STEP_SEQUENCE"))
    if not success:
        raise RuntimeError("Instigating failure.")
    return progname


def build_flow(run_mode, run_id=None, success=True):
    ev = evr.Eventor(name=appname, run_mode=run_mode, run_id=run_id,
                     config={'LOGGING':
                             {'logging_level': logging.INFO}})

    ev1s = ev.add_event('run_step1')
    ev2s = ev.add_event('run_step2')
    ev3s = ev.add_event('run_step3')

    kwprog1 = {'progname': 'prog1'}
    kwprog2 = {'progname': 'prog2', 'success': success}
    kwprog3 = {'progname': 'prog3'}

    s1 = ev.add_step('s1', func=prog, kwargs=kwprog1, triggers={evr.STEP_SUCCESS: (ev2s, )})
    s2 = ev.add_step('s2', func=prog, kwargs=kwprog2, triggers={evr.STEP_SUCCESS: (ev3s,)})
    s3 = ev.add_step('s3', func=prog, kwargs=kwprog3,)

    ev.add_assoc(ev1s, s1, delay=1)
    ev.add_assoc(ev2s, s2, delay=1)
    ev.add_assoc(ev3s, s3, delay=1)

    ev.trigger_event(ev1s, 1)
    return ev


def construct_and_run(recovery=True):
    # Instigate failure in run
    ev = build_flow(run_mode=evr.RUN_RESTART, success=not recovery,)
    run_id = ev.run_id
    ev.run()
    ev.close()

    if recovery:
        # recover run
        ev = build_flow(run_mode=evr.RUN_RECOVER, run_id=run_id)
        ev.run()
        ev.close()


if __name__ == '__main__':
    construct_and_run(recovery=True)
