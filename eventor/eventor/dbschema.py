'''
Created on Oct 21, 2016

@author: arnon
'''

from sqlalchemy import Column, UniqueConstraint, Sequence, create_engine
from sqlalchemy import Integer, BigInteger, String, PickleType, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from sqlalchemy import Enum as SQLEnum

from eventor.eventor_types import TaskStatus
from email.mime import base
from asyncio.tasks import Task
from collections import namedtuple
from namedlist import namedlist

#Base = declarative_base()

Info=namedlist("InfoRow", "name value")
def info_from_db(tobj):
    result=Info(tobj.name, tobj.value)
    return result
def info_to_db(obj, tcls):
    result=tcls(obj.name, obj.value)
    return result
def info_table(base):
    class Info(base):
        __tablename__ = 'Info'
        
        #id=Column(Integer, Sequence('info_id_seq'), primary_key=True)
        name=Column(String, primary_key=True)
        value=Column(String, nullable=True)
        
        __table_args__ = (
                UniqueConstraint('name'),
                )
    
        def __repr__(self):
            return "<Info(name='%s', value='%s')>" % (self.name, self.value)
        
    return Info

Trigger=namedlist("Trigger", "id_ event_id sequence recovery created acted")
def trigger_from_db(tobj):
    result=Trigger(tobj.id_, tobj.event_id, tobj.sequence, tobj.recovery, tobj.created, tobj.acted)
    return result
def trigger_to_db(obj, tcls):
    result=tcls(obj.id_, obj.eveny_id, obj.sequence, obj.recovery, obj.created, obj.acted)
    return result
def trigger_table(base):
    class Trigger(base):
        __tablename__ = 'Trigger'
        
        id_=Column(Integer, Sequence('trigger_id_seq'), primary_key=True)
        event_id=Column(String, nullable=False)
        sequence=Column(Integer, nullable=False)
        recovery=Column(Integer, nullable=False, default=0)
        created=Column(DateTime(), default=datetime.utcnow) 
        acted=Column(DateTime(), nullable=True) 
    
        def __repr__(self):
            return "<Trigger(id='%s', event_id='%s', sequence='%s', recovery='%s', created='%s', acted='%s')>" % (
                self.id_, self.event_id, self.sequence, self.recovery, self.created, self.acted)
    
    return Trigger

Task=namedlist("Task", "id_ step_id sequence recovery pid status result created updated")        
def task_from_db(tobj):
    result=Task(tobj.id_, tobj.step_id, tobj.sequence, tobj.recovery, tobj.pid, tobj.status, tobj.result, tobj.created, tobj.updated)
    return result
def task_to_db(obj, tcls):
    result=tcls(obj.id_, obj.step_id, obj.sequence, obj.recovery, obj.pid, obj.status, obj.result, obj.created, obj.updated)
    return result
def task_table(base):
    class Task(base):
        __tablename__ = 'Task'
        
        id_=Column(Integer, Sequence('task_id_seq'), primary_key=True)
        step_id=Column(String, )
        sequence=Column(Integer, )
        recovery=Column(Integer, nullable=False)
        pid=Column(Integer, nullable=True)
        status=Column(SQLEnum(TaskStatus), ) 
        result=Column(PickleType() , nullable=True,)
        created=Column(DateTime(), default=datetime.utcnow) 
        updated=Column(DateTime(), nullable=True, ) 
        
        __table_args__ = (
                UniqueConstraint('step_id', 'sequence', 'recovery'),
                )
    
        def __repr__(self):
            return "<Task(id='%s', step_id='%s', sequence='%s', recovery='%s', pid='%s', status='%s', created='%s', updated='%s')>" % (
                self.id_, self.step_id, self.sequence, self.recovery, self.pid, self.status, self.created, self.updated)
    
    return Task

Delay=namedlist("Delay", "id_ delay_id sequence recovery seconds active activated updated")
def delay_from_db(tobj):
    result=Delay(tobj.id_, tobj.delay_id, tobj.sequence, tobj.recovery, tobj.seconds, tobj.active, tobj.activated, tobj.updated)
    return result
def delay_to_db(obj, tcls):
    result=tcls(obj.id_, obj.delay_id, obj.sequence, obj.recovery, obj.active, obj.activated, obj.updated)
    return result
def delay_table(base):
    class Delay(base):
        __tablename__ = 'Delay'
        
        id_=Column(Integer, Sequence('delay_id_seq'), primary_key=True)
        delay_id=Column(String, )
        sequence=Column(Integer, )
        recovery=Column(Integer, )
        seconds=Column(BigInteger, nullable=True)
        active=Column(Boolean, default=False)
        activated=Column(DateTime(), nullable=True,) 
        updated=Column(DateTime(), default=datetime.utcnow) 
        
        __table_args__ = (
                UniqueConstraint('delay_id', 'sequence', 'recovery'),
                )
    
        def __repr__(self):
            return "<Delay(id='%s', delay_id='%s', delay='%s', active='%s, activated='%s')>" % (
                self.id_, self.delay_id, self.seconds, self.active, self.activated)
    
    return Delay   
 
'''
class Step(Base):
    __tablename__ = 'Step'
    
    id_ = Column(String, primary_key=True)
    name=Column(String, primary_key=True)
    created=Column(DateTime(), nullable=False, default=datetime.datetime.utcnow) 
    
    __table_args__ = (
            UniqueConstraint('name'),
            )

    def __repr__(self):
        return "<Step(id='%s', name='%s', created='%s')>" % (
            self.id_, self.name, self.created)
    
        
class Event(Base):
    __tablename__ = 'Event'
    
    id_=Column(String, primary_key=True)
    name=Column(String, nullable=False,)
    created=Column(DateTime(), nullable=False, default=datetime.datetime.utcnow) 
    
    __table_args__ = (
            UniqueConstraint('name'),
            )

    def __repr__(self):
        return "<event_id='%s', name='%s', created='%s'')>" % (
            self.id_,  self.expr, self.created, self.resolved)

class Assoc(Base):
    __tablename__ = 'Assoc'
    
    id_=Column(Integer, Sequence('assoc_id_seq'), primary_key=True)
    event_id=Column(String, nullable=False)
    obj_type=Column(SQLEnum(AssocType), nullable=False)
    obj_id=Column(String, nullable=False) 
    created=Column(DateTime(), nullable=False, default=datetime.datetime.utcnow) 
    
    __table_args__ = (
            UniqueConstraint('id_', 'obj_type', 'obj_id'),
            )

    def __repr__(self):
        return "<Assoc(assoc_id='%s', event_id='%s', obj_type='%s', obj_id='%s', created='%s')>" % (
            self.id_, self.event_id, self.obj_type, self.obj_id, self.created)

class Registry(Base):
    __tablename__ = 'Registry'
    registry_id=Column(Integer, Sequence('registry_id_seq'), primary_key=True)
    task_id=Column(Integer, primary_key=True)
    value=Column(PickleType())
'''
        
if __name__ == '__main__':
    #engine = create_engine('sqlite:///:memory:', echo=True)
    file='/var/acrisel/sand/eventor/eventor/eventor/eventor/schema.db'
    dns='sqlite:///' + file
    try:
        import os
        os.remove(file)
    except FileNotFoundError:
        pass
    
    Base=declarative_base()
    engine = create_engine(dns, echo=True)
    Info=info_table(Base)
    Trigger=trigger_table(Base)
    Task=task_table(Base)
    Delay=delay_table(Base)
    Base.metadata.create_all(engine)
    
    '''
    from sqlalchemy import MetaData
    from sqlalchemy_schemadisplay import create_schema_graph
    
    graph = create_schema_graph(
      metadata = MetaData(dns),
      show_datatypes=True, # The image would get nasty big if we'd show the datatypes
      show_indexes=True, # ditto for indexes
      #rankdir='LR', # From left to right (instead of top to bottom)
      concentrate=True # Don't try to join the relation lines together
    )

    graph.write_png('schema.png')
    '''
    
    from sqlalchemy.orm import sessionmaker
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    db_task=Task(step_id='34',status=TaskStatus.ready , sequence='45')
    session.add(db_task)
    session.flush() 
    session.commit() 
    
    db_trigger=Trigger(event_id='46' , sequence='45')
    session.add(db_trigger)
    session.flush() 
    session.commit() 

    db_info=Info(name='46' , value='45')
    session.add(db_info)
    session.flush() 
    session.commit() 

    