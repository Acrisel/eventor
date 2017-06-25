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

def getconfdict(conf=None, root='', expand=True, expand_map=None):
    result=conf
    if root is not None:
        for key in root.split('.'):
            result=result.get(key, result.get(key.swapcase(), result))
    if expand:
        result=expandmap(result, expand_map=expand_map)
    
    return result


def getconfstr(conf=None, root=None, expand=True, expand_map=None):
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
    result=getconfdict(conf=content, root=root, expand=expand, expand_map=expand_map)
    return result


def getconffile(conf=None, root=None, expand=True, expand_map=None):
    '''file object opened to read: read file text and treat as str.
    '''
    text=conf.read()
    return getconfstr(conf=text, root=root, expand=expand, expand_map=expand_map)

type_map={
    'dict': getconfdict,
    'MergedChainedDict': getconfdict,
    'str': getconfstr,
    'file': getconffile,
    }


def getrootconf(conf=None, root=None, expand=True, expand_map=None):
    '''Translate configuration into sqlalchemy url
    
    Args:
        conf: dictionary, text, filename, or 
    '''
    
    type_=type(conf).__name__
    try:
        func=type_map.get(type_)
    except Exception as e:
        raise Exception('unhandled conf type: %s, allow %s.' %(type_, repr(list(type_map.keys())))) from e
    
    rootconf=func(conf=conf, root=root, expand=expand, expand_map=expand_map)
    
    return rootconf    

if __name__ == '__main__':
    from pprint import pprint
    pprint(getrootconf('db.conf', 'default'))
    pprint(getrootconf(conf='db.conf', root='playpg'))
    pprint(getrootconf(conf='db.conf', root='playmem'))
    pprint(getrootconf(conf='db.conf', root='playfile'))
    pprint(getrootconf('db.conf', 'playmy'))

    