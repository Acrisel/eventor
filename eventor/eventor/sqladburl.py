'''
Created on Jun 20, 2017

@author: arnon
'''

from sqlalchemy.engine.url import URL
from sqlalchemy import create_engine
from sqlalchemy.schema import MetaData 
from sqlalchemy.orm import sessionmaker, scoped_session
import logging
from eventor.conf_handler import getrootconf
import sys
import sqlite3

logger=logging.getLogger(__file__)

URL_ARGS=['drivername', 'username', 'password', 'host', 'port', 'database', 'query', 'file']
CONNECT_ARGS=['dialect', 'schema'] + URL_ARGS


def getdbinfo(conf=None, database=None, root='DATABASES', quiet=False, expand=True, expand_map=None):
    databases=getrootconf(conf=conf, root=root, expand=expand, expand_map=expand_map)
    db=None
    if database is not None:
        try: db=databases[database]
        except: 
            if not quiet:
                raise Exception("Database configuration not found for: %s"%(database))
            else: return None
    else: db=databases
    return db

def get_item(conf, tag, default=None, ):
    try:
        value=conf[tag]
    except Exception as e: 
        if not default:
            raise Exception("missing %s" % (tag)) from e
        value=default
    return value


def sqlite_url(dbconf, database):
    '''
    engine = create_engine('sqlite:///foo.db')
    engine = create_engine('sqlite:////absolute/path/to/foo.db')
    engine = create_engine('sqlite:///C:\\path\\to\\foo.db')
    engine = create_engine(r'sqlite:///C:\path\to\foo.db')
    engine = create_engine('sqlite://')
    '''
    creator=None
    
    file=dbconf.get('database')
    url_args=get_url_kwargs(dbconf, )
    url=URL(drivername='sqlite', **url_args)
    if not file:
        PY2 = sys.version_info.major == 2
        if PY2:
            params = {}
        else:
            params = {'uri': True}
            
        url_args_list=["%s=%s" % (k, v) for k, v in url_args.items()]
        url_args_str=''
        if url_args_list: url_args_str="?%s" % '&'.join(url_args_list)
        DB_URI = 'file::memory:%s' %(url_args_str)
        creator = lambda: sqlite3.connect(DB_URI, **params)
        
    kwargs=get_rest_kwargs(dbconf, ignore=CONNECT_ARGS, )
    if creator:
        kwargs['creator']=creator
    return url, kwargs

dialect_map={
    'sqlite': sqlite_url,
    }


def get_rest_kwargs(dbconf, ignore=[], ):
    kwargs=dict([(k,v) for k, v in dbconf.items() if k not in ignore])
    return kwargs

def get_url_kwargs(dbconf, ):
    kwargs=dict([(k,v) for k, v in dbconf.items() if k in URL_ARGS and k != 'drivername'])
    return kwargs

class SQLAlchemyConf(object):
    def __init__(self, conf=None, root='DATABASES', database=None, expand=True, expand_map=None, quiet=False, echo=False):
        self.conf=conf
        self.database=database
        self.dbconf=getdbinfo(conf=self.conf, root=root, database=self.database, expand=expand, expand_map=expand_map, quiet=quiet) 
        self.engine=None
        self.metadata=None
        self.session=None
        self.echo=echo
        
    def __repr__(self):
        return repr(self.dbconf)
        
    def get_info(self):
        return self.dbconf
          
    def get_url(self):
        dbconf=self.dbconf
        try:
            dialect=get_item(dbconf, 'dialect', )
        except Exception as e:
            raise Exception("dialect key missing in configuration for: %s" % (self.database)) from e

        func=dialect_map.get(dialect)
        
        if func:
            #except Exception as e:
            #raise Exception('unhandled dialect: %s, allow %s.' %(dialect, repr(list(dialect_map.keys())))) from e
            logger.debug('specialize map: %s' % repr(func))
            url, kwargs=func(dbconf, self.database)
        else:
            url_args=get_url_kwargs(dbconf, )
            try:
                url=URL(drivername=dialect, **url_args)
                # fetch other connection args (called query in sqlalchemy.engine.url.URL
            except Exception as e:
                raise Exception('Failed to create URL for : %s:%s' % (dialect, url_args.get('drivername'))) from e
            kwargs=get_rest_kwargs(dbconf, ignore=CONNECT_ARGS, )
            
        return url, kwargs
                    
    def get_engine(self, force=False):
        if self.engine and not force: return self.engine
        url, kwargs =self.get_url()
        self.engine=engine=create_engine(url, **kwargs, echo=self.echo, )
        return engine
        
    
    def get_metadata(self, force=False):
        if self.metadata and not force: return self.metadata
        dbconf=self.dbconf
        engine = self.get_engine(force=force)
        schema=dbconf.get('schema')
        self.metadata=metadata=MetaData(bind=engine, schema=schema)
        return metadata
    
    def get_session(self, force=False):
        if self.session and not force: return self.session
        session_factory=sessionmaker(bind=self.get_metadata(force=force).bind.engine)
        Session = scoped_session(session_factory)
        self.session=session=Session()
        return session

    
    

if __name__ == '__main__':
    url, connect_args=SQLAlchemyConf('db.conf', database='default').get_url()
    print(url, connect_args)
    
    dbconf=SQLAlchemyConf(conf='db.conf', database='playpg').get_info()
    url, connect_args=SQLAlchemyConf(dbconf,).get_url()
    print(url, connect_args)
    
    dbconf=SQLAlchemyConf(conf='db.conf', database='playmem').get_info()
    url, connect_args=SQLAlchemyConf(dbconf,).get_url()
    print(url, connect_args)

    dbconf=SQLAlchemyConf(conf='db.conf', database='playfile').get_info()
    url, connect_args=SQLAlchemyConf(dbconf,).get_url()
    print(url, connect_args)
    
    url, connect_args=SQLAlchemyConf('db.conf', database='playmy').get_url()
    print(url, connect_args)

    