=================
Development Notes
=================

------------------------
Distribution Environment
------------------------

Goal
====

Allow Eventor and its derivative tools to work on clustered environment.

Architecture
============

Assumptions
-----------
1. Each node in the cluster will have software resources installed - there is no need to pass the software needed to run
#. Nodes are access-able vi ssh
#. Nodes have access to shared database compatible with SQLAlchemy
#. When binding 

Guideline
---------

1. Assignment of runs to nodes is pre-configured.
#. Eventor resources can be either in the scope of a node or of a cluster.
#. Monitor and control of a run can be done from anywhere that has ssh access to serving hosts.
#. Multiple runs of the same program are each separate running instance.

Example
-------

.. code-block:: python

    import eventor as evr
    import os
    
    def prog(progname):
        logger.info("doing what %s is doing" % progname)
        logger.info("EVENTOR_STEP_SEQUENCE: %s" % os.getenv("EVENTOR_STEP_SEQUENCE"))
        return progname
        
    mysql_store="mysql+mysqldb://..."
    pg_store="postgresql+psycopg2://user:password@/dbname"
    
    ev=evr.Eventor(store=mysql_store, logging_level=logging.DEBUG)
    
    ev1s=ev.add_event('run_step1')
    ev2s=ev.add_event('run_step2')
    ev3s=ev.add_event('run_step3')
    
    s11=ev.add_step('s11', host='s1', func=prog, kwargs={'progname': 'prog11'}, triggers={evr.StepStatus.success: (ev2s,),}) 
    s12=ev.add_step('s12', host='s2', func=prog, kwargs={'progname': 'prog12'}, triggers={evr.StepStatus.success: (ev2s,),}) 
    s2=ev.add_step('s2', host='s2', func=prog, kwargs={'progname': 'prog2'}, triggers={evr.StepStatus.success: (ev3s,), })
    s3=ev.add_step('s3', host='s1', func=prog, kwargs={'progname': 'prog3'},)
    
    ev.add_assoc(ev1s, s11)
    ev.add_assoc(ev1s, s12)
    ev.add_assoc(ev2s, s2)
    ev.add_assoc(ev3s, s3)
    
    ev.trigger_event(ev1s, 1)
    ev.run()
    ev.close()
    

Running modes
-------------

1. **Standalone**: Mode of operation in which Steps runs on single host.  In sqlite DB is dedicated to each run.  
#. **Distributed**: Mode of operation in which Steps runs on multiple machines. DB is shared among the cluster.

Standalone
~~~~~~~~~~

1. in-memory and file DB are fine as there is no need to share DB among hosts 
2. Eventor controller is incorporated in each run. 
3. Resources are confined to the scope of the program.

Distributed
~~~~~~~~~~~

1. DB is shared among the cluster.
2. Program is registered in Eventor DB and then run by Eventor daemons on hosts.
3. There are three level of scopes: program, local, cluster
4. if host is not associated with step, it would run on default host.  If there is no default host, run on same host as previous step.  If there are more than one step prior that are running on different host, raise Error.
5. defines groups with properties and have steps member of those groups.



1. Each machine will run its own agent(s).
#. agent monitors one or more database for events triggering action on their node.
#. agent would launch the appropriate step when triggered.
#. programs can be submitted from anywhere with access to the cluster - pending that the software is installed on the cluster nodes.
#. cleanup, rerun, recover

Change Overview
---------------

1. Allow multiple programs and instances thereof in the same database -> change of DB table schema.

    a. example: two testers running the same eventor based program using the same test database
    b. example: same user running the same eventor based program with different arguments for the steps.
    
2. Allow other DB engines supported by SQL Alchemy.
    
    a. have configuration for database configuration (with encrypted password)

3. Allow run() to be in background.

Notes
=====

Remove dates prefix from logs 

for f in goodrun badrun; do
    source=${f}.txt
    target=${f}_strip.txt
    gsed 's/([[:digit:]]\+) \]/ \]/g' $source | \
    gsed 's/\[ [[:digit:][:punct:]]* \]//g' | \
    gsed 's/[[:digit:]]\{4\}\, \([[:digit:]]\{1,\}\, \)\{5\}[[:digit:]]*//g' | \
    gsed 's/pid=[[:digit:]]*/pid=/g' \
    > $target
done

