import eventor as evr
import logging
import os
import time

appname = os.path.basename(__file__)


def prog(progname):
    logger = logging.getLogger(os.getenv("EVENTOR_LOGGER_NAME"))
    logger.info("doing what %s is doing" % progname)
    logger.info("EVENTOR_STEP_SEQUENCE: %s" % os.getenv("EVENTOR_STEP_SEQUENCE"))
    return progname


def build_flow(run_mode):
    ev = evr.Eventor(name=appname, run_mode=run_mode,)

    ev1s = ev.add_event('run_step1')
    ev2s = ev.add_event('run_step2')
    ev3s = ev.add_event('run_step3')

    s1 = ev.add_step('s1', func=prog, kwargs={'progname': 'prog1'}, triggers={evr.STEP_SUCCESS: (ev2s,)})
    s2 = ev.add_step('s2', func=prog, kwargs={'progname': 'prog2'}, triggers={evr.STEP_SUCCESS: (ev3s,)})
    s3 = ev.add_step('s3', func=prog, kwargs={'progname': 'prog3'},)

    ev.add_assoc(ev1s, s1, delay=0)
    ev.add_assoc(ev2s, s2, delay=10)
    ev.add_assoc(ev3s, s3, delay=10)

    ev.trigger_event(ev1s, 1)
    return ev


def construct_and_run():
    ev = build_flow(run_mode=evr.RUN_RESTART)
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
        ev = build_flow(run_mode=evr.RUN_CONTINUE)
        ev.run(max_loops=1)
        ev.close()


if __name__ == '__main__':
    import multiprocessing as mp
    mp.freeze_support()
    mp.set_start_method('spawn')
    construct_and_run()
