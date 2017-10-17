'''
Created on Oct 17, 2017

@author: arnon
'''

from sqlalchemy                 import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy                 import create_engine
from sqlalchemy.orm             import sessionmaker

engine = create_engine('sqlite:///:memory:', echo=True)
engine.execute("select 1").scalar() # works fine

Session = sessionmaker(bind=engine)
session = Session()
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    fullname = Column(String)
    password = Column(String)

    def __init__(self, name, fullname, password):
        self.name = name
        self.fullname = fullname
        self.password = password

    def __repr__(self):
        return "<User('%s','%s', '%s')>" % (self.name, self.fullname, self.password)

# Initialize database schema (create tables)
Base.metadata.create_all(engine)

jeff_user = User("jeff", "Jeff", "foo")
session.add(jeff_user)

our_user = session.query(User).filter_by(name='jeff').first() # fails here

jeff_user.password = "foobar"

session.add_all([
                User('wendy', 'Wendy Williams', 'foobar'),
                User('mary', 'Mary Contrary', 'xxg527'),
                User('fred', 'Fred Flinstone', 'blah')])

session.dirty # shows nothing as dirty
session.new   # shows nothing as new