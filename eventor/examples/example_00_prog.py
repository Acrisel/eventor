'''
Created on Sep 2, 2017

@author: arnon
'''

def prog(progname, logger):
    logger.info("doing what %s is doing" % progname)
    logger.info("EVENTOR_STEP_SEQUENCE: %s" % os.getenv("EVENTOR_STEP_SEQUENCE"))
    return progname
