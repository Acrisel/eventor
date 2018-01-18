
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
import time
from eventor.examples.run_types import prog

appname = os.path.basename(__file__)


def build_flow(run_mode):
    config = os.path.abspath('runly.conf')
    ev = evr.Eventor(name=appname, config=config, config_tag='EVENTOR')

    ev1s = ev.add_event('run_step1')
    ev2s = ev.add_event('run_step2')
    ev3s = ev.add_event('run_step3')

    s1 = ev.add_step('s1', func=prog, kwargs={'progname': 'prog1'},
                     triggers={evr.STEP_SUCCESS: (ev2s,)})
    s2 = ev.add_step('s2', func=prog, kwargs={'progname': 'prog2'},
                     triggers={evr.STEP_SUCCESS: (ev3s,)}, )
    s3 = ev.add_step('s3', func=prog, kwargs={'progname': 'prog3'},)

    ev.add_assoc(ev1s, s1, delay=0)
    ev.add_assoc(ev2s, s2, delay=10)
    ev.add_assoc(ev3s, s3, delay=10)

    ev.trigger_event(ev1s, 1)
    return ev


def construct_and_run_in_steps():
    ev = build_flow(run_mode=evr.RUN_RESTART)
    ev.run(max_loops=1)
    ev.close()

    for loop in range(4):
        delay = 5 if loop in [1, 2] else 15
        time.sleep(delay)
        ev = build_flow(run_mode=evr.RUN_CONTINUE)
        result = ev.run(max_loops=1)
        ev.close()
        print('Result: %s' % result)


def construct_and_run():
    ev = build_flow(run_mode=evr.RunMode.restart)
    result = ev.run()
    print('Result: %s' % result)


if __name__ == '__main__':
    import multiprocessing as mp
    mp.freeze_support()
    mp.set_start_method('spawn')
    construct_and_run()
