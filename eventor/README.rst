=======
Eventor
=======

--------------------------------------------------------
Programming interface to use events to synchronize tasks
--------------------------------------------------------

.. contents:: Table of Contents
   :depth: 1

Overview
========

    *Eventor* provides programmer with interface to create events, steps and associations of these artifacts with to create a flow.
    
    It would be easier to show an example. 

Simple Example
--------------
    
    .. code-block:: python
        :number-lines:
        
        import eventor as evr
        import logging
        
        logger=logging.getLogger(__name__)
        
        def prog(progname):
            logger.info("doing what %s is doing" % progname)
            return progname
        
        ev=evr.Eventor(store=':memory:')
        
        ev1s=ev.add_event('run_step1')
        ev2s=ev.add_event('run_step2')
        ev3s=ev.add_event('run_step3')
        
        s1=ev.add_step('s1', func=prog, kwargs={'progname': 'prog1'}, 
                       triggers={evr.StepStatus.success: (ev2s,),}) 
        s2=ev.add_step('s2', func=prog, kwargs={'progname': 'prog2'}, 
                       triggers={evr.StepStatus.success: (ev3s,), })
        s3=ev.add_step('s3', func=prog, kwargs={'progname': 'prog3'},)
        
        ev.add_assoc(ev1s, s1)
        ev.add_assoc(ev2s, s2)
        ev.add_assoc(ev3s, s3)
        
        ev.trigger_event(ev1s, 1)
        ev()
        
Example Output
--------------

    The above example with provide the following log output.
              
    .. code::
    
        [ 2016-11-30 10:07:48,572 ][ INFO ][ Eventor store file: :memory: ][ main.__init__ ]
        [ 2016-11-30 10:07:48,612 ][ INFO ][ Running step s1[1] ][ main.task_wrapper ]
        [ 2016-11-30 10:07:48,612 ][ INFO ][ Step completed s1[1], status: success, result 'prog1' ][ main.task_wrapper ]
        [ 2016-11-30 10:07:50,649 ][ INFO ][ Running step s2[1] ][ main.task_wrapper ]
        [ 2016-11-30 10:07:50,649 ][ INFO ][ Step completed s2[1], status: success, result 'prog2' ][ main.task_wrapper ]
        [ 2016-11-30 10:07:52,688 ][ INFO ][ Running step s3[1] ][ main.task_wrapper ]
        [ 2016-11-30 10:07:52,689 ][ INFO ][ Step completed s3[1], status: success, result 'prog3' ][ main.task_wrapper ]
        [ 2016-11-30 10:07:53,700 ][ INFO ][ Processing finished with: success ][ main.loop_session_start ]

Example Highlights
------------------

    *Eventor* (line 10) defines an in-memory eventor object.  Note that in-memory eventors are none recoverable.
    
    *add_event* (e.g., line 12) adds an event named **run_step1** to the respective eventor object.
    
    *add_step* (e.g., line 16) adds step **s1** which when triggered would run predefined function **prog** with key words parameters **progname='prog1'**.
    Additionally, when step would end, if successful, it would trigger event **evs2**
    
    *add_assoc* (e.g., line 22) links event **evs1** and step **s1**.
    
    *trigger_event* (line 26) marks event **evs1**; when triggers, event is associated with sequence.  This would allow multiple invocation.
    
    *ev()* (line 27) invoke eventor process that would looks for triggers and tasks to act upon.  It ends when there is nothing to do.
 
Program Run File
================
 
    One important artifact used in Eventor is program's runner file.  Runner file database (sqlite) will be created at execution, if not directed otherwise, at the location of the run (UNIX's pwd).  
    This file contains information on tasks and triggers that are used in the run and in recovery.
 
Eventor Interface
=================

Eventor Class Initiator
-----------------------

    .. code-block:: python
        
        Eventor(name='', store='', run_mode=RunMode.restart, recovery_run=None, logging_level=logging.INFO, config={})

