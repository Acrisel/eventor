'''
Created on Oct 31, 2016

@author: arnon
'''

import logging

mlogger = logging.getLogger(__name__)


class Delay(object):
    """Event object used to reuse in user program.

        Event objects are created by Eventor.add_event programming interface or by
        the mechanism itself.

        Attributes:
            N/A

        Methods:
            db_write: write event to db file

    """

    def __init__(self, delay_id, func, seconds, event):
        self.func = func
        self.seconds = seconds
        self.delay_id = delay_id  # get_event_id(
        self.event = event

    def __repr__(self):
        return "Delay(%s, %s)" % (self.delay_id, self.seconds)

    def __str__(self):
        return repr(self)


if __name__ == '__main__':
    e1 = Delay('E1')
    e2 = Delay('E2')
    e3 = Delay('E3')
    e4 = Delay('E4')
