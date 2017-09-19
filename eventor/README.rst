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
        
        
        def construct_and_run():
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
            ev.run()
            ev.close()
            
        
        if __name__ == '__main__':
            import multiprocessing as mp
            mp.freeze_support()
            mp.set_start_method('spawn')
            construct_and_run()
        
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
        
        Eventor(name='', store='', run_mode=RunMode.restart, recovery_run=None, run_id='', shared_db=False,
                logging_level=logging.INFO, config={})

Args
````

    *name*: string id for Eventor object initiated.
    
    *store*: Eventor mechanism is built to work with SQLAlchemy. If store is provided, Eventor first check if store is a tag within config under **EVENTOR.DATABASE** (or whatever the environment variables *EVENTOR_CONFIG_TAG* and *EVENTOR_DB_CONFIG_TAG* points to) section. It the tag exists, it will pick its configuration as database configuration. If tag is not found, If tag is not provided, Eventor will tyr to look for *default* database configuration. Otherwise, *store* will be considered as a path to file that would store runnable (sqlite) information; if ':memory:' is used, in-memory temporary storage will be created.  If not provided, calling module path and name will be used with db extension instead of '.py'.
    
    *run_mode*: can be either *RunMode.restart* (default) or *RunMode.recover*; in restart, new instance or the run will be created. In recovery, if *shared_db* is set, run_id or the recovered program must be provided.
    
    *recovery_run*: if *RunMode.recover* is used, *recovery_run* will indicate specific instance of previously recovery run that would be executed.If not provided, latest run would be used.
    
    *run_id*: unique ID for the program run (excluding recovery_run).  It is mandatory in *shared_db* mode, and if not provided, will be generated.
    
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
        | shared_db           | False      | if set, db must not be in memory. signals that   |
        |                     |            | multiple programs will use the same database     |
        |                     |            | tables.                                          |
        +---------------------+------------+--------------------------------------------------+
        | envvar_prefix       | EVENTOR_   | set prefix for environment variable defined for  |
        |                     |            | each step:                                       |
        |                     |            |    STEP_NAME, STEP_SEQUENCE, and STEP_RECOVERY   |
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
    
Eventor *run* method
---------------------

    .. code-block:: python
    
        run(max_loops=-1)
        
when calling *run*, information is built and loops evaluating events and task starts are executed.  
In each loop events are raised and tasks are performed.  max_loops parameters allows control of how many
loops to execute.

In simple example, **ev.run()** engage Eventor's *run()* method.
        
Args
````

    *max_loops*: max_loops: number of loops to run.  If positive, limits number of loops.
                 defaults to negative, which would run loops until there are no events to raise and
                 no task to run. 
                 
Returns
```````

    If there was a failure that was not followed by event triggered, result will be False.


Eventor *close* method
----------------------

    .. code-block:: python
    
        close()
        
when calling *close*, Eventor object will close its open artifacts.  This is similar to close method on multiprocessing Pool.

In simple example, **ev.close()** engage Eventor's *close()* method.
        
Args
````

    N/A. 
                 
Returns
```````

    N/A.


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


        def construct_and_run():
            # start regularly; it would fail in step 2
            ev=build_eventor(param=-9)
            ev.run()
            ev.close()

            # rerun in recovery
            ev=build_eventor(evr.RunMode.recover, param=9)
            ev.run()
            ev.close()
        
        
        if __name__ == '__main__':
            import multiprocessing as mp
            mp.freeze_support()
            mp.set_start_method('spawn')
            construct_and_run()

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
    

        def construct_and_run():
            ev=build_flow(run_mode=evr.RunMode.restart)
            ev.run(max_loops=1)
            ev.close()

            loop=0
            while True:
                total_todos, _ = ev.count_todos()
                if total_todos == 0:
                    break
                    
                loop += 1
                delay=5 if loop % 4 != 0 else 15
                time.sleep(delay)
                ev=build_flow(run_mode=evr.RunMode.continue_)
                ev.run(max_loops=1) 
           ß     ev.close()
    

        if __name__ == '__main__':
            import multiprocessing as mp
            mp.freeze_support()
            mp.set_start_method('spawn')
            construct_and_run()  
                      
