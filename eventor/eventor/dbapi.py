'''
Created on Oct 21, 2016

@author: arnon
'''

from sqlalchemy import create_engine
from sqlalchemy.sql.expression import update
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import logging
import os

from eventor.dbschema import *
from eventor.eventor_types import DbMode

module_logger=logging.getLogger(__name__)

class DbApi(object):

    def __init__(self, runfile=None, mode=DbMode.write):
        self.engine=None
        self.session=None
        self.runfile=None
        
        if runfile:
            self.open(runfile, mode=mode)    
    
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
                self.create_engine(runfile)
            self.set_session() 
       
    def get_dns(self, runfile):
        dns='sqlite://'
        if runfile != ':memory:':
            dns= dns + '/' + runfile
        return dns
    
    def create_engine(self, runfile):
        dns=self.get_dns(runfile)
        self.engine = create_engine(dns, echo=False)
    
    def set_session(self):
        if not self.session:
            Session = sessionmaker(bind=self.engine)
            self.session = Session()
        return self.session
        
    def create_db(self, runfile):
        self.create_engine(runfile)
        Base.metadata.create_all(self.engine)
        
    def commit_db(self):
        self.session.flush()
        self.session.commit()
        
    def read_db(self, runfile):
        # TODO: fix to serve resume
        self.create_engine(runfile)
        
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
        
    def get_trigger_iter(self, ):
        rows = self.session.query(Trigger).all()
        #rows = query.statement.execute().fetchall()
        return rows
        
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
        
    def add_trigger(self, event_id, sequence):
        #print("add_trigger", event_id, self.session)
        trigger=Trigger(event_id=event_id, sequence=sequence)
        self.session.add(trigger)
        self.commit_db()
        
    def add_trigger_if_not_exists(self, event_id, sequence):
        found=self.session.query(Trigger).filter(Trigger.sequence==sequence, Trigger.event_id==event_id).first()
        #print("add_trigger", event_id, sequence, found)
        if found is None:
            trigger=Trigger(event_id=event_id, sequence=sequence)
            self.session.add(trigger)
            self.commit_db()
        return found is None
    
    def acted_trigger(self, trigger):
        trigger.acted=datetime.datetime.utcnow()
        #self.session.add(trigger)
        self.commit_db()
    
    def count_trigger_ready(self, ):
        count=self.session.query(Trigger).filter(Trigger.acted == None).count()
        return count
        
    def get_assoc_iter(self, event):
        rows = self.session.query(Assoc).filter(Assoc.event_id==event.event_id).all()
        # rows = query.statement.execute().fetchall()
        return rows    
    
    def get_step(self, step_id):
        row=self.session.query(Step).filter(Step.step_id==step_id).first()
        #row = query.statement.execute().fetchone()
        return row
        
    def add_task(self, step_id, sequence, status=TaskStatus.ready):
        task=Task(step_id=step_id, sequence=sequence, status=status,)
        self.session.add(task)
        self.commit_db()
        
    def add_task_if_not_exists(self, step_id, sequence, status=TaskStatus.ready):
        found=self.session.query(Task).filter(Task.sequence==sequence, Task.step_id == step_id).first()
        task=None
        if found is None:
            task=Task(step_id=step_id, sequence=sequence, status=status,)
            module_logger.debug('DBAPI - add_task_if_not_exists: %s' % (repr(task), ))
            self.session.add(task)
            self.commit_db()
        return task
        
    def update_task(self, task):
        updated=datetime.datetime.utcnow()
        updates={Task.status:task.status, Task.updated: updated,}
        if task.result:
            updates['result']=Task.result                                                                   
        self.session.query(Task).filter(Task.id==task.id).update(updates, synchronize_session=False)
        self.commit_db()
        
    def get_task_iter(self, status=[TaskStatus.ready,]):
        rows = self.session.query(Task).filter(Task.status.in_(status)).all()
        return rows  
    
    def count_tasks(self, status=[TaskStatus.active, TaskStatus.ready,]):
        count=self.session.query(Task).filter(Task.status.in_(status)).count()
        return count
  
if __name__ == '__main__':
    file='/var/acrisel/sand/eventor/eventor/eventor/eventor/schema.db'
    #file=':memory:'
    mydb=DbApi(file)
    mydb.add_event(event_id='34', name='evently')
    mydb.commit_db()
    mydb.add_assoc(event_id='34', obj_type='step', obj_id='42')
    mydb.commit_db()
