'''
Created on Oct 18, 2016

@author: arnon
'''

import logging
import time

module_logger = logging.getLogger(__name__)


def step1_create_data(outfile="source.txt"):
    module_logger.info("starting writing into %s" % outfile)
    with open(outfile, mode='w') as ofile:
        for item in range(100):
            ofile.write(str(item) + '\n')
    module_logger.info("done writing into %s" % outfile)
    return True


def step2_multiple_data(infile="source.txt", outfile="multi.txt"):
    module_logger.info("start processing from %s into %s" % (infile, outfile))
    with open(infile, mode='r') as ifile, open(outfile, mode='w') as ofile:
        for item in ifile:
            ofile.write(str(int(item)*2)+'\n')
    module_logger.info("done writing into %s" % outfile)
    return True


def step3():
    module_logger.info("start processing step 3")
    time.sleep(5)
    module_logger.info("done processing step 3")
    return True
