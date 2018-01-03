import eventor as evr
import logging
import os
# from eventor_examples.program import prog

mlogger = logging.getLogger(__name__)


def prog(progname):
    mlogger.info("doing what %s is doing" % progname)
    mlogger.info("EVENTOR_STEP_SEQUENCE: %s" % os.getenv("EVENTOR_STEP_SEQUENCE"))
    return progname


def build_flow(run_mode, run_id=None):
    ev = evr.Eventor(run_mode=run_mode,
                     run_id=run_id,
                     config={'LOGGING':
                             {'logging_level': logging.INFO}})

    ev1s = ev.add_event('run_step1')
    ev2s = ev.add_event('run_step2')
    ev3s = ev.add_event('run_step3')

    s1 = ev.add_step('s1', func=prog, kwargs={'progname': 'prog1'}, triggers={evr.STEP_SUCCESS: (ev2s,)})
    s2 = ev.add_step('s2', func=prog, kwargs={'progname': 'prog2'}, triggers={evr.STEP_SUCCESS: (ev3s,)})
    s3 = ev.add_step('s3', func=prog, kwargs={'progname': 'prog3'},)

    ev.add_assoc(ev1s, s1, delay=0)
    ev.add_assoc(ev2s, s2, delay=0)
    ev.add_assoc(ev3s, s3, delay=0)

    ev.trigger_event(ev1s, 1)
    return ev


def construct_and_run():
    ev = build_flow(run_mode=evr.RUN_RESTART)
    ev.run()


if __name__ == '__main__':
    construct_and_run()
