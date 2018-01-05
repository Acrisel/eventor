'''
Created on Oct 18, 2016

@author: arnon
'''

import logging
import time
import os

mlogger = logging.getLogger(__name__)


def step1_create_data(outfile="source.txt"):
    mlogger = logging.getLogger(os.getenv("EVENTOR_LOGGER_NAME"))
    mlogger.info("starting writing into %s" % outfile)
    with open(outfile, mode='w') as ofile:
        for item in range(100):
            ofile.write(str(item) + '\n')
    mlogger.info("done writing into %s" % outfile)
    return True


def step2_multiple_data(infile="source.txt", outfile="multi.txt"):
    mlogger = logging.getLogger(os.getenv("EVENTOR_LOGGER_NAME"))
    mlogger.info("start processing from %s into %s" % (infile, outfile))
    with open(infile, mode='r') as ifile, open(outfile, mode='w') as ofile:
        for item in ifile:
            ofile.write(str(int(item) * 2) + '\n')
    mlogger.info("done writing into %s" % outfile)
    return True


def step3():
    mlogger = logging.getLogger(os.getenv("EVENTOR_LOGGER_NAME"))
    mlogger.info("start processing step 3")
    time.sleep(5)
    mlogger.info("done processing step 3")
    return True


def prog(appname, progname):
    mlogger = logging.getLogger(appname)
    mlogger.info("doing what %s is doing" % (progname,))
    mlogger.info("EVENTOR_STEP_SEQUENCE: %s" % (os.getenv("EVENTOR_STEP_SEQUENCE"),))
    return True

