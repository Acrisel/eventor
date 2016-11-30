=======
eventor
=======

Overview
========

**eventor** is a python programming tool facilitating build of event base sequencing of activities (function execution etc.)

Overview
========

decorator for methods that can be executed as a thread.  

example
-------

.. code-block:: python

    from acris import threaded
    from time import sleep

    class ThreadedExample(object):
        @threaded
        def proc(self, id_, num, stall):
            s=num
            while num > 0:
                print("%s: %s" % (id_, s))
                num -= 1
                s += stall
                sleep(stall)
            print("%s: %s" % (id_, s))  
            return s
          
    class RetVal(object):
        def __init__(self, name):
            self.name=name
        
        def __call__(self, retval):
            print(self.name, ':', retval)  

          
example output
--------------

.. code-block:: python

    te1=ThreadedExample().proc(1, 3, 1)
    te2=ThreadedExample().proc(2, 3, 5)
    
    te1.addCallback(RetVal('te1'))
    te2.addCallback(RetVal('te2'))

will produce:

.. code-block:: python

    1: 3
    2: 3
    1: 4
    1: 5
    1: 6
    te1 : 6
    2: 8
    2: 13
    2: 18
    te2 : 18

Singleton
=========

meta class that creates singleton footprint of classes inheriting from it.

example
-------

.. code-block:: python

    from acris import Singleton

    class Sequence(Singleton):
        step_id=0
    
        def __call__(self):
            step_id=self.step_id
            self.step_id += 1
            return step_id  

example output
--------------

.. code-block:: python
 
    A=Sequence()
    print('A', A())
    print('A', A())
    B=Sequence()
    print('B', B()) 

will produce:

.. code-block:: python

    A 0
    A 1
    B 2
    
Sequence
========

meta class to produce sequences.  Sequence allows creating different sequences using name tags.

example
-------

.. code-block:: python

    from acris import Sequence

    A=Sequence('A')
    print('A', A())
    print('A', A())
    B=Sequence('B')
    print('B', B()) 
    
    A=Sequence('A')
    print('A', A())
    print('A', A())
    B=Sequence('B')
    print('B', B()) 

example output
--------------

.. code-block:: python
     
    A 0
    A 1
    B 0
    A 2
    A 3
    B 1

TimedSizedRotatingHandler
=========================
	
Use TimedSizedRotatingHandler is combining TimedRotatingFileHandler with RotatingFileHandler.  
Usage as handler with logging is as defined in Python's logging how-to
	
example
-------

.. code-block:: python
	
	import logging
	
	# create logger
	logger = logging.getLogger('simple_example')
	logger.setLevel(logging.DEBUG)
	
	# create console handler and set level to debug
	ch = logging.TimedRotatingFileHandler()
	ch.setLevel(logging.DEBUG)
	
	# create formatter
	formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
	
	# add formatter to ch
	ch.setFormatter(formatter)
	
	# add ch to logger
	logger.addHandler(ch)
	
	# 'application' code
	logger.debug('debug message')
	logger.info('info message')
	logger.warn('warn message')
	logger.error('error message')
	logger.critical('critical message')	

MpLogger
========

Multiprocessor logger using QueueListener and QueueHandler
It uses TimedSizedRotatingHandler as its logging handler
	
example
-------

In main process:

.. code-block:: python
    
    import logging
    import time
	
    logger=logging.getLogger(__name__)
	
    mplogger=MpLogger(logging_level=logging.DEBUG)
    mplogger.start()
	
    logger.debug("starting sub processes")
    # running processes
    module_logger.debug("joining sub processes")
	
    mplogger.stop()
	
 Within individual process:

.. code-block:: python
	
    import logging
	
    logger=logging.getLogger(__name__)
    module_logger.debug("logging from sub process")
	
Data Types
==========

varies derivative of Python data types

MergeChainedDict
----------------

Similar to ChainedDict, but merged the keys and is actually derivative of dict.

.. code-block:: python

    a={1:11, 2:22}
    b={3:33, 4:44}
    c={1:55, 4:66}
    d=MergedChainedDict(c, b, a)
    print(d) 

Will output:

.. code-block:: python

	{1: 55, 2: 22, 3: 33, 4: 66}

   