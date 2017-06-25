'''
Created on Oct 21, 2016

@author: arnon
'''

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
import logging
import os
import sys
import sqlite3
import multiprocessing 
import threading
from datetime import datetime

from eventor.dbschema import task_table, trigger_table, delay_table, info_table
from eventor.dbschema import Trigger, trigger_from_db, trigger_to_db
from eventor.dbschema import Task, task_from_db, task_to_db
from eventor.dbschema import Delay, delay_from_db, delay_to_db
from eventor.eventor_types import DbMode, Invoke
from eventor.utils import decorate_all, print_method
from eventor.sqladburl import SQLAlchemyConf

module_logger=logging.getLogger(__name__)
#logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

class DbApiError(Exception): pass

#class DbApiReplca(metaclass=decorate_all(print_method(module_logger.debug))):
class DbApiReplca(object):
    def __init__(self, db_mode=DbMode.read, mode='proess', value=None):
        self.mode=mode
        self.value=value
        self.db_mode=db_mode
            
    def initialize(self):
        if self.mode=='process':
            return DbApi(runfile=self.value, mode=self.db_mode)
        else:
            #session=scoped_session(sessionmaker(bind=self.value)) 
            return DbApi(session=self.value)
        
        
def get_sqlalchemy_conf(modulefile, userstore, config, root=None, echo=False):
    '''
        If userstore is provided:
            If it is a database key in config:
                use that database
            elif ':memory:':
                use in-memory
            else:
                use as runfile
        elif database has default key:
            use default database
        elif modulefile  is provided:
            use modulefile
        else:
            use memory
    '''
    
    if not root:
        root=os.environ.get('EVENTOR_DB_CONFIG_TAG', 'DATABASES')
        
    database=userstore if userstore else 'default'
    try:
        sqldb=SQLAlchemyConf(conf=config, root=root, database=database, quiet=False, echo=echo)
    except Exception:
        if userstore==':memory:':
            conf={'DB': {'db': {'dialect': 'sqlite', 'query': {'cache':'shared'}}}}
        elif userstore:
            conf={'DB': {'db': {'dialect': 'sqlite', 'database':userstore,}}} # 'query': {'cache':'shared'}}}}
        elif modulefile:
            conf={'DB': {'db': {'dialect': 'sqlite', 'database':modulefile,}}} # 'query': {'cache':'shared'}}}}
        else:
            conf={'DB': {'db': {'dialect': 'sqlite', 'query': {'cache':'shared'}}}}
            
        module_logger.debug("Using adhoc DB config: %s" %(repr(conf)))
        sqldb=SQLAlchemyConf(conf=conf, root='DB', database='db',quiet=True, echo=echo)
        
        
    return sqldb
 
#class DbApi(metaclass=decorate_all(print_method(module_logger.debug))):   
class DbApi(object):

    def __init__(self, modulefile=None, userstore=None, session=None, mode=DbMode.write, config={}, root=None, thread_sync=False, echo=False):
        '''
        Args:
            moduefile (path): file in which Eventor data would be stored and managed for reply/restart 
            if the value is :memory:, an in-memory temporary structures will be used
            userstore (path): store file provided by user
            
        Devising storage:
            If Store is provided:
                If it is a database key in config:
                    use that database
                else:
                    use as runfile
            else:
                if database has default key:
                    use default database
                else:
                    use modulefile if provided
        

        '''
        self.engine=None
        self.session=None
        self.runfile=None
        self.thread_sync=thread_sync
        
        self.__sqlalchemy=get_sqlalchemy_conf(modulefile, userstore, config, root=root, echo =echo)
        self.metadata=metadata=self.__sqlalchemy.get_metadata()
        
        Base = declarative_base(metadata=metadata)
        self.Info=info_table(Base)
        self.Task=task_table(Base)
        self.Delay=delay_table(Base)
        self.Trigger=trigger_table(Base)

        
        #if runfile:
        #    self.open(runfile, mode=mode) 
        if session:
            self.session = session()   
        else:
            #self.open(mode=mode) 
            self.session=self.__sqlalchemy.get_session()
        self.open(mode=mode) 
            
        self.db_transaction_lock=threading.Lock()
    
    def set_thread_synchronization(self, value=True):
        self.thread_sync=value
        
    def lock(self):
        if self.thread_sync:
            self.db_transaction_lock.acquire()
            
    def release(self):
        if self.thread_sync:
            self.db_transaction_lock.release()
    
    '''
    def open(self, mode=DbMode.write):
        if self.runfile != runfile:
            if mode == DbMode.write:
                try:
                    os.remove(runfile)
                except FileNotFoundError:
                    pass                
            self.runfile=runfile
            
            if mode == DbMode.write:
                self.create_db(runfile)  
            else:
                self.__create_engine(runfile,)
            self.set_session() 
    '''
    
    def open(self, mode=DbMode.write):
        if mode == DbMode.write:
            # try to remove existing eventor run from database
            # TODO: delete from tables
            pass
        
        if mode == DbMode.write:
            self.create_db()  
       
    '''
    def get_create_params(self, runfile):
        if runfile.startswith(':memory:'):
            PY2 = sys.version_info.major == 2
            if PY2:
                params = {}
            else:
                params = {'uri': True}
            dns='sqlite://?cache=shared'
            DB_URI = 'file::memory:?cache=shared'
            creator = lambda: sqlite3.connect(DB_URI, **params)
        else:    
            dns= 'sqlite:///' + runfile
            creator=None
        return dns, creator
    
    def __create_engine(self, runfile):
        dns, creator=self.get_create_params(runfile)
        if creator:
            self.engine = create_engine(dns, creator=creator, echo=False, connect_args={'check_same_thread':False})
        else:
            self.engine = create_engine(dns, echo=False, connect_args={'check_same_thread':False}) 
    
    def set_session(self,):
        if not self.session:
            self.session_factory=sessionmaker(bind=self.metadata.bind.engine)
            self.Session = scoped_session(self.session_factory)
            self.session = self.Session()
        return self.session
    '''
            
    def close(self):
        self.session.remove()
    
    def replicate(self, target=multiprocessing.Process):
        if target == multiprocessing.Process:
            mode='process'
            value=self.runfile
        elif target==threading.Thread:
            mode='thread'
            value=self.Session
        elif target==Invoke:
            mode='thread'
            value=self.Session
        return DbApiReplca(mode=mode, value=value)
    
    def create_schema(self):
        metadata=self.metadata
        schemas = set()
        for table in metadata.tables.values():
            if table.schema is not None:
                schemas.add(table.schema)
        for schema in schemas:
            metadata.bind.execute("DROP SCHEMA IF EXISTS %s CASCADE " % schema)
            metadata.bind.execute("CREATE SCHEMA IF NOT EXISTS %s" % schema)

        
    def create_db(self, ):
        #self.__create_engine(runfile)
        self.create_schema()
        self.metadata.create_all()
        
    def commit_db(self):
        self.session.flush()
        self.session.commit()
        
    '''
    def read_db(self, runfile):
        # TODO: fix to serve resume
        self.__create_engine(runfile)
    '''
           
    def write_info(self, **info):
        self.lock()
        for name, value in info.items():
            db_info=self.Info(name=name, value=value)
            self.session.add(db_info)
            self.commit_db()
        self.release()
        
    def read_info(self, ):
        self.lock()
        rows = self.session.query(self.Info).all()
        self.release()
        info=dict()
        for row in rows:
            info[row.name]=row.value
        return info
        
    def update_info(self, **info):
        self.lock()
        for name, value in info.items():
            self.session.query(self.Info).filter(self.Info.name==name).update({self.Info.name:name, self.Info.value:value}, synchronize_session=False)
        self.release()
        
    '''
    def add_step(self, step_id, name):
        db_step=Step(id=step_id, name=name)
        self.session.add(db_step)
        self.commit_db()
       
    def add_event(self, event_id, name):
        db_event=Event(id=event_id, name=name, )
        self.session.add(db_event) 
        self.commit_db()
        
    def add_assoc(self, event_id, obj_type, obj_id):
        db_assoc=Assoc(event_id=event_id, obj_type=obj_type, obj_id=obj_id)
        self.session.add(db_assoc)
    '''
        
    def get_trigger_iter(self, recovery):
        self.lock()
        rows = self.session.query(self.Trigger).filter(self.Trigger.recovery==recovery)
        #rows = query.statement.execute().fetchall()
        self.release()
        for row in rows:
            yield trigger_from_db(row)
        #return rows
    
    def get_trigger_map(self, recovery=0):
        self.lock()
        triggers = self.session.query(self.Trigger).filter(recovery==recovery)
        self.release()
        trigger_map=dict()
        for trigger in triggers:
            try:
                sequence_map=trigger_map[trigger.sequence]
            except KeyError:
                sequence_map=dict()
                trigger_map[trigger.sequence]=sequence_map
            sequence_map[trigger.event_id]=trigger_from_db(trigger)
        return trigger_map
        
    '''
    def get_event_iter(self, ):
        rows = self.session.query(Event).all() #.filter(Event.name==u'john')
        # rows = query.statement.execute().fetchall()
        return rows
        
    def get_event(self, expr):
        row = self.session.query(Event).filter(Event.expr==expr).first()
        #row = session.execute(query.statement).fetchone()
        return row
        
    def update_event_expr(self, rowid, value):
        stmt=update(Event).where(id=rowid).values(expr=value)
        try:
            rows=self.session.execute(stmt)
        except Exception:
            raise
        else:
            self.commit_db()
        return rows
    '''
        
    def add_trigger(self, event_id, sequence, recovery):
        #print("add_trigger", event_id, self.session)
        trigger=self.Trigger(event_id=event_id, sequence=sequence, recovery=recovery)
        self.lock()
        self.session.add(trigger)
        self.commit_db()
        self.release()
        return trigger_from_db(trigger)
        
    def add_trigger_if_not_exists(self, event_id, sequence, recovery):
        self.lock()
        trigger=self.session.query(self.Trigger).filter(self.Trigger.event_id==event_id, self.Trigger.sequence==sequence, self.Trigger.recovery==recovery).first()
        #print("add_trigger", event_id, sequence, recovery, found)
        if trigger is None:
            trigger=self.Trigger(event_id=event_id, sequence=sequence, recovery=recovery)
            self.session.add(trigger)
            self.commit_db()
        self.release()
        return trigger_from_db(trigger)
    
    def _get_trigger(self, trigger):
        rows = self.session.query(self.Trigger).filter(self.Trigger.id_==trigger.id_)
        try: return rows[0]
        except: return None
    
    def acted_trigger(self, trigger):
        self.lock()
        db_trigger=self._get_trigger(trigger)
        trigger.acted=db_trigger.acted=datetime.utcnow()
        #self.session.add(trigger)
        self.commit_db()
        self.release()
        return trigger
    
    def count_trigger_ready(self, sequence=None, recovery=None ):
        self.lock()
        members=self.session.query(self.Trigger).filter(self.Trigger.acted == None, self.Trigger.recovery==recovery)
        if sequence:
            members=members.filter(self.Trigger.sequence==sequence)
        count=members.count()
        self.release()
        return count
        
    def count_trigger_ready_like(self, sequence, recovery):
        self.lock()
        try:
            members=self.session.query(self.Trigger).filter(self.Trigger.sequence.like(sequence), self.Trigger.acted == None, self.Trigger.recovery==recovery)
        except:
            self.release()
            raise
        count=members.count()
        self.release()
        return count
        
    '''
    def get_assoc_iter(self, event):
        rows = self.session.query(Assoc).filter(Assoc.event_id==event.event_id).all()
        # rows = query.statement.execute().fetchall()
        return rows
        
    def get_step(self, step_id):
        row=self.session.query(Step).filter(Step.step_id==step_id).first()
        #row = query.statement.execute().fetchone()
        return row
    '''
        
    def add_task(self, step_id, sequence, status, recovery=None):
        self.lock()
        task=self.Task(step_id=step_id, sequence=sequence, status=status, recovery=recovery)
        self.session.add(task)
        self.commit_db()
        self.release()
        return task_from_db(task)
        
    def add_task_if_not_exists(self, step_id, sequence, status, recovery=None):
        self.lock()
        task=self.session.query(self.Task).filter(self.Task.sequence==sequence, self.Task.step_id == step_id, self.Task.recovery==recovery).first()
        if task is None:
            task=self.Task(step_id=step_id, sequence=sequence, status=status, recovery=recovery)
            self.session.add(task)
            self.commit_db()
        self.release()
        result=task_from_db(task)
        module_logger.debug('DBAPI - add_task_if_not_exists: %s' % (repr(result), ))
        return result
        
    def update_task(self, task, session=None):
        self.lock()
        if not session:
            session=self.session
        task.updated=updated=datetime.utcnow()
        updates={self.Task.status:task.status, self.Task.updated: updated,}
        if task.pid:
            updates[self.Task.pid]=task.pid                            
        if task.result:
            updates[self.Task.result]=task.result                                                                   
        self.session.query(self.Task).filter(self.Task.id_==task.id_).update(updates, synchronize_session=False)
        self.commit_db()
        self.release()
        module_logger.debug('DBAPI - update_task: %s' % (repr(task), ))
        return task
        
    def update_task_status(self, task, status, session=None,):
        self.lock()
        #if isinstance(task, int):
        #    task_id=task
        #elif isinstance(task, Task):
        #    task_id=task.id_
        #else:
        #    raise DbApiError("Unknown task type (%s), expected int or Task" % (type(task), ))
        
        task_id=task.id_
        
        if not session:
            session=self.session
        task.updated=updated=datetime.utcnow()
        task.status=status
        module_logger.debug('updating task status: %s(%s)' % (task_id, status))
        updates={self.Task.status: status, self.Task.updated: updated,}                                               
        self.session.query(self.Task).filter(self.Task.id_==task_id).update(updates, synchronize_session=False)
        self.commit_db()
        self.release()
        return task
        
    def get_task_iter(self, recovery, status=None):
        # TODO: do we really need recovery here
        self.lock()
        rows = self.session.query(self.Task)
        if status:
            rows = self.session.query(self.Task).filter(self.Task.status.in_(status)).all()
        else:
            rows = self.session.query(self.Task).all()
        self.release()
        for row in rows:
            result=task_from_db(row)
            module_logger.debug("task_iter: task: %s" %(repr(result)))
            yield  result
    
    def get_task_map(self, recovery=0):
        self.lock()
        tasks = self.session.query(self.Task).filter(recovery==recovery)
        task_map=dict()
        for task in tasks:
            try:
                sequence_map=task_map[task.sequence]
            except KeyError:
                sequence_map=dict()
                task_map[task.sequence]=sequence_map
            sequence_map[task.step_id]=task_from_db(task)
        self.release()
        module_logger.debug("get_task_map: task: %s" %(repr(task_map)))
        return task_map
    
    def count_tasks(self, recovery, status, sequence=None):
        self.lock()
        #print("Counting status: %s, sequence: %s" % (status, sequence))
        with self.session.no_autoflush:
            members=self.session.query(self.Task)
        #for member in members:
        #    print(member)
        members=members.filter(self.Task.status.in_(status), self.Task.recovery==recovery)
        if sequence:
            members=members.filter(self.Task.sequence==sequence)
        count=members.count()
        self.release()
        return count
    
    def count_tasks_like(self, sequence, recovery, status):
        self.lock()
        with self.session.no_autoflush:
            members=self.session.query(self.Task).filter(self.Task.sequence.like(sequence), self.Task.status.in_(status), self.Task.recovery==recovery)
        count=members.count()
        self.release()
        return count
    
    def get_task_status(self, task_names, sequence, recovery):
        self.lock()
        tasks=self.session.query(self.Task).filter(self.Task.step_id.in_(task_names), self.Task.sequence==sequence, self.Task.recovery==recovery).all()
        result=dict()
        for task in tasks:
            result[task.step_id]=task.status        
        self.release()
        module_logger.debug("get_task_status: task: %s" %(repr(result)))
        return result
 
    def add_delay(self, delay_id, sequence, seconds, active=None, activated=None, recovery=None):
        delay=self.Delay(delay_id=delay_id, seconds=seconds, sequence=sequence, recovery=recovery,)
        self.lock()
        try:
            self.session.add(delay)
        except IntegrityError:
            self.release()
            raise
        self.commit_db()
        self.release()
        return delay_from_db(delay)
        
    def add_delay_update_if_not_exists(self, delay_id, sequence, seconds, active=None, activated=None, recovery=None):
        '''try:
            delay=self.add_delay(delay_id, sequence, seconds, active, activated, recovery)
        except IntegrityError:
            self.lock()
            delay=Delay(delay_id=delay_id, sequence=sequence, recovery=recovery)
            self.release()
            '''
        self.lock()
        delay=self.session.query(self.Delay).filter(self.Delay.sequence==sequence, self.Delay.delay_id == delay_id, self.Delay.recovery==recovery).first()
        if delay is None:
            delay=self.Delay(delay_id=delay_id, seconds=seconds, sequence=sequence, recovery=recovery, active=active, activated=activated)
            module_logger.debug('DBAPI - add_delay_if_not_exists: %s' % (repr(delay), ))
            self.session.add(delay)
            self.commit_db()
        elif delay.active != active:
            if active: delay.activated=datetime.utcnow()
            delay.active=active
            self.commit_db()
        self.release()
        return delay_from_db(delay)
        
    def get_delay_map(self, recovery=0):
        self.lock()
        items = self.session.query(self.Delay).filter(recovery==recovery)
        self.release()
        item_map=dict()
        for item in items:
            try:
                sequence_map=item_map[item.sequence]
            except KeyError:
                sequence_map=dict()
                item_map[item.sequence]=sequence_map
            sequence_map[item.delay_id]=delay_from_db(item)
        return item_map

    def get_delay_iter(self, recovery, active=True):
        self.lock()
        rows = self.session.query(self.Delay).filter(self.Delay.recovery==recovery)
        #rows = query.statement.execute().fetchall()
        self.release()
        for row in rows:
            yield delay_from_db(row)
  
    def _get_delay(self, delay):
        self.lock()
        rows = self.session.query(self.Delay).filter(self.Delay.id_==delay.id_)
        #rows = query.statement.execute().fetchall()
        self.release()
        try: return rows[0]
        except: return None
  
    def activate_delay(self, delay):
        self.lock()
        db_delay = self._get_delay(delay)
        delay.activated=db_delay.activated=datetime.utcnow()
        delay.active=True
        self.commit_db()
        self.release()
        return delay
        
    def deactivate_delay(self, delay):
        self.lock()
        db_delay = self._get_delay(delay)
        delay.active=db_delay.active=False
        self.commit_db()
        self.release()
        return delay

    def count_active_delays(self, sequence, recovery,):
        self.lock()
        with self.session.no_autoflush:
            members=self.session.query(self.Delay)
            members=members.filter(self.Delay.recovery==recovery, self.Delay.active.is_(True))
        
        now=datetime.utcnow()
        time_to_mature=[m.seconds-(now-m.activated).total_seconds() for m in members]
        min_time_to_mature = min(time_to_mature) if len(time_to_mature) > 0 else None
        count=members.count()
        self.release()
        return count, min_time_to_mature
    
        
 
if __name__ == '__main__':
    import pickle
    file='/var/acrisel/sand/eventor/eventor/eventor/eventor/schema.db'
    #file=':memory:'
    mydb=DbApi(userstore='sqfile', root='eventor.databases', config='dbapi.conf')
    # mydb.add_event(event_id='34', name='evently')
    mydb.commit_db()
    delay=mydb.add_delay(delay_id='mydelay', seconds=2419200, sequence=3, )
    print(repr(delay))
    delay=mydb.activate_delay(delay)
    print(repr(delay))
    delay=mydb.deactivate_delay(delay)
    print(repr(delay))
    mydb.commit_db()
    task=mydb.Task()