Args
````

    name: string id for Eventor object initiated
    
    store: path to file that would store runnable (sqlite) information; if ':memory:' is used, in-memory temporary 
        storage will be created.  If not provided, calling module path and name will be used 
        with db extension instead of py
    
    run_mode: can be either *RunMode.restart* (default) or *RunMode.recover*; in restart, new instance or the run 
        will be created. In recovery, 
              
    recovery_run: if *RunMode.recover* is used, *recovery_run* will indicate specific instance of previously recovery 
        run that would be executed.If not provided, latest run would be used.
          
    config: keyword dictionary of default configurations.  Available keywords and their default values:
    
        +---------------------+------------+--------------------------------------------------+
        | Name                | Default    | Description                                      |
        |                     | Value      |                                                  |
        +=====================+============+==================================================+
        | workdir             | /tmp       | place to create necessry artifacts (not in use)  |
        +---------------------+------------+--------------------------------------------------+
        | logdir              | /tmp       | place to create debug and error log files        |
        +---------------------+------------+--------------------------------------------------+
        | task_construct      | mp.Process | method to use for execution of steps             |
        +---------------------+------------+--------------------------------------------------+
        | max_concurrent      | 1          | maximum concurrent processing, if value <1, no   |
        |                     |            | limit will be pose                               |
        +---------------------+------------+--------------------------------------------------+
        | stop_on_exception   | True       | if an exception occurs in a step, stop           |
        |                     |            | all processes.  If True, new processes will not  |
        |                     |            | start.  But running processes will be permitted  |
        |                     |            | to finish                                        |
        +---------------------+------------+--------------------------------------------------+
        | sleep_between_loops | 1          | seconds to sleep between iteration of checking   |
        |                     |            | triggers and tasks                               |
        +---------------------+------------+--------------------------------------------------+
          
Eventor *add_event* method
--------------------------

    .. code-block:: python
        
        add_event(name, expr=None)

Args
````

    *name*: string unique id for event 
    
    *expr*: logical expression 'sqlalchemy' style to automatically raise this expresion.
        syntax: 
        
        .. code ::
            
            expr : (expr, expr, ...)
                 | or_(expr, expr, ...) 
                 | event
                 
        - if expression is of the first style, logical *and* will apply.
        - the second expression will apply logical *or*.
        - the basic atom in expression is *even* which is the product of *add_event*.
        
Returns
```````

    Event object to use in other *add_event* expressions, *add_assoc* methods, or with *add_step* triggers.
    
Eventor *add_step* method
-------------------------

    .. code-block:: python
        
        add_step(name, func, args=(), kwargs={}, triggers={}, acquires=[], releases=None, recovery={}, config={})

Args
````

    *name*: string unique id for step 
    
    *func*: callable object that would be call at time if step execution
    
    *args*: tuple of values that will be passed to *func* at calling
    
    *kwargs*: keywords arguments that will be pust to *func* at calling
    
    *triggers*: mapping of step statuses to set of events to be triggered as in the following table:
    
        +--------------------+-------------------------------------------+
        | status             | description                               |
        +====================+===========================================+
        | StepState.ready    | set when task is ready to run (triggered) |
        +--------------------+-------------------------------------------+
        | StepState.active   | set when task is running                  |
        +--------------------+-------------------------------------------+
        | StepState.success  | set when task is successful               |
        +--------------------+-------------------------------------------+
        | StepState.failure  | set when task fails                       |
        +--------------------+-------------------------------------------+
        | StepState.complete | stands for success or failure of task     |
        +--------------------+-------------------------------------------+
        
    *acquires*: list of tuples of resource pool and amount of resources to acquire before starting. 
    
    *releases*: list of tuples of resources pool and amount of resources to release once completed. If None, defaults to *acquires*.  If set to empty list, none of the acquired resources would be released.
        
    *recovery*: mapping of state status to how step should be handled in recovery:
    
        +----------------------+------------------+------------------------------------------------------+
        | status               | default          | description                                          |
        +======================+==================+======================================================+
        | StateStatus.ready    | StepReplay.rerun | if in recovery and previous status is ready, rerun   |
        +----------------------+------------------+------------------------------------------------------+
        | StateStatus.active   | StepReplay.rerun | if in recovery and previous status is active, rerun  |
        +----------------------+------------------+------------------------------------------------------+
        | StateStatus.failure  | StepReplay.rerun | if in recovery and previous status is failure, rerun |
        +----------------------+------------------+------------------------------------------------------+
        | StateStatus.success  | StepReplay.skip  | if in recovery and previous status is success, skip  |
        +----------------------+------------------+------------------------------------------------------+
    
    *config*: keywords mapping overrides for step configuration.
    
        +-------------------+------------------+---------------------------------------+
        | name              | default          | description                           |
        +===================+==================+=======================================+
        | stop_on_exception | True             | stop flow if step ends with Exception | 
        +-------------------+------------------+---------------------------------------+
    
Returns
```````

    Step object to use in add_assoc method.
    
Eventor *add_assoc* method
--------------------------

    .. code-block:: python
        
        add_assoc(event, *assocs, delay=0)

Args
````

    *event*: event objects as provided by add_event.
    
    *assocs*: list of associations objects.  List is composed from either events (as returned by add_event) or steps (as returned by add_step)
    
    *delay*: seconds to wait, once event is triggered, before engaging its associations
    
Returns
```````

    N/A
    
Eventor *trigger_event* method
------------------------------

    .. code-block:: python
        
        trigger_event(event, sequence=None)

Args
````

    *event*: event objects as provided by add_event.
    
    *sequence*: unique association of triggered event.  Event can be triggered only once per sequence.  All derivative triggers will carry the same sequence.
    
Returns
```````

    N/A
    
Eventor *__call__* method
-------------------------

    .. code-block:: python
    
        eventor(max_loops=-1)
        
when calling eventor, information is built and loops evaluating events and task starts are executed.  
In each loop events are raised and tasks are performed.  max_loops parameters allows control of how many
loops to execute.

In simple example, **ev()** engage Eventor's __call__() method.
        
Args
````

    *max_loops*: max_loops: number of loops to run.  If positive, limits number of loops.
                 defaults to negative, which would run loops until there are no events to raise and
                 no task to run. 
                 
