'''
Created on Nov 23, 2016

@author: arnon
'''

import logging
from acris import Sequence, MpLogger, MergedChainedDict
from acris import virtual_resource_pool as vrp
import multiprocessing as mp
from collections import namedtuple
import inspect
from enum import Enum
import os
import pickle
import queue
import time
from eventor.step import Step
from eventor.event import Event
from eventor.assoc import Assoc
from eventor.dbapi import DbApi
from eventor.utils import calling_module, traces, rest_sequences, store_from_module
from eventor.eventor_types import EventorError, TaskStatus, step_to_task_status, task_to_step_status, LoopControl, StepStatus, StepReplay, RunMode, DbMode
from eventor.VERSION import __version__
from eventor.dbschema import Task
#from eventor.loop_event import LoopEvent

module_logger=logging.getLogger(__name__)

from acris.decorated_class import traced_method
from eventor.utils import decorate_all, print_method
#traced=traced_method(None, True)

class TaskAdminMsgType(Enum):
    result=1
    update=2
    
TaskAdminMsg=namedtuple('TaskAdminMsg', ['msg_type', 'value', ])
TriggerRequest=namedtuple('TriggerRequest', ['type', 'value'])

class ResourceAllocationCallback(object):
    def __init__(self, notify_queue):
        self.q=notify_queue
        
    def __call__(self,resources=None):
        self.q.put(resources)

def task_wrapper(task=None, step=None, adminq=None):
    ''' 
    Args:
        func: object with action method with the following signature:
            action(self, action, unit, group, sequencer)    
        action: object with taskid, unit, group: id of the unit to pass
        sqid: sequencer id to pass to action '''
    
    #db=db.initialize()
        
    #db=DbApi(runfile=dbfile, mode=DbMode.append)
    task.pid=os.getpid()
    os.environ['EVENTOR_STEP_SEQUENCE']=str(task.sequence)
    os.environ['EVENTOR_STEP_NAME']=str(step.name)
    #db.update_task(task)
    #db.close()
    
    # Update task with PID
    update=TaskAdminMsg(msg_type=TaskAdminMsgType.update, value=task) 
    adminq.put( update )
    
    module_logger.info('[ Step {}/{} ] Trying to run'.format(step.name, task.sequence))
    
    try:
        # todo: need to pass task resources.
        result=step(seq_path=task.sequence, )
    except Exception as e:
        trace=inspect.trace()
        trace=traces(trace) #[2:]
        task.result=(e, pickle.dumps(trace))
        task.status=TaskStatus.failure
    else:
        task.result=result
        task.status=TaskStatus.success
        
    result=TaskAdminMsg(msg_type=TaskAdminMsgType.result, value=task) 
    module_logger.info('[ Step {}/{} ] Completed, status: {}'.format(step.name, task.sequence, str(task.status), ))
    adminq.put( result )
    return True

class EventorState(Enum):
    active=1
    shutdown=2
    
class RpCallback(object):
    def __init__(self, notify_queue, task_id=''):
        self.q=notify_queue
        self.task_id=task_id
    #def get_name(self):
    #    return self.name
    def __call__(self,ready=False):
        self.q.put( self.task_id )

class Memtask(object):
    def __init__(self, task, ):
        self.id_=task.id_
        self.step_id=task.step_id
        self.sequence=task.sequence
        self.requestor=None
        self.fueled=False
        self.request_id=None
        #self.resources=None
        
    #def __del__(self):
    #    if self.requestor and self.resources:
    #        self.requestor.put(*self.resources)
    
