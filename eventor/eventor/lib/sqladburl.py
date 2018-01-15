'''
Created on Jun 20, 2017

@author: arnon
'''

from sqlalchemy.engine.url import URL
from sqlalchemy import create_engine
from sqlalchemy.schema import MetaData
from sqlalchemy.orm import sessionmaker, scoped_session
import logging
from .conf_handler import getrootconf
import sys
import sqlite3

mlogger = logging.getLogger(__file__)

URL_ARGS = ['drivername', 'username', 'password', 'host', 'port', 'database', 'query', 'file']
CONNECT_ARGS = ['dialect', 'schema'] + URL_ARGS


def getdbinfo(conf=None, database=None, root='DATABASES', quiet=False, expand=True, expand_map=None):
    databases = getrootconf(conf=conf, root=root, expand=expand, expand_map=expand_map)
    db = None
    if database is not None:
        try:
            db = databases[database]
        except Exception:
            if not quiet:
                raise Exception("Database configuration not found for: %s" % (database))
            else:
                return None
    else:
        db = databases
    return db


def get_item(conf, tag, default=None, ):
    try:
        value = conf[tag]
    except Exception as e:
        if not default:
            raise Exception("missing %s" % (tag)) from e
        value = default
    return value


def sqlite_url(dbconf, database):
    '''
    engine = create_engine('sqlite:///foo.db')
    engine = create_engine('sqlite:////absolute/path/to/foo.db')
    engine = create_engine('sqlite:///C:\\path\\to\\foo.db')
    engine = create_engine(r'sqlite:///C:\path\to\foo.db')
    engine = create_engine('sqlite://')
    '''
    creator = None

    file = dbconf.get('database')
    url_args = get_url_kwargs(dbconf, )
    url = URL(drivername='sqlite', **url_args)

    if not file:
        PY2 = sys.version_info.major == 2
        if PY2:
            params = {}
        else:
            params = {'uri': True}

        url_args_list = ["%s=%s" % (k, v) for k, v in url_args.items()]
        url_args_str = ''
        if url_args_list:
            url_args_str="?%s" % '&'.join(url_args_list)
        creator_uri = 'file::memory:%s' % (url_args_str)
        creator = lambda: sqlite3.connect(creator_uri, **params)

    kwargs = get_rest_kwargs(dbconf, ignore=CONNECT_ARGS, )
    if creator:
        kwargs['creator'] = creator

    return url, kwargs


dialect_map = {
    'sqlite': sqlite_url,
    }


def get_rest_kwargs(dbconf, ignore=[], ):
    kwargs = dict([(k, v) for k, v in dbconf.items()
                   if k not in ignore])
    return kwargs


def get_url_kwargs(dbconf):
    kwargs = dict([(k, v) for k, v in dbconf.items()
                  if k in URL_ARGS and k != 'drivername'])
    return kwargs


class SQLAlchemyConf(object):
    def __init__(self, conf=None, root='DATABASES', database=None, expand=True, expand_map=None, quiet=False, echo=False, logger=None):
        global mlogger

        if logger:
            mlogger = logger
        self.conf = conf
        self.database = database
        self.dbconf = getdbinfo(conf=self.conf, root=root, database=self.database, expand=expand,
                                expand_map=expand_map, quiet=quiet)
        self.engine = None
        self.metadata = None
        self.session = None
        self.echo = echo

    def __repr__(self):
        return repr(self.dbconf)

    def get_info(self):
        return self.dbconf

    def get_url(self):
        dbconf = self.dbconf
        try:
            dialect = get_item(dbconf, 'dialect', )
        except Exception as e:
            raise Exception("dialect key missing in configuration for: %s." % (self.database)) from e

        func = dialect_map.get(dialect)

        if func:
            mlogger.debug('SQLAlchemyConf: specialized dialect map for {}: {}.'
                          .format(dialect, getattr(func, "__name__", repr(func))))
            url, kwargs = func(dbconf, self.database)
        else:
            mlogger.debug('SQLAlchemyConf: default SQLAlchemy mapping for {}.'.format(dialect))
            url_args = get_url_kwargs(dbconf, )
            try:
                url = URL(drivername=dialect, **url_args)
                # fetch other connection args (called query in sqlalchemy.engine.url.URL
            except Exception as e:
                raise Exception('Failed to create URL for : {}:{}.'
                                .format(dialect, url_args.get('drivername'))) from e
            kwargs = get_rest_kwargs(dbconf, ignore=CONNECT_ARGS, )
        mlogger.debug("SQLAlchemyConf: url: {}, kwargs: {}.".format(url, kwargs))
        return url, kwargs

    def get_engine(self, force=False,):
        if self.engine and not force:
            mlogger.debug("SQLAlchemyConf: engine already set and force is not set.")
            return self.engine
        mlogger.debug("SQLAlchemyConf: getting SQLAlchemy URL.")
        url, kwargs = self.get_url()
        self.engine = engine = create_engine(url, **kwargs, echo=self.echo)
        return engine

    def get_metadata(self, force=False):
        if self.metadata and not force:
            return self.metadata
        dbconf = self.dbconf
        engine = self.get_engine(force=force)
        schema = dbconf.get('schema')
        self.metadata = metadata = MetaData(bind=engine, schema=schema)
        return metadata

    def get_session(self, force=False, autocommit=True):
        if self.session and not force:
            return self.session
        session_factory = sessionmaker(bind=self.get_metadata(force=force).bind.engine,
                                       autocommit=autocommit)
        Session = scoped_session(session_factory)
        self.session = session = Session()
        # session=Session()
        return session


if __name__ == '__main__':
    dbconf = {
        "EVENTOR": {
            "DATABASES": {
                "default": {
                    "dialect": "sqlite",
                    "query": {
                        "cache": "shared"
                    },
                },
                "sqfile00": {
                    "dialect": "sqlite",
                    "database": "/var/acrisel/sand/eventor/eventor/eventor/examples/example00.db",
                },
                "pgdb1": {
                    "dialect": "postgresql",
                    "drivername": "psycopg2",
                    "username": "arnon",
                    "password": "arnon42",
                    "host": "localhost",
                    "port": 5433,
                    "database": "pyground",
                    "schema": "play",
                },
                "pgdb2": {"dialect": "postgresql",
                          "drivername": "psycopg2",
                          "username": "arnon",
                          "password": "arnon42",
                          "host": "192.168.1.70",
                          "port": 5432,
                          "database": "pyground",
                          "schema": "play",
                          }}}}

    for db in ['default', 'sqfile00', 'pgdb1', 'pgdb2', ]:
        sqlconf = SQLAlchemyConf(dbconf, root='EVENTOR.DATABASES', database=db)
        url, connect_args = sqlconf.get_url()
        print(db, url, connect_args)

    from .dbschema import info_table
    from sqlalchemy.ext.declarative import declarative_base
    sqlconf = SQLAlchemyConf(dbconf, root='EVENTOR.DATABASES', database='default', echo=True)
    metadata = sqlconf.get_metadata()
    engine = sqlconf.get_engine()
    Base = declarative_base(bind=engine, metadata=metadata)
    Info = info_table(Base)

    session = sqlconf.get_session(force=True, autocommit=False)
    # info_table = metadata.tables['Info']
    # print("Schema:", info_table.schema)

    # print("metadata tables:")
    # for name, table in metadata.tables.items():
    #        print("    {}: {}".format(name, table))

    metadata.create_all()
    # session.flush()
    # session.commit()

    data = {
        'app_version': '5.1.0',
        }
    for name, value in data.items():
        db_info = Info(run_id='test1', name=name, value=value)
        session.add(db_info)
    session.commit()
