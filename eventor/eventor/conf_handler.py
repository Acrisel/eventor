'''
Created on Jun 20, 2017

@author: arnon
'''

import os
import yaml
import logging
from eventor.expandvars import expandvars

logger=logging.getLogger(__file__)


from collections import Mapping

def keys2lower(map_):
    ''' Build the same dict but with keys in lower case
    '''
    if not isinstance(map_, Mapping): return map_
    
    type_=type(map_)
    nmap=type_([(k.lower(), keys2lower(v)) for k,v in map_.items()])
    return nmap

def expandmap(map_, expand_map=None):
    ''' Build the same dict but with keys in lower case
    '''
    if not expand_map:
        expand_map=os.environ
    
    type_=type(map_)
    nmap=type_([(k, expandvars(v, expand_map)) for k,v in map_.items()])
    return nmap

def getconfdict(conf=None, key='', expand=True, expand_map=None):
    ''' dive in dict (conf) according to key (=key1.key2...keyn)
    
    Args:
        conf: Mapping configuration.
        key: string of key.  If hierarchical, hierarchy is separated by '.'
        expand: expands variable values ($VAR or ${VAR}) according to expan_map (os.environ if not provided)
        
    Return:
        dict part implied by key or empty dict if not found.
    '''
    result = conf
    if key is not None:
        for k in key.split('.'):
            try:
                result = result.get(k, result.get(k.lower(), {}))
            except Exception as e:
                raise Exception("Failed to find key in config: %s, %s" %(key, conf))
    if expand:
        result = expandmap(result, expand_map=expand_map)
    
    return result


def getconfstr(conf=None, key=None, expand=True, expand_map=None):
    ''' YAML text or name of file.
    '''
    
    # try first as file
    path=os.path.abspath(conf)
    if os.path.isfile(path):
        with open(path, 'r') as f:
            text=f.read()
    else:
        text=conf
        
    content=yaml.load(text)
    result=getconfdict(conf=content, key=key, expand=expand, expand_map=expand_map)
    return result


def getconffile(conf=None, key=None, expand=True, expand_map=None):
    '''file object opened to read: read file text and treat as str.
    '''
    text=conf.read()
    return getconfstr(conf=text, key=key, expand=expand, expand_map=expand_map)

type_map={
    'MergedChainedDict': getconfdict,
    'str': getconfstr,
    'file': getconffile,
    }


def getrootconf(conf=None, root=None, expand=True, expand_map=None):
    '''Translate configuration into sqlalchemy url
    
    Args:
        conf: dictionary, text, filename, or 
    '''
    
    type_ = type(conf).__name__
    try:
        func = type_map[type_]
    except Exception as e:
        if isinstance(conf, Mapping):
                func = getconfdict
        else:
            raise Exception('unhandled conf type: %s, allow %s.' %(type_, repr(list(type_map.keys())))) from e
    
    rootconf = func(conf=conf, key=root, expand=expand, expand_map=expand_map)
    
    return rootconf    

if __name__ == '__main__':
    from pprint import pprint
    dbconf={
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
                    "database": "/var/acrisel/sand/eventor/eventor/eventor/examples/example00.db"  
                },
                "pgdb1": {
                    "dialect": "postgresql",
                    "drivername" : "psycopg2",
                    "username": "arnon",
                    "password": "arnon42",
                    "host": "localhost",
                    "port": 5433,
                    "database": "pyground",
                    "schema": "play",
                },
                "pgdb2": {
                    "dialect": "postgresql",
                    "drivername" : "psycopg2",
                    "username": "arnon",
                    "password": "Chompi42",
                    "host": "192.168.1.70",
                    "port": 5432,
                    "database": "pyground",
                    "schema": "play",
                },

        }}}
    pprint(getrootconf(dbconf, 'EVENTOR.DATABASES.default'))
    pprint(getrootconf(conf=dbconf, root='EVENTOR.DATABASES.playpg'))
    pprint(getrootconf(conf=dbconf, root='EVENTOR.DATABASES.playmem'))
    pprint(getrootconf(conf=dbconf, root='EVENTOR.DATABASES.playfile'))
    pprint(getrootconf(dbconf, 'EVENTOR.DATABASES.pgdb2'))

    