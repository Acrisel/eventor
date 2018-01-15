#!/usr/bin/env python
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
logger = logging.getLogger(appname)


def prog(progname):
    logger = logging.getLogger(os.getenv("EVENTOR_LOGGER_NAME"))
    logger.info("doing what %s is doing" % progname)
    logger.info("EVENTOR_STEP_SEQUENCE: {}".format(
        os.getenv("EVENTOR_STEP_SEQUENCE")))
    return progname


class MyEnventor(evr.Eventor):
    def __init__(self, ):
        db = 'pgdb2'
        config = os.path.abspath('runly.conf')
        super().__init__(name=appname, config=config, config_tag='EVENTOR', store=db,)

    def construct_and_run(self):
        ev1s = self.add_event('run_step1')
        ev2s = self.add_event('run_step2')
        ev3s = self.add_event('run_step3')

        s1 = self.add_step('s1', func=prog, kwargs={'progname': 'prog1'},
                           triggers={evr.STEP_SUCCESS: (ev2s,), })
        s2 = self.add_step('s2', func=prog, kwargs={'progname': 'prog2'},
                           triggers={evr.STEP_SUCCESS: (ev3s,), })
        s3 = self.add_step('s3', func=prog, kwargs={'progname': 'prog3'},)

        self.add_assoc(ev1s, s1)
        self.add_assoc(ev2s, s2)
        self.add_assoc(ev3s, s3)

        self.trigger_event(ev1s, 1)
        self.run()
        self.close()


if __name__ == '__main__':
    import multiprocessing as mp
    mp.freeze_support()
    mp.set_start_method('spawn')
    myeventor = MyEnventor()
    myeventor.construct_and_run()
