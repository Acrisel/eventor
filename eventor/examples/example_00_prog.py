'''
Created on Sep 2, 2017

@author: arnon
'''

import os

def prog(progname, logger=None):
    func = print
    if logger:
        func=logger.info
    func("doing what %s is doing" % progname)
    func("EVENTOR_STEP_SEQUENCE: %s" % os.getenv("EVENTOR_STEP_SEQUENCE"))
    return progname