#class Eventor(metaclass=decorate_all(print_method(module_logger.debug))):
class Eventor(object):
    """Eventor manages events and steps that needs to be taken when raised.
    
    Eventor provides programming interface to create events, steps and associations among them.
    It provides means to raise events, and a service that would perform steps according to those events. 
        
    Attributes: 
        controlq: mp queue is used to control endless eventor loop
    
    Methods:
        add_event: 
        add_step: 
    
    """
    
    config_defaults={'workdir':'/tmp', 
                     'logdir': '/tmp', 
                     'task_construct': mp.Process, 
                     #'synchrous_run': False, 
                     'max_concurrent': -1, 
                     'stop_on_exception': True,
                     'sleep_between_loops': 0.1,
                     'sequence_arg_name': None, # 'eventor_task_sequence'
                     #'pass_resources': False,
                     }  
    
    recovery_defaults={StepStatus.ready: StepReplay.rerun, 
                      StepStatus.allocate: StepReplay.rerun, 
                       StepStatus.fueled: StepReplay.rerun, 
                       StepStatus.active: StepReplay.rerun, 
                       StepStatus.failure: StepReplay.rerun, 
                       StepStatus.success: StepReplay.skip,}  
        
    def __init__(self, name='', store='', run_mode=RunMode.restart, recovery_run=None, dedicated_logging=False, logging_level=logging.INFO, config={},):
        """initializes steps object
        
            Args:
                name: human readable identifying eventor among other eventors
                store: file in which Enetor data would be stored and managed for reply/restart 
                    if the value is blank, filename will be based on calling module 
                    if the value is :memory:, an in-memory temporary structures will be used
                run_mode: (RunMode) set Eventor to operate in recovery or as restart
                recovery_run: (int) if in recovery, and provided, it would recover the provided run.
                    if in recovery, but recovery_run not provided, latest run would be recovered.
                config: dict of configuration parameters to be used in operating eventor

                config parameters can include the following keys:
                    - logdir=/tmp, 
                    - workdir=/tmp, 
                    #- synchrous_run=False,
                    - task_construct=mp.Process, 
                    - stop_on_exception=True,
                    - sleep_between_loops=1

            Returns:
                new object
                
            Raises:
                N/A
        """
        self.name=''
        self.__config=MergedChainedDict(config, os.environ, Eventor.config_defaults) 
        self.__controlq=mp.Queue()
        self.__steps=dict() 
        #self.__acquires=dict() 
        #self.__releases=dict() 
        self.__tasks=dict() 
        self.events=dict() 
        self.assocs=dict()
        self.__rp_notify=queue.Queue()
        
        if dedicated_logging:
            logging_root='.'.join(__name__.split('.')[:-1])
        else:
            logging_root=''
        level_formats={logging.DEBUG:"[ %(asctime)-15s ][ %(levelname)-7s ][ %(message)s ][ %(module)s.%(funcName)s(%(lineno)d) ]",
                        'default':   "[ %(asctime)-15s ][ %(levelname)-7s ][ %(message)s ]",
                        }
        
        self.logger=MpLogger(logging_level=logging_level, level_formats=level_formats, logging_root=logging_root, datefmt='%Y-%m-%d,%H:%M:%S.%f', logdir=self.__config['logdir'])
        self.logger.start()
        
        self.calling_module=calling_module()
        self.filename=store if store else store_from_module(self.calling_module)

        module_logger.info("Eventor store file: %s" % self.filename)
        #self.db=DbApi(self.filename)
        self.__adminq_mp=mp.Queue()
        self.__adminq_th=queue.Queue()
        self.__resource_notification_queue=mp.Queue()
        self.requestq=queue.Queue()
        self.task_proc=dict()
        self.state=EventorState.active
        
        db_mode=DbMode.write if run_mode==RunMode.restart else DbMode.append
        self.db=DbApi(self.filename, mode=db_mode)
        self.__requestors=vrp.Requestors()
        
        rest_sequences()
        
        if run_mode == RunMode.restart:
            self.__write_info()
        else: # recover
            self.__read_info(recovery_run)
        
    def __repr__(self):
        steps='\n'.join([ repr(step) for step in self.__steps.values()])
        events='\n'.join([ repr(event) for event in self.events.values()])
        assocs='\n'.join([ repr(assoc) for assoc in self.assocs.values()])
        result="Steps( name( {} ) events( {} ) steps( {} ) assocs( {} )  )".format(self.name, events, steps, assocs)
        return result
        
    def __str__(self):
        steps='\n    '.join([ str(step) for step in self.__steps.values()])
        events='\n    '.join([ str(event) for event in self.events.values()])
        assocs='\n    '.join([ str(assoc) for assoc in self.assocs.values()])
        result="Steps( name( {} )\n    events( \n    {}\n   )\n    steps( \n    {}\n   )\n    assocs( \n    {}\n   )  )".format(self.name, events, steps, assocs)
        return result
    
    def __write_info(self):
        self.recovery=0
        info={'version': __version__,
              'program': self.calling_module,
              'recovery': self.recovery,
              }
        self.db.write_info(**info)
        self.previous_triggers=None
        self.previous_tasks=None
    
    def __read_info(self, recovery_run=None):
        self.info=self.db.read_info()
        recovery=recovery_run
        if recovery is None:
            recovery=self.info['recovery']
        self.recovery=str(int(recovery) + 1)
        self.db.update_info(recovery=self.recovery)
        self.previous_triggers=self.db.get_trigger_map(recovery=recovery)
        self.previous_tasks=self.db.get_task_map(recovery=recovery)

    def __convert_trigger_at_complete(self, triggers):
        at_compete=triggers.get(StepStatus.complete)
        if at_compete:
            del triggers[StepStatus.complete]
            at_fail=triggers.get(StepStatus.failure, list())
            at_success=triggers.get(StepStatus.success, list())
            at_fail.extend(at_compete)
            at_success.extend(at_compete)
            triggers[StepStatus.failure]=at_fail
            triggers[StepStatus.success]=at_success
        return triggers
          
    def __convert_recovery_at_complete(self, recovery):
        at_compete=recovery.get(StepStatus.complete)
        if at_compete is not None:
            del recovery[StepStatus.complete]
            at_fail=recovery.get(StepStatus.failure, at_compete)
            at_success=recovery.get(StepStatus.success, at_compete)
            recovery[StepStatus.failure]=at_fail
            recovery[StepStatus.success]=at_success
        return recovery

    def add_event(self, name, expr=None):
        """add a event to Eventor object
        
        Args:
            name: (string) unique identifier provided by caller
            
        returns:
            new event that was added to Eventor; this event can be used further in assoc method
        """
        try:
            event=self.events[name]
        except:
            pass
        else:
            if expr == event.expr:
                return event
            
        event=Event(name, expr=expr)
        self.events[event.id_]=event
        #event.db_write(self.db)
        return event
    
    def get_step(self, name):
        return self.__steps.get(name, None)
    
    def add_step(self, name, func=None, args=(), kwargs={}, triggers={}, acquires=None, releases=None, recovery={}, config={}):
        """add a step to steps object
    
        config parameters can include the following keys:
            - stop_on_exception=True
            - sequence_arg_name=None : when set, corresponding name will be used as keyword argument to passed sequence to step
            #- pass_resources=False: when set, eventor_task_resources keyword argument will be passed to step
            
        Args:
            name: (string) unique identifier
            
            func: (callable) if provided, will be called when step is activated; otherwise its nope step.
            
            func_args: args to pass step when executing
            
            func_kwargs: keyword args to pass step when executing
            
            config: additional dict of keywords configuration 
            
            triggers: set of events to trigger once step processing is done
            
            acquires: list of resources to acquire before starting
            
            releases: list of resources to release once done; 
                defaults to acquires. if not provided.
            
            recovery: instructions on how to deal with 
                default: {TaskStatus.failure: StepReplay.rerun, 
                          TaskStatus.success: StepReplay.skip}
            
        returns:
            new step that was added to Eventor; this step can be used further in assoc method
            
        raises:
            EventorError: if func is not callable
        """
        try:
            step=self.__steps[name]
        except:
            pass
        else:
            return step
        
        triggers=self.__convert_trigger_at_complete(triggers)
        recovery=self.__convert_recovery_at_complete(recovery)
        recovery=MergedChainedDict(recovery, Eventor.recovery_defaults)
        recovery=dict([(step_to_task_status(status), replay) for status, replay in recovery.items()])
        
        config=MergedChainedDict(config, self.__config, os.environ,)
        step=Step(name=name, func=func, func_args=args, func_kwargs=kwargs, acquires=acquires, releases=releases, config=config, triggers=triggers, recovery=recovery)
        found=self.__steps.get(step.id_)
        if found:
            raise EventorError("Step with similar name already defined: %s" % step.id_)
        self.__steps[step.id_]=step
        #step.db_write(self.db)
        return step
        
    def add_assoc(self, event, *assocs):
        """add a assoc to Eventor object
        
        Associates event with one or more objects of steps and events
        
        Args:
            event: an event object return from add_event()
            objs: list of either step or event objects returned from add_step() or add_event() respectively
            
        returns:
            N/A
            
        raises:
            EnventorError: if event is not of event type or obj is not instance of Event or Step
        """
        try:
            objs=self.assocs[event.id_]
        except KeyError:
            objs=list()
            self.assocs[event.id_]=objs

        for obj in assocs:
            assoc=Assoc(event, obj)
            objs.append(assoc)
    
    def trigger_event(self, event, sequence=None, db=None):
        """Activates event 
        
            Activate event by registering it in trigger table. 
            
            If Sequence is provided, it will be used as trigger sequence for this event.
            This is done to allow multiple triggers for the same event.
            
            If sequence is not provided, one will assigned to this trigger.  
            
            Sequence creates association with derived steps or events associated with the event triggered.
        
            Args:
                event: (Event) object returned from add_event()
                sequence: (str) object uniquely identifying this trigger among other triggers of the same event
                
            Returns:
                N/A
            
            Raises:
                EventorError
                
        """
        if not db:
            db=self.db
        added=event.trigger_if_not_exists(db=db, sequence=sequence, recovery=self.recovery)
        return added
        
    def remote_trigger_event(self, event, sequence=None,):
        trigger_request=TriggerRequest(type='event', value=(event, sequence))
        self.requestq.put(trigger_request)
        
    def trigger_step(self, step, sequence):
        """Activates step 
        
            Activate step by registering it in task table are 'ready'.  Task loop will pick it up for processing. 
        
            Args:
                step: (Step) object returned from add_step()
                sequence: (str) object uniquely identifying this trigger among other triggers of the same event
                
            Returns:
                N/A
            
            Raises:
                EventorError
                
        """
        task=step.trigger_if_not_exists(self.db, sequence, status=TaskStatus.ready, recovery=self.recovery)
        if task:
            self.__triggers_at_task_change(task)
        return task is not None
    
    def __loop_trigger_request(self):
        while True:   
            try:
                request=self.requestq.get_nowait() 
            except queue.Empty:
                return 
            if request.type=='event':
                event, sequence = request.value
                self.trigger_event(event, sequence)
                module_logger.debug('[ %s/%s ] Triggering event' % (event.id_, sequence))
        
          
    def assoc_loop(self, event, sequence):
        ''' Fetches event associations and trigger them.
        
        If association is an event:
            trigger the event
            
        If association is a step:  
            register task
            trigger event - task running.
            
        '''
        assoc_events=list()
        assoc_steps=list()
        try:
            assocs=self.assocs[event.id_]
        except KeyError:
            assocs=[]
            
        for assoc in assocs:
            assoc_obj=assoc.assoc_obj
            if isinstance(assoc_obj, Event):
                # trigger event
                module_logger.debug('Processing event association event [%s]: %s' % (sequence, repr(assoc_obj)))
                self.trigger_event( assoc_obj, sequence )
                assoc_events.append(sequence)
            elif isinstance(assoc_obj, Step):
                # Check if there is previous task for this step
                module_logger.debug('Processing event association step [%s]: %s' % (sequence, repr(assoc_obj)))
                self.trigger_step(assoc_obj, sequence)
                assoc_steps.append(sequence)
                
            else:
                raise EventorError("Unknown assoc object in association: %s" % repr(assoc))
        
        return list(set(assoc_events)), list(set(assoc_steps))

    def __loop_event(self):
        loop_seq=Sequence('EventLoop')
        self.loop_id=loop_seq() 
            
        # first pick up requests and move to act
        # this step is needed so automated requests will not impact 
        # the process as it is processing.
        # requests not picked up in current loop, will be picked by the next.
        triggers=self.db.get_trigger_iter(recovery=self.recovery)
        trigger_db=dict()
        
        event_seqs=list()
        step_seqs=list()

        # need to rearrange per iteration
        for trigger in triggers:
            try:
                trigger_map=trigger_db[trigger.sequence]
            except KeyError:
                trigger_map=dict()
                trigger_db[trigger.sequence] = trigger_map
            
            #print('trigger %s[%s]' % (trigger.event_id, trigger.iteration) )  
            trigger_map[trigger.event_id] = True

            if not trigger.acted:
                assoc_events, assoc_steps = self.assoc_loop(self.events[trigger.event_id], trigger.sequence)
                event_seqs.extend(assoc_events)
                step_seqs.extend(assoc_steps)
                self.db.acted_trigger(trigger)
                                  
        # trigger_map=dict([(trigger.event_id, True) for trigger in triggers])
        for sequence, trigger_map in trigger_db.items():
            #print('trigger_map (%s)' % iteration, trigger_map)
            
            for event in self.events.values():
                if not event.expr: continue
                
                try:
                    result=eval(event.expr, globals(), trigger_map)
                except:
                    result=False
                    
                module_logger.debug("[ Event %s/%s ] Eval expr: %s = %s\n    %s" % (event.id_, sequence,event.expr, result, trigger_map))
                
                # update trigger map with result
                #trigger_map[event.event_id]=result
                
                if result==True: # and self.act:
                    # TODO: do we need to raise event.
                    added=self.trigger_event(event, sequence,)   
                    #print('loop_event_iteration', event.event_id, iteration, added)  
                    if added:  
                        module_logger.debug('[ Event %s/%s] Triggered event (%s ):\n    {}' % (event.id_, sequence, repr(event))) 
                        event_seqs.append(sequence)
                        
        return list(set(event_seqs)), list(set(step_seqs))                  
    
    def __log_error(self, task, stop_on_exception):
        logutil=module_logger.error if stop_on_exception else module_logger.warning
        err_exception, pickle_trace=task.result
        err_trace=pickle.loads(pickle_trace)
        
        logutil('Exception in run_action: \n    {}'.format(task,)) #)
        logutil("%s" % (repr(err_exception), ))
        trace='\n'.join([line.rstrip() for line in err_trace])
        if trace: logutil("%s" % (trace, ) )

    def __apply_task_result(self, task):
        #step=self.__steps[task.step_id]
        module_logger.debug('[ Task %s/%s ] applying task update to db\n    %s' % (task.step_id, task.sequence, repr(task), ))
        self.db.update_task(task=task)
        if task.status in [TaskStatus.success, TaskStatus.failure]:
            self.__release_task_resources(task)
        triggered=self.__triggers_at_task_change(task)
        return triggered
    
    def __play_result(self, act_result,):
            module_logger.debug('Result collected: \n    %s' % ( repr(act_result)) )  
            stop_on_exception=self.__config['stop_on_exception']
            
            result=True
            if isinstance(act_result.value, Task): 
                task=act_result.value   
                if act_result.msg_type==TaskAdminMsgType.result:
                    proc=self.task_proc[task.id_]
                    module_logger.debug('[ Task %s/%s ] applying result, process: %s, is_allive: %s' % \
                                        (task.step_id, task.sequence, repr(proc), proc.is_alive()))
                    if proc.is_alive():
                        proc.join()
                        module_logger.debug('[ Task %s/%s ] joined' % (task.step_id, task.sequence, ))
                    del self.task_proc[task.id_]  
                    module_logger.debug('[ Task %s/%s ] deleted' % (task.step_id, task.sequence, ))
                    step=self.__steps[task.step_id]
                    step.concurrent-=1
                    triggered=self.__apply_task_result(task)
                    shutdown=(len(triggered) == 0 or stop_on_exception) and task.status == TaskStatus.failure 
                    if task.status==TaskStatus.failure:
                        self.__log_error(task, shutdown)
                    if shutdown:
                        module_logger.info("Stopping running processes") 
                        self.state=EventorState.shutdown
                        result=False
                elif act_result.msg_type==TaskAdminMsgType.update: 
                    self.db.update_task(task=task)
                    # TODO: stop running processes            
            else:
                # TODO: need to deal with action
                module_logger.debug('skip play result; act_result value type not matched: %s' % ( repr(type(act_result.value))) )  
            
            return result
    
    def __collect_results(self,):
        ''' Collect results from task wrapper queues.
        
        There are two queues for the different types of process constructs.
        multiprocess.Process: adminq_mp
        threading.Thread and Invoke: adminq_th
        '''
        
        result=True
        iterate_mp=iterate_th=True
        while iterate_mp or iterate_th: 
            module_logger.debug('Trying to read result queue')   
            
            try:
                act_result=self.__adminq_mp.get_nowait() 
            except queue.Empty:
                act_result=None
                iterate_mp=False
                result_mp=True
            else:    
                result_mp=self.__play_result(act_result)
            
            try:
                act_result=self.__adminq_th.get_nowait() 
            except queue.Empty:
                act_result=None
                iterate_th=False
                result_th=True
            else:    
                result_th=self.__play_result(act_result)
            
            result=result_mp and result_th
                         
        return result
    
    def __triggers_at_task_change(self, task):
        step=self.__steps[task.step_id]
        status=task_to_step_status(task.status)
        triggers=step.triggers.get(status, None)
        triggered=list()
        if triggers:
            for event in triggers: 
                result=event.trigger_if_not_exists(self.db, task.sequence, self.recovery)
                if result: 
                    triggered.append( (event.id_, task.sequence) )
                    module_logger.debug("Triggered post task: %s[%s]" % (repr(event.id_), task.sequence))
        return triggered
    
    def __get_admin_queue(self, task_construct):
        if task_construct == mp.Process:
            result=self.__adminq_mp
        else:
            result=self.__adminq_th
        return result
               
    def __initiate_task(self, task, previous_task=None):
        ''' Playing synchronous action.  
            
        Algorithm:
            1. Set action state to active.
            2. Launch a thread to perform action (use thread pool).
            
        Args:
            task: (Task) task to run
            previous_task: (Task), will be populated if in recovery and an instance of task exists.
        '''
        step=self.__steps[task.step_id]
        step_recovery=StepReplay.rerun
        if previous_task:
            step_recovery=step.recovery[previous_task.status]
        
        if step_recovery == StepReplay.rerun:
            # on rerun, act as before - just run the task  
            
            max_concurrent=step.config['max_concurrent']
            task_construct=step.config['task_construct']
            adminq=self.__get_admin_queue(task_construct=task_construct)
            # TODO: add join when synchronus
            kwds={'task':task, 'step': self.__steps[task.step_id], 'adminq': adminq, }
            if max_concurrent <0 or step.concurrent < max_concurrent: # no-limit
                self.__update_task_status(task, TaskStatus.active)
                triggered=self.__triggers_at_task_change(task)
                
                module_logger.debug('[ Task {} ] Going to construct ({}/{}) and run task:\n    {}'.format(task.step_id, task.sequence, task_construct, repr(task), ))
                proc=task_construct(target=task_wrapper, kwargs=kwds)
                step.concurrent+=1
                try:
                    proc.start()
                except Exception as e:
                    step.concurrent-=1
                    task.status=TaskStatus.failure
                    module_logger.critical('Exception in task execution: \n    {}'.format(task,)) #)
                    trace=inspect.trace()
                    trace=traces(trace)
                    module_logger.critical("%s\n    %s" % (repr(e), '\n    '.join(trace)))
                    module_logger.info("Stopping running processes") 
                    self.state=EventorState.shutdown
                else:
                    self.task_proc[task.id_]=proc
            else:
                module_logger.debug('[ Task {}/{} ] Delaying run (max_concurrent: {}, concurrent: {}) and run task:\n    {}'.format(task.step_id, task.sequence, max_concurrent, step.concurrent, repr(task), ))       
        else:
            # TODO: make sure htis works
            # on skip
            module_logger.debug('[ Step %s/%s ] Skipping task in recovery mode' % (task.step_id, task.sequence ))
            task.status=TaskStatus.success
            #task_result=TaskAdminMsg(msg_type=TaskAdminMsgType.result, value=task)
            triggered=self.__apply_task_result(task,)
            
        return triggered
    
    def __loop_awating_resource_allocation(self):
        while True:
            module_logger.debug("Trying to receive resources" )
            try:
                task_id=self.__rp_notify.get_nowait()
            except queue.Empty:
                break
            
            memtask=self.__tasks.get(task_id, None)    
            step=self.__steps[memtask.step_id]
            module_logger.debug("Received resources for task %s" % (step.name, ))

            memtask.resources=self.__requestors.get(memtask.request_id)
            self.__update_task_status(memtask, TaskStatus.fueled)
    
    def __update_task_status(self, task, status):
        #task.status=status    
        self.db.update_task_status(task=task.id_, status=status)
        
    def __release_task_resources(self, task):
        step=self.__steps[task.step_id]
        module_logger.debug("Releasing task resources %s: %s" % (step.name, step.releases))
        if step.releases is not None:
            self.__requestors.put_requested(step.releases)

    def __allocate_resources_for_task(self, task, previous_task=None):
        ''' Request resources for task.  
            
        When satisfied, change status to .
        '''
        step=self.__steps[task.step_id]
        
        memtask=self.__tasks.get(task.id_, None)
        if memtask is None:
            memtask=Memtask(task)
            self.__tasks[task.id_]=memtask
        # need to allocate resources from all requested pools.
        # requests uses callback as a method to request all resources 
        # once all resources are collected, task is satisfied.
        
        #ResourceAllocationCallback(self.__resource_notification_queue)
        
        if not memtask.fueled :
            # not requested resources yet
            rp_callback=RpCallback(self.__rp_notify, task_id=task.id_)
            #requestors=vrp.Requestors(request=step.acquires, callback=rp_callback, audit=False)
            module_logger.debug("Going to reserve resources %s: %s" % (step.name, step.acquires, ))
            memtask.request_id=self.__requestors.reserve(request=step.acquires, callback=rp_callback)
            self.__update_task_status(memtask, TaskStatus.allocate)
            
    def __loop_task(self,):
        ''' evaluate ready tasks to initiate.
        
        loop_task will do its work only if eventor state is active.
        '''
        loop_seq=Sequence('_EventorTaskLoop')
        self.loop_id=loop_seq() 
        
        # all items are pulled so active can also be monitored for timely end
        if self.state==EventorState.active:
            module_logger.debug("Going to fetch tasks: %s: recovery: %s" % (self.name, self.recovery, ))
            tasks=self.db.get_task_iter(recovery=self.recovery,status=[TaskStatus.ready, TaskStatus.allocate, TaskStatus.fueled, TaskStatus.active ])
            for task in tasks:
                step=self.__steps[task.step_id]
                try:
                    previous_task=self.previous_tasks[task.sequence][task.step_id]
                except (KeyError, TypeError):
                    previous_task=None
                
                if task.status == TaskStatus.fueled or (task.status == TaskStatus.ready and not step.acquires):
                    self.__initiate_task(task, previous_task)
                elif task.status == TaskStatus.ready : # task.status == TaskStatus.ready and has resources to satisfy
                    self.__allocate_resources_for_task(task, previous_task)
                elif TaskStatus.allocate:
                    # TODO: check if expired - if so, halt
                    pass
                else: # active
                    # TODO: check run time allowance passed - if so, halt
                    pass
                    
        result=self.__collect_results()
        
        return result

    def __loop_once(self, ):
        ''' run single iteration over triggers to see if other events and associations needs to be launched.
        
        loop event: to see if new triggers matured
        loop task: to see if there is anything to run 
        '''
        self.__loop_event()
        result = self.__loop_task()
        self.__loop_trigger_request()
        self.__loop_awating_resource_allocation()
        return result
    
    def __check_control(self):
        loop=True
        if not self.__controlq.empty():
            msg=self.__controlq.get()        
            if msg:
                loop=msg not in [LoopControl.stop]
                #self.act=msg in [LoopControl.start]
        return loop
    
    def count_todos(self, sequence=None):
        module_logger.debug('[Step %s/%s] Counting todos; state: %s, recovery: %s' % (self.name, sequence, self.state, self.recovery))
        todo_triggers=0
        task_to_count=[TaskStatus.active, TaskStatus.fueled, TaskStatus.allocate, TaskStatus.ready,]
        if self.state == EventorState.active:
            todo_triggers=self.db.count_trigger_ready(sequence=sequence, recovery=self.recovery)
        else:
            task_to_count=[TaskStatus.active,]                 
        active_and_todo_tasks=self.db.count_tasks(status=task_to_count, sequence=sequence, recovery=self.recovery) 
        total_todo=todo_triggers + active_and_todo_tasks                       
        module_logger.debug('[Step %s/%s] total todo: %s (triggers: %s, tasks: %s)' % (self.name, sequence, total_todo, todo_triggers, active_and_todo_tasks))
        return total_todo

    def count_todos_like(self, sequence):
        ''' Counts items that are about to be in process, or in process.
        
        Args:
            sequence: (str) the sequence prefix to search for
            
        Returns:
            Count of in process 
        '''
        module_logger.debug('[Step %s/%s] Counting todos; state: %s, recovery: %s' % (self.name, sequence, self.state, self.recovery))
        todo_triggers=0
        task_to_count=[TaskStatus.active, TaskStatus.fueled, TaskStatus.allocate, TaskStatus.ready,]
        # If step (mega-step) is active, needs to add triggers ready.
        # else, we need to take only those tasks tat are active
        if self.state == EventorState.active:
            todo_triggers=self.db.count_trigger_ready_like(sequence=sequence, recovery=self.recovery)
        else:
            # since step is not active, we are interested only with active steps with in this mega-step.
            task_to_count=[TaskStatus.active,]                 
        active_and_todo_tasks=self.db.count_tasks_like(status=task_to_count, sequence=sequence, recovery=self.recovery) 
        total_todo=todo_triggers + active_and_todo_tasks                       
        module_logger.debug('[Step %s/%s] total todo: %s (triggers: %s, tasks: %s)' % (self.name, sequence, total_todo, todo_triggers, active_and_todo_tasks))
        return total_todo

    def loop_session_start(self):
        ''' loops until there is no work to do
        
        Each loop is consist from:
            1. one processing log, 
            2. check if there is still work to do, 
            3. sleep give CPU a break
            4. check if forced to stop
        
        '''
        module_logger.debug('Starting loop session')
        sleep_loop=self.__config['sleep_between_loops']
        loop=True
        self.db.set_thread_synchronization(True)
        
        while loop:
            result=self.__loop_once()
            # count ready triggers only if state is active
            # count ready tasks only if active
            total_todo=self.count_todos()                       
            loop=total_todo>0 
            if loop:
                loop=self.__check_control()
                if loop:
                    time.sleep(sleep_loop)
                    loop=self.__check_control()
                if not loop:
                    module_logger.info('Processing stopped')
            else:
                human_result="success" if result else 'failure'
                module_logger.info('Processing finished with: %s' % human_result)
        self.logger.stop()     
        return result
    
    def loop_session_stop(self):
        self.__controlq.put(LoopControl.stop)
        
    def get_step_sequence(self):
        result=os.environ.get('EVENTOR_STEP_SEQUENCE', '')
        return result
    
    def get_step_name(self):
        result=os.environ.get('EVENTOR_STEP_NAME', '')
        return result
    
    def get_task_status(self, task_names, sequence,):
        result=self.db.get_task_status(task_names=task_names, sequence=sequence, recovery=self.recovery)
        return result
        
    def __call__(self, ):
        #self.filename=self.get_filename(filename, self.calling_module)
        #module_logger.debug(str(self))
        result=self.loop_session_start()
        return result