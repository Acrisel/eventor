import eventor as evr
import logging
import os

logger = logging.getLogger(__name__)


def prog(progname, success=True):
    logger.info("{} doing what %s is doing: {}".format(progname, success))
    logger.info("EVENTOR_STEP_SEQUENCE: %s" % os.getenv("EVENTOR_STEP_SEQUENCE"))
    if not success:
        raise RuntimeError("Instigating failure.")
    return progname


def build_flow(run_mode, run_id=None, success=True):
    ev = evr.Eventor(run_mode=run_mode, run_id=run_id)

    ev1s = ev.add_event('run_step1')
    ev2s = ev.add_event('run_step2')
    ev3s = ev.add_event('run_step3')

    kwprog1 = {'progname': 'prog1'}
    kwprog2 = {'progname': 'prog2', 'success': success}
    kwprog3 = {'progname': 'prog3'}

    s1 = ev.add_step('s1', func=prog, kwargs=kwprog1, triggers={evr.STEP_SUCCESS: (ev2s, )})
    s2 = ev.add_step('s2', func=prog, kwargs=kwprog2, triggers={evr.STEP_SUCCESS: (ev3s,)})
    s3 = ev.add_step('s3', func=prog, kwargs=kwprog3,)

    ev.add_assoc(ev1s, s1, delay=0)
    ev.add_assoc(ev2s, s2, delay=10)
    ev.add_assoc(ev3s, s3, delay=10)

    ev.trigger_event(ev1s, 1)
    return ev


def construct_and_run():
    # Instigate failure in run
    ev = build_flow(run_mode=evr.RUN_RESTART, success=False,)
    run_id = ev.run_id
    ev.run()
    ev.close()

    # recover run
    ev = build_flow(run_mode=evr.RUN_RECOVER, run_id=run_id)
    ev.run()
    ev.close()

    '''
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
        '''


if __name__ == '__main__':
    construct_and_run()