Returns
```````

    If there was a failure that was not followed by event triggered, result will be False.


Recovery
========

    When running in recovery, unless indicated otherwise, latest run (initial or recovery) would be used.
    
    Note that when running a program with the intent to use its recovery capabilities, in-memory store **cannot** be use.
    Instead, physical storage must be used.
    
    Here is an example for recovery program and run.
    
Recovery Example
----------------

    .. code-block:: python
        :number-lines:
    
        import eventor as evr
        import logging
        import math

        logger=logging.getLogger(__name__)

        logger.setLevel(logging.DEBUG)

        def square(x):
            y=x*x
            logger.info("Square of %s is %s" % (x, y))
            return y

        def square_root(x):
            y=math.sqrt(x)
            logger.info("Square root of %s is %s" % (x, y))
            return y

        def divide(x,y):
            z=x/y
            logger.info("dividing %s by %s is %s" % (x, y, z))
            return z

        def build_flow(run_mode=evr.RunMode.restart, param=9):
            ev=evr.Eventor(run_mode=run_mode, logging_level=logging.INFO)
    
            ev1s=ev.add_event('run_step1')
            ev1d=ev.add_event('done_step1')
            ev2s=ev.add_event('run_step2')
            ev2d=ev.add_event('done_step2')
            ev3s=ev.add_event('run_step3', expr=(ev1d, ev2d)) 
    
            s1=ev.add_step('s1', func=square, kwargs={'x': 3}, 
                           triggers={evr.StepStatus.success: (ev1d, ev2s,)},) 
            s2=ev.add_step('s2', square_root, kwargs={'x': param}, triggers={evr.StepStatus.success: (ev2d,), },
                           recovery={evr.StepStatus.failure: evr.StepReplay.rerun, 
                                     evr.StepStatus.success: evr.StepReplay.skip})
            s3=ev.add_step('s3', divide, kwargs={'x': 9, 'y': 3},)
    
            ev.add_assoc(ev1s, s1)
            ev.add_assoc(ev2s, s2)
            ev.add_assoc(ev3s, s3)
            ev.trigger_event(ev1s, 3)    
            return ev

        # start regularly; it would fail in step 2
        ev=build_eventor(param=-9)
        ev()

        # rerun in recovery
        ev=build_eventor(evr.RunMode.recover, param=9)
        ev()

Example Output
--------------

    .. code:: 
        :number-lines:

        [ 2016-12-07 08:37:53,541 ][ INFO ][ Eventor store file: /eventor/example/runly03.run.db ]
        [ 2016-12-07 08:37:53,586 ][ INFO ][ [ Step s1/3 ] Trying to run ]
        [ 2016-12-07 08:37:53,588 ][ INFO ][ Square of 3 is 9 ]
        [ 2016-12-07 08:37:53,588 ][ INFO ][ [ Step s1/3 ] Completed, status: TaskStatus.success ]
        [ 2016-12-07 08:37:55,644 ][ INFO ][ [ Step s2/3 ] Trying to run ]
        [ 2016-12-07 08:37:55,647 ][ INFO ][ [ Step s2/3 ] Completed, status: TaskStatus.failure ]
        [ 2016-12-07 08:37:56,663 ][ ERROR ][ Exception in run_action: 
            <Task(id='2', step_id='s2', sequence='3', recovery='0', pid='8112', status='TaskStatus.failure', created='2016-12-07 14:37:55.625870', updated='2016-12-07 14:37:55.633819')> ]
        [ 2016-12-07 08:37:56,663 ][ ERROR ][ ValueError('math domain error',) ]
        [ 2016-12-07 08:37:56,663 ][ ERROR ][ File "/sand/eventor/eventor/main.py", line 62, in task_wrapper
                    result=step(seq_path=task.sequence)
        File "/sand/eventor/eventor/step.py", line 82, in __call__
                    result=func(*func_args, **func_kwargs)
        File "/eventor/example/runly03.py", line 66, in square_root
                y=math.sqrt(x) ]
        [ 2016-12-07 08:37:56,663 ][ INFO ][ Stopping running processes ]
        [ 2016-12-07 08:37:56,667 ][ INFO ][ Processing finished with: failure ]
        [ 2016-12-07 08:37:56,670 ][ INFO ][ Eventor store file: /eventor/example/runly03.run.db ]
        [ 2016-12-07 08:37:57,736 ][ INFO ][ [ Step s2/3 ] Trying to run ]
        [ 2016-12-07 08:37:57,739 ][ INFO ][ Square root of 9 is 3.0 ]
        [ 2016-12-07 08:37:57,739 ][ INFO ][ [ Step s2/3 ] Completed, status: TaskStatus.success ]
        [ 2016-12-07 08:38:00,798 ][ INFO ][ [ Step s3/3 ] Trying to run ]
        [ 2016-12-07 08:38:00,800 ][ INFO ][ dividing 9 by 3 is 3.0 ]
        [ 2016-12-07 08:38:00,800 ][ INFO ][ [ Step s3/3 ] Completed, status: TaskStatus.success ]
        [ 2016-12-07 08:38:01,824 ][ INFO ][ Processing finished with: success ]

Example Highlights
------------------
    
    The function *build_flow* (code line 24) build an eventor flow using three functions defined in advance.  
    Since no specific store is provided in Eventor instantiation, a default runner store is assigned (code line 25). 
    In this build, step *s2* (lines 30-35) is being set with recovery directives.  
    
    The first build and run is done in lines 47-48.  In this run, a parameter that would cause the second 
    step to fail is being passed.  As a result, flow fails.  Output lines 1-17 is associated with the first run.  
    
    The second build and run is then initiated.  In this run, parameter is set to a value that would pass 
    step *s2* and run mode is set to recovery (code lines 51-52). Eventor skips successful steps and start 
    executing from failed steps onwards.  Output lines 18-25 reflects successful second run.
        
Delayed Associations
====================

    There are situations in which it is desire to hold off activating a task.  This behavior is captured in Eventor as a delayed association.
    
    Associations can be made delayed.  Assuming source event is associated to target event with time delay.  When source event is triggered, Eventor will wait time delay seconds before triggering target event.
    
    In such situations, it sometimes desire to run Eventor engine in specific period on a time line instead of continuously.  For example, if Eventor is synchronizing activities that has 6 hours association delay.  Instead of running Eventor continuously, it can be set to run every 5 minutes, and save computing resources on the side.
    
    With *delayed associations*, Eventor can run in *continue* run mode (*RunMode.continue_*).  When running in *continue*, Eventor will pick up from where it left last run.
    
    The following example present *delayed association* with *continue* run mode.
    

Delay Example
-------------

    .. code:: 
        :number-lines:
        
        import eventor as evr
        import logging
        import os
        import time

        logger=logging.getLogger(__name__)

        def prog(progname):
            logger.info("doing what %s is doing" % progname)
            logger.info("EVENTOR_STEP_SEQUENCE: %s" % os.getenv("EVENTOR_STEP_SEQUENCE"))
            return progname

        def build_flow(run_mode):
            ev=evr.Eventor(run_mode=run_mode, logging_level=logging.INFO)
    
            ev1s=ev.add_event('run_step1')
            ev2s=ev.add_event('run_step2')
            ev3s=ev.add_event('run_step3')
    
            s1=ev.add_step('s1', func=prog, kwargs={'progname': 'prog1'}, triggers={evr.StepStatus.success: (ev2s,),}) 
            s2=ev.add_step('s2', func=prog, kwargs={'progname': 'prog2'}, triggers={evr.StepStatus.success: (ev3s,), })
            s3=ev.add_step('s3', func=prog, kwargs={'progname': 'prog3'},)
    
            ev.add_assoc(ev1s, s1, delay=0)
            ev.add_assoc(ev2s, s2, delay=10)
            ev.add_assoc(ev3s, s3, delay=10)
    
            ev.trigger_event(ev1s, 1)
            return ev

        ev=build_flow(run_mode=evr.RunMode.restart)
        ev(max_loops=1)

        for _ in range(4):
            delay=5 if loop in [1,2] else 15
            time.sleep(delay)
            ev=build_flow(run_mode=evr.RunMode.continue_)
            ev(max_loops=1)
            
Example Output
--------------

    .. code:: 
        :number-lines:

        [ 2017-01-30,14:06:33.660379 ][ INFO    ][ Eventor store file: /eventor/example/runly08.run.db ]
        [ 2017-01-30,14:06:33.713544 ][ INFO    ][ [ Step s1/1 ] Trying to run ]
        [ 2017-01-30,14:06:33.715248 ][ INFO    ][ doing what prog1 is doing ]
        [ 2017-01-30,14:06:33.715441 ][ INFO    ][ EVENTOR_STEP_SEQUENCE: 1 ]
        [ 2017-01-30,14:06:33.715624 ][ INFO    ][ [ Step s1/1 ] Completed, status: TaskStatus.success ]
        [ 2017-01-30,14:06:33.985704 ][ INFO    ][ Processing finished with: success ]
        [ 2017-01-30,14:06:48.990540 ][ INFO    ][ Eventor store file: /eventor/example/runly08.run.db ]
        [ 2017-01-30,14:06:49.029116 ][ INFO    ][ [ Step s2/1 ] Trying to run ]
        [ 2017-01-30,14:06:49.032463 ][ INFO    ][ doing what prog2 is doing ]
        [ 2017-01-30,14:06:49.032766 ][ INFO    ][ EVENTOR_STEP_SEQUENCE: 1 ]
        [ 2017-01-30,14:06:49.033149 ][ INFO    ][ [ Step s2/1 ] Completed, status: TaskStatus.success ]
        [ 2017-01-30,14:06:49.296886 ][ INFO    ][ Processing finished with: success ]
        [ 2017-01-30,14:06:54.305313 ][ INFO    ][ Eventor store file: /eventor/example/runly08.run.db ]
        [ 2017-01-30,14:06:54.320393 ][ INFO    ][ Processing finished with: success ]
        [ 2017-01-30,14:06:59.327107 ][ INFO    ][ Eventor store file: /eventor/example/runly08.run.db ]
        [ 2017-01-30,14:06:59.365875 ][ INFO    ][ [ Step s3/1 ] Trying to run ]
        [ 2017-01-30,14:06:59.368390 ][ INFO    ][ doing what prog3 is doing ]
        [ 2017-01-30,14:06:59.368845 ][ INFO    ][ EVENTOR_STEP_SEQUENCE: 1 ]
        [ 2017-01-30,14:06:59.369028 ][ INFO    ][ [ Step s3/1 ] Completed, status: TaskStatus.success ]
        [ 2017-01-30,14:06:59.512375 ][ INFO    ][ Processing finished with: success ]
        [ 2017-01-30,14:07:14.517336 ][ INFO    ][ Eventor store file: /eventor/eventor/example/runly08.run.db ]
        [ 2017-01-30,14:07:14.534758 ][ INFO    ][ Processing finished with: success ]
        
Example Highlights
------------------

   The example program builds and runs Eventor sequence 4 times.  The build involves three tasks that would run sequentially.  They are associated to each other with delay of 10 seconds each (lines 25 and 26.)
   
   
   The first time, sequence is build with *restart* run mode (line 31).  In this case, the sequence is initiated.  The next four runs are in *continue* run mode (line 38).  Each of those run continue its preceding run.  To have it show the point, a varying delay is introduced between runs (lines 35-36).
   
   Each run limits the number of loop to a single loop (lines 32 and 38).  A single loop entails Eventor executing triggers and tasks until there is none to execute.  It may be though that there are still outstanding delayed association to act upon.
   
   This behavior is different than continous run (using max_loops=-1), which is the default.  In such run, Eventor will continue to loop until there are no triggers, tasks, and delayed association to process.
   
   Eventor five runs can be observed in example output lines 1-6, 7-2, 13-14, 15-20, and 21-22 each.  During the first run, Step *s1* matures and executed.  Eventor is executed again after 15 seconds by which the delay for *s2* passed.  As a result *s2* is executed in Eventor's second run.  
   
   The third run is executed 5 seconds after *s2* completion.  Too short of a time to have *s3* delayed association pass.  As a result, third run finds nothing to run.  The fourth cycle finds *s3* association matured and execute it.  The last cycle, finds nothing to run, as the sequence is complete.
    
Resources
=========

    *add_step* allows association of step with resources.  If acquires argument is provided, before step starts, *Eventor* 
    will attempt to reserve resources.  Step will be executed only when resources are secured.
    
    When *release* argument is provided, resources resources listed as its value will be released when step is done.  If 
    release is None, whatever resources stated by *acquires* would be released.  If the empty list is set as value, no 
    resource would be released.
    
    To use resources, program to use Resource and ResourcePool from acris.virtual_resource_pool.  Example for such definitions are below.
    
Example for resources definitions
---------------------------------

    .. code:: 
        :number-lines:
        
        import eventor as evr
        from acris import virtual_resource_pool as vrp

        class Resources1(vrp.Resource): pass
        class Resources2(vrp.Resource): pass
        
        rp1=vrp.ResourcePool('RP1', resource_cls=Resources1, policy={'resource_limit': 2, }).load()                   
        rp2=vrp.ResourcePool('RP2', resource_cls=Resources2, policy={'resource_limit': 2, }).load()
        
        ev=evr.Eventor( logging_level=logging.INFO, )
        
        s1=ev.add_step('s0.s00.s1', func=prog, kwargs={'progname': 'prog1'}, acquires=[(rp2, 1), ],) 
        

Next Release
============

    The following is some of the major tasks intended to be completed into this product.
    
    1. remote tasks: expand ability to launch tasks to include remote host via ssh
    #. asynchronous tasks: embed mechanism to launch asynchronous tasks
    #. remote callback mechanisms: allow remote asynchronous tasks communicate with Eventor (TCP/IP, HTTP, etc.) 
    

Additional Information
======================

    Eventor github project (https://github.com/Acrisel/eventor) has additional examples with more complicated flows.
    
    
    



 