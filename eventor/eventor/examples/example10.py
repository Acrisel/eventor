'''
Created on Aug 16, 2017

@author: arnon
'''

import eventor as evr
import logging
import time
from eventor.examples.run_types import prog

logger = logging.getLogger(__name__)


def build_flow(run_mode, run_id=None):
    ev = evr.Eventor(run_mode=run_mode, run_id=run_id)

    ev1s = ev.add_event('run_step1')
    ev2s = ev.add_event('run_step2')
    ev3s = ev.add_event('run_step3')

    s1 = ev.add_step('s1', func=prog, kwargs={'progname': 'prog1'},
                     triggers={evr.StepStatus.success: (ev2s,)})
    s2 = ev.add_step('s2', func=prog, kwargs={'progname': 'prog2'},
                     triggers={evr.StepStatus.success: (ev3s,)})
    s3 = ev.add_step('s3', func=prog, kwargs={'progname': 'prog3'},)

    ev.add_assoc(ev1s, s1, delay=0)
    ev.add_assoc(ev2s, s2, delay=5)
    ev.add_assoc(ev3s, s3, delay=5)

    ev.trigger_event(ev1s, 1)
    return ev


def construct_and_run():
    ev = build_flow(run_mode=evr.RUN_RESTART)
    run_id = ev.run_id
    ev.run(max_loops=1)
    ev.close()

    loop = 0
    while True:
        total_todos, _ = ev.count_todos()
        if total_todos == 0:
            break

        loop += 1
        delay = 5 if loop % 4 != 0 else 15
        time.sleep(delay)
        ev = build_flow(run_mode=evr.RUN_CONTINUE, run_id=run_id)
        ev.run(max_loops=1)
        ev.close()


if __name__ == '__main__':
    construct_and_run()
