=======
Eventor
=======

--------
Overview
--------

    *Eventor* provides programmer with interface to create events, steps and associations of these artifacts with to create a flow.
    
    It would be easier to show an example. 

Simple Example
==============
    
    .. code::
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
                       triggers={evr.StepTriggers.at_success: (ev2s,),}) 
        s2=ev.add_step('s2', func=prog, kwargs={'progname': 'prog2'}, 
                       triggers={evr.StepTriggers.at_success: (ev3s,), })
        s3=ev.add_step('s3', func=prog, kwargs={'progname': 'prog3'},)
        
        ev.add_assoc(ev1s, s1)
        ev.add_assoc(ev2s, s2)
        ev.add_assoc(ev3s, s3)
        
        ev.trigger_event(ev1s, 1)
        ev()
        
Example Output
==============

    The above example with provide the following log output.
              
    .. code::
    
        [ 2016-11-30 10:07:48,572 ][ INFO ][ Eventor store file: :memory: ][ main.__init__ ]
        [ 2016-11-30 10:07:48,612 ][ INFO ][ Running step s1[1] ][ main.task_wrapper ]
        [ 2016-11-30 10:07:48,612 ][ INFO ][ Step completed s1[1], status: success, result 'prog1' ][ main.task_wrapper ]
        [ 2016-11-30 10:07:50,649 ][ INFO ][ Running step s2[1] ][ main.task_wrapper ]
        [ 2016-11-30 10:07:50,649 ][ INFO ][ Step completed s2[1], status: success, result 'prog2' ][ main.task_wrapper ]
        [ 2016-11-30 10:07:52,688 ][ INFO ][ Running step s3[1] ][ main.task_wrapper ]
        [ 2016-11-30 10:07:52,689 ][ INFO ][ Step completed s3[1], status: success, result 'prog3' ][ main.task_wrapper ]
        [ 2016-11-30 10:07:53,700 ][ INFO ][ Processing finished ][ main.loop_session_start ]

Code Highlights
===============

    *Eventor* (line 10) defines an in-memory eventor object.  Note that in-memory eventors are none recoverable.
    
    *add_event* (e.g., line 12) adds an event named **run_step1** to the respective eventor object.
    
    *add_step* (e.g., line 16) adds step **s1** which when triggered would run predefined function **prog** with key words parameters **progname='prog1'**.
    Additionally, when step would end, if successful, it would trigger event **evs2**
    
    *add_assoc* (e.g., line 22) links event **evs1** and step **s1**.
    
    *trigger_event* (line 26) marks event **evs1**; when triggers, event is associated with sequence.  This would allow multiple invocation.
    
    *ev()* (line 27) invoke eventor process that would looks for triggers and tasks to act upon.  It ends when there is nothing to do.
 
-----------------
Eventor Interface
-----------------

Eventor 
=======

Envtor Class Initiator
----------------------

    .. code::
        
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
          
Envtor add_event method
-----------------------

    .. code::
        
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
        - the basic atom in expression is *even* which is the product of add_event.
        
Returns
```````

    Event object to use in other add_event expressions, add_assoc methods, or with add_step triggers.
    
Envtor add_step method
-----------------------

    .. code::
        
        add_step(name, func, args=(), kwargs={}, triggers={}, recovery={}, config={})

Args
````

    *name*: string unique id for step 
    
    *func*: callable object that would be call at time if step execution
    
    *args*: tuple of values that will be passed to *func* at calling
    
    *kwargs*: keywords arguments that will be pust to *func* at calling
    
    *triggers*: mapping of step statuses to set of events to be triggered as in the following table:
    
        +-------------+-------------------------------------------+
        | status      | description                               |
        +=============+===========================================+
        | at_ready    | set when task is ready to run (triggered) |
        +-------------+-------------------------------------------+
        | at_active   | set when task is running                  |
        +-------------+-------------------------------------------+
        | at_success  | set when task is successful               |
        +-------------+-------------------------------------------+
        | at_failure  | set when task fails                       |
        +-------------+-------------------------------------------+
        | at_complete | stands for success or failure of task     |
        +-------------+-------------------------------------------+
        
        
    *recovery*: mapping of state status to how step should be handled in recovery:
    
        +----------+------------------+------------------------------------------------------+
        | status   | default          | description                                          |
        +==========+==================+======================================================+
        | ready    | StepReplay.rerun | if in recovery and previous status is ready, rerun   |
        +----------+------------------+------------------------------------------------------+
        | active   | StepReplay.rerun | if in recovery and previous status is active, rerun  |
        +----------+------------------+------------------------------------------------------+
        | failure  | StepReplay.rerun | if in recovery and previous status is failure, rerun |
        +----------+------------------+------------------------------------------------------+
        | success  | StepReplay.skip  | if in recovery and previous status is success, skip  |
        +----------+------------------+------------------------------------------------------+
    
    *config*: keywords mapping overrides for step configuration.
    
        +-------------------+------------------+---------------------------------------+
        | name              | default          | description                           |
        +===================+==================+=======================================+
        | stop_on_exception | True             | stop flow if step ends with Exception | 
        +-------------------+------------------+---------------------------------------+
    
Returns
```````

    Step object to use in add_assoc method.
    
Envtor add_assoc method
-----------------------

    .. code::
        
        add_assoc(event, *assocs)

Args
````

    *event*: event objects as provided by add_event.
    
    *assocs*: list of associations objects.  List is composed from either events (as returned by add_event) or steps (as returned by add_step)
    
Returns
```````

    N/A
    
Envtor trigger_event method
---------------------------

    .. code::
        
        trigger_event(event, sequence=None)

Args
````

    *event*: event objects as provided by add_event.
    
    *sequence*: unique association of triggered event.  Event can be triggered only once per sequence.  All derivative triggers will carry the same sequence.
    
Returns
```````

    N/A
    


 