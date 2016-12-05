'''
Created on Oct 21, 2016

@author: arnon
'''

from sqlalchemy import create_engine
from sqlalchemy.sql.expression import update
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.scoping import scoped_session
from sqlalchemy.exc import IntegrityError
import logging
import os
import sys
import sqlite3
import multiprocessing 
import threading
from enum import Enum

from eventor.dbschema import *
from eventor.eventor_types import DbMode

module_logger=logging.getLogger(__name__)
#logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

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

class DbApi(object):

    def __init__(self, runfile=None, session=None, mode=DbMode.write):
        self.engine=None
        self.session=None
        self.runfile=None
        
        if runfile:
            self.open(runfile, mode=mode) 
        elif session:
            self.session = session()   
        self.db_transaction_lock=threading.Lock()
    
    def lock(self):
        self.db_transaction_lock.acquire()
            
    def release(self):
        self.db_transaction_lock.release()
    
    def open(self, runfile, mode=DbMode.write):
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
                self.create_engine(runfile,)
            self.set_session() 
       
    def get_create_params(self, runfile):
        if runfile.startswith(':memory:'):
            PY2 = sys.version_info.major == 2
            if PY2:
                params = {}
            else:
                params = {'uri': True}
            dns='sqlite:///:memory:'
            DB_URI = 'file::memory:?cache=shared'
            creator = lambda: sqlite3.connect(DB_URI, **params)
        else:    
            dns= 'sqlite:///' + runfile
            creator=None
        return dns, creator
    
    def create_engine(self, runfile):
        dns, creator=self.get_create_params(runfile)
        if creator:
            self.engine = create_engine(dns, creator=creator, echo=False, connect_args={'check_same_thread':False})
        else:
            self.engine = create_engine(dns, echo=False, connect_args={'check_same_thread':False}) 
    
    def set_session(self):
        if not self.session:
            self.session_factory=sessionmaker(bind=self.engine)
            self.Session = scoped_session(self.session_factory)
            self.session = self.Session()
        return self.session
    
    def close(self):
        self.session.remove()
    
    def replicate(self, target=multiprocessing.Process):
        if target == multiprocessing.Process:
            mode='process'
            value=self.runfile
        elif target==threading.Thread:
            mode='thread'
            value=self.Session
        return DbApiReplca(mode=mode, value=value)
        
    def create_db(self, runfile):
        self.create_engine(runfile)
        Base.metadata.create_all(self.engine)
        
    def commit_db(self):
        self.session.flush()
        self.session.commit()
        
    def read_db(self, runfile):
        # TODO: fix to serve resume
        self.create_engine(runfile)
        
    def write_info(self, **info):
        self.lock()
        for name, value in info.items():
            db_info=Info(name=name, value=value)
            self.session.add(db_info)
            self.commit_db()
        self.release()
        
    def read_info(self, ):
        self.lock()
        rows = self.session.query(Info).all()
        self.release()
        info=dict()
        for row in rows:
            info[row.name]=row.value
        return info
        
    def update_info(self, **info):
        self.lock()
        for name, value in info.items():
            self.session.query(Info).filter(Info.name==name).update({Info.name:name, Info.value:value}, synchronize_session=False)
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
        rows = self.session.query(Trigger).filter(Trigger.recovery==recovery)
        #rows = query.statement.execute().fetchall()
        self.release()
        return rows
    
    def get_trigger_map(self, recovery=0):
        self.lock()
        triggers = self.session.query(Trigger).filter(recovery==recovery)
        self.release()
        trigger_map=dict()
        for trigger in triggers:
            try:
                sequence_map=trigger_map[trigger.sequence]
            except KeyError:
                sequence_map=dict()
                trigger_map[trigger.sequence]=sequence_map
            sequence_map[trigger.event_id]=trigger
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
        trigger=Trigger(event_id=event_id, sequence=sequence, recovery=recovery)
        self.lock()
        self.session.add(trigger)
        self.commit_db()
        self.release()
        
    def add_trigger_if_not_exists(self, event_id, sequence, recovery):
        self.lock()
        found=self.session.query(Trigger).filter(Trigger.event_id==event_id, Trigger.sequence==sequence, Trigger.recovery==recovery).first()
        #print("add_trigger", event_id, sequence, recovery, found)
        found=found is None
        if found:
            trigger=Trigger(event_id=event_id, sequence=sequence, recovery=recovery)
            self.session.add(trigger)
            self.commit_db()
        self.release()
        return found
    
    def acted_trigger(self, trigger):
        self.lock()
        trigger.acted=datetime.datetime.utcnow()
        #self.session.add(trigger)
        self.commit_db()
        self.release()
    
    def count_trigger_ready(self, sequence=None):
        self.lock()
        members=self.session.query(Trigger).filter(Trigger.acted == None)
        if sequence:
            members=members.filter(Trigger.sequence==sequence)
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
        
    def add_task(self, step_id, sequence, status=TaskStatus.ready, recovery=None):
        self.lock()
        task=Task(step_id=step_id, sequence=sequence, status=status,)
        self.session.add(task)
        self.commit_db()
        self.release()
        
    def add_task_if_not_exists(self, step_id, sequence, status=TaskStatus.ready, recovery=None):
        self.lock()
        found=self.session.query(Task).filter(Task.sequence==sequence, Task.step_id == step_id, Task.recovery==recovery).first()
        task=None
        if found is None:
            task=Task(step_id=step_id, sequence=sequence, status=status, recovery=recovery)
            module_logger.debug('DBAPI - add_task_if_not_exists: %s' % (repr(task), ))
            self.session.add(task)
            self.commit_db()
        self.release()
        return task
        
    def update_task(self, task, session=None):
        self.lock()
        if not session:
            session=self.session
        updated=datetime.datetime.utcnow()
        updates={Task.status:task.status, Task.updated: updated,}
        if task.pid:
            updates[Task.pid]=task.pid                            
        if task.result:
            updates[Task.result]=task.result                                                                   
        self.session.query(Task).filter(Task.id_==task.id_).update(updates, synchronize_session=False)
        self.commit_db()
        self.release()
        
    def get_task_iter(self, status=[TaskStatus.ready,]):
        self.lock()
        rows = self.session.query(Task).filter(Task.status.in_(status)).all()
        self.release()
        return rows  
    
    def get_task_map(self, recovery=0):
        self.lock()
        tasks = self.session.query(Task).filter(recovery==recovery)
        task_map=dict()
        for task in tasks:
            try:
                sequence_map=task_map[task.sequence]
            except KeyError:
                sequence_map=dict()
                task_map[task.sequence]=sequence_map
            sequence_map[task.step_id]=task
        self.release()
        return task_map
    
    def count_tasks(self, status=[TaskStatus.active, TaskStatus.ready,], sequence=None):
        self.lock()
        with self.session.no_autoflush:
            members=self.session.query(Task).filter(Task.status.in_(status))
        if sequence:
            members=members.filter(Task.sequence==sequence)
        count=members.count()
        self.release()
        return count
  
if __name__ == '__main__':
    file='/var/acrisel/sand/eventor/eventor/eventor/eventor/schema.db'
    #file=':memory:'
    mydb=DbApi(file)
    mydb.add_event(event_id='34', name='evently')
    mydb.commit_db()
    mydb.add_assoc(event_id='34', obj_type='step', obj_id='42')
    mydb.commit_db()