Example Output
--------------

    .. code:: 
        :number-lines:

        [ 2017-08-16,16:31:29.277048 ][ Task-s1(1)  ][ INFO    ][ [ Step s1/1 ] Trying to run ]
        [ 2017-08-16,16:31:29.277903 ][ Task-s1(1)  ][ INFO    ][ doing what prog1 is doing ]
        [ 2017-08-16,16:31:29.278114 ][ Task-s1(1)  ][ INFO    ][ EVENTOR_STEP_SEQUENCE: 1 ]
        [ 2017-08-16,16:31:29.278360 ][ Task-s1(1)  ][ INFO    ][ [ Step s1/1 ] Completed, status: TaskStatus.success ]
        [ 2017-08-16,16:31:29.500688 ][ MainProcess ][ INFO    ][ Processing finished with: success; outstanding tasks: 1 ]
        [ 2017-08-16,16:31:35.074012 ][ MainProcess ][ INFO    ][ Processing finished with: success; outstanding tasks: 1 ]
        [ 2017-08-16,16:31:41.028196 ][ Task-s2(1)  ][ INFO    ][ [ Step s2/1 ] Trying to run ]
        [ 2017-08-16,16:31:41.029191 ][ Task-s2(1)  ][ INFO    ][ doing what prog2 is doing ]
        [ 2017-08-16,16:31:41.029429 ][ Task-s2(1)  ][ INFO    ][ EVENTOR_STEP_SEQUENCE: 1 ]
        [ 2017-08-16,16:31:41.029697 ][ Task-s2(1)  ][ INFO    ][ [ Step s2/1 ] Completed, status: TaskStatus.success ]
        [ 2017-08-16,16:31:41.240564 ][ MainProcess ][ INFO    ][ Processing finished with: success; outstanding tasks: 1 ]
        [ 2017-08-16,16:31:46.989434 ][ MainProcess ][ INFO    ][ Processing finished with: success; outstanding tasks: 1 ]
        [ 2017-08-16,16:32:02.931265 ][ Task-s3(1)  ][ INFO    ][ [ Step s3/1 ] Trying to run ]
        [ 2017-08-16,16:32:02.932407 ][ Task-s3(1)  ][ INFO    ][ doing what prog3 is doing ]
        [ 2017-08-16,16:32:02.932661 ][ Task-s3(1)  ][ INFO    ][ EVENTOR_STEP_SEQUENCE: 1 ]
        [ 2017-08-16,16:32:02.932940 ][ Task-s3(1)  ][ INFO    ][ [ Step s3/1 ] Completed, status: TaskStatus.success ]
        [ 2017-08-16,16:32:03.014584 ][ MainProcess ][ INFO    ][ Processing finished with: success; outstanding tasks: 0 ]
        
Example Highlights
------------------

   The example program builds and runs Eventor sequence 4 times.  The build involves three tasks that would run sequentially.  They are associated to each other with delay of 10 seconds each (lines 26 and 28.)
   
   
   The first time, sequence is build with *restart* run mode (line 35).  In this case, the sequence is initiated.  The next four runs are in *continue* run mode (line 48).  Each of those run continue its preceding run.  To have it show the point, a varying delay is introduced between runs (lines 46-47).
   
   Each run limits the number of loop to a single loop (lines 40 and 50).  A single loop entails Eventor executing triggers and tasks until there is none to execute.  It may be though that there are still outstanding delayed association to act upon.
   
   This behavior is different than continuous run (using max_loops=-1), which is the default.  In such run, Eventor will continue to loop until there are no triggers, tasks, and delayed association to process.
   
   Eventor runs can be observed in example output lines 1-5, 6, 7-11, 12, and 13-17 each.  Note that the second and forth runs had not trigger to execute on.  The associated tasks' delays was not yet matured.
    
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

    .. code_block:: python
        :number-lines:
        
        import eventor as evr
        from acris import virtual_resource_pool as vrp

        class Resources1(vrp.Resource): pass
        class Resources2(vrp.Resource): pass
        
        rp1=vrp.ResourcePool('RP1', resource_cls=Resources1, policy={'resource_limit': 2, }).load()                   
        rp2=vrp.ResourcePool('RP2', resource_cls=Resources2, policy={'resource_limit': 2, }).load()
        
        ev=evr.Eventor( logging_level=logging.INFO, )
        
        s1=ev.add_step('s0.s00.s1', func=prog, kwargs={'progname': 'prog1'}, acquires=[(rp2, 1), ],) 
        

Distributed Steps
=================

Eventor program can work in a clustered environment.  In this arrangement, steps can be defined to run on different nodes in the cluster.  This is possible granted:
    
    1. SSH is defined among cluster nodes.
    #. Eventor DB is shared among cluster nodes.
    #. Program environment is the *seamlessly-the-same* among cluster nodes.
    
How it works
------------

Eventor will be launched from one host, *server*.  It will then start the same program on every associated host relevant to program, *clients*.  *Client* programs will skip *starting* steps (steps with no )

Cluster SSH access
------------------

When working on distributed environment, Eventor assumes that ssh is set properly among participating hosts.  

To allow ssh run command with .profile (or .bash_profile) are not automatically exceuted, add the following before rsa key in .ssh/authorizedkeys

    .. code_block:: python
    
        command "if [[ \"x${SSH_ORIGINAL_COMMAND}x\" != \"xx\" ]]; then source ~/.profile; eval \"${SSH_ORIGINAL_COMMAND}\"; else /bin/bash --login; fi;" <key>
        
Database
--------

Eventor program would be launched on all cluster nodes relevant to the program.

Next Release
============

    The following is some of the major tasks intended to be completed into this product.
    
    1. remote tasks: expand ability to launch tasks to include remote host via ssh
    #. asynchronous tasks: embed mechanism to launch asynchronous tasks
    #. remote callback mechanisms: allow remote asynchronous tasks communicate with Eventor (TCP/IP, HTTP, etc.) 
    
Change log
==========

5.0
---

    1. added database configuration allowing the use of SqlAlchemy database engines
    #. added shared_db to indicate db is shared among multiple programs and runs
    #. added run_id as unique identifier for program run (not to be confused with recovery)
    #. improved documentation to reflect the need for mp.freeze_support() and mp.set_start_method('spawn')
    #. added dependency on namedlist, and PyYAML, packages
    #. bug fix in delay

Additional Information
======================

    Eventor github project (https://github.com/Acrisel/eventor) has additional examples with more complicated flows.
    
    
    



 