'''
Created on Jan 31, 2014

@author: arnon
'''
import os
import re
import collections
from copy import copy
from acrilib import FlatDict
from pprint import pprint

_varprog = re.compile(r'\$(\w+|(\{[^\}]*})|(\[[^]]*\]))')
_varprogb = None


def expandvars(map_, environ=None):
    """Expand variables in flat dictionary.

    Args:
        source: flat dictionary
        environ: environment dictionary; defaults for os.environ

    Arlgorithm:
        expands ${} from environment
        expands $[] from flat names; e.g. $[EVENTOR.LOGGING.PATH]

    Returns:
        New flat dict with expanded vars.
    """
    nmap_ = type(map_)()
    if environ is None:
        environ = os.environ

    smap = find_iner_dependencies(map_)

    for k, v in list(smap.items()):
        ev = expandvar(v, environ, nmap_)
        nmap_[k] = ev

    return nmap_


def calculate_ranks(depends, rank):
    def calc_rank(k, d):
        if len(d) == 0:
            result = 0
        elif rank[k] > 0:
            result = rank[k]
        else:
            result = sum([calc_rank(i, depends[i]) for i in d])
        return result

    for k, d in depends.items():
        if d and rank[k] == 0:
            rank[k] = calc_rank(k, d)
    return rank


def find_iner_dependencies(map_):
    global _varprog
    
    depends = dict()
    no_depends = dict()
    for k, v in list(map_.items()):
        if not isinstance(v, str):
            no_depends[k] = v
            continue
        matchiter = _varprog.finditer(v)
        names = list()
        for m in matchiter:
            name = m.group(0)[1:]
            if name[0] == '[':
                names.append(name[1:-1])
        depends[k] = names

    rank = calculate_ranks(depends, dict([(k, 0) for k in depends.keys()]))

    combined = zip(sorted(rank.items(), key=lambda x: x[0]), sorted(depends.items(), key=lambda x: x[0]))
    combined = sorted(combined, key=lambda x: x[0][1])
    map_ = collections.OrderedDict([(rank[0], map_[rank[0]]) for rank, dependes in combined])
    map_.update(no_depends)
    return map_


def expandvar(source, environ=None, map_=None):
    """Expand shell variables of form $var and ${var}.  Unknown variables
    are left unchanged.

    Args:
        source: flat dictionary
        environ: environment dictionary; defaults for os.environ

    Arlgorithm:
        expands ${} from environment
        expands $[] from flat names; e.g. $[EVENTOR.LOGGING.PATH]

    Returns:
        New flat dict with expanded vars.
    """
    global _varprog

    if source is None or not isinstance(source, str):
        return source

    if environ is None:
        environ = os.environ
        # os.path.expandvars(path)

    if isinstance(source, bytes):
        source = source.decode()

    if source.startswith('~') or source.startswith('/~'):
        source = os.path.expanduser(source)

    if '$' not in source:
        return source

    matchiter = _varprog.finditer(source)

    for m in matchiter:
        start, end = m.span(0)
        name = m.group(0)[1:]
        if name[0] in ['{', '[']:
            varname = name[1:-1]
            typename = name[0]
        else:
            varname = name
            typename = '{'

        if typename == '{':
            env = environ
        else:
            env = map_

        try:
            value = str(env[varname])
        except KeyError:
            pass
        else:
            source = source[:start] + value + source[end:]

    return source


def pathhasvars(source):
    """Expand shell variables of form $var and ${var}.  Unknown variables
    are left unchanged."""
    global _varprog, _varprogb
    if isinstance(source, bytes):
        if b'$' not in source:
            return False
        if not _varprogb:
            import re
            # _varprogb = re.compile(br'\$(\w+|\{[^}]*\})', re.ASCII)
            _varprogb = re.compile(br'\$(\w+|\{[^}]*\})')
        search = _varprogb.search
        start = b'{'
        end = b'}'
    else:
        if '$' not in source:
            return False
        if not _varprog:
            import re
            # _varprog = re.compile(r'\$(\w+|\{[^}]*\})', re.ASCII)
            _varprog = re.compile(r'\$(\w+|\{[^}]*\})')
        search = _varprog.search
        start = '{'
        end = '}'
    i = 0
    m = search(source, i)
    return not (not m)


def expandmap(map_, expand_map=None):
    ''' Expands path variables ${}
    '''
    if not expand_map:
        expand_map = copy(os.environ)
    else:
        expand_map = copy(expand_map)

    flat = FlatDict()(map_)

    fmap = expandvars(flat)

    nmap = fmap.unflat()
    return nmap


if __name__ == '__main__':
    from pprint import pprint

    print(expandvar("~/log/environ"))

    config = {
        'workdir': '/tmp',
        'debug': False,
        'task_construct': 'process',  # or 'thread'
        'envvar_prefix': 'EVENTOR_',
        'max_concurrent': -1,
        'stop_on_exception': True,
        'sleep_between_loops': 0.25,
        'sequence_arg_name': None,  # 'eventor_task_sequence'
        'day_to_keep_db': 5,
        'remote_method': 'ssh',
        'pass_logger_to_task': False,
        'shared_db': False,
        'ssh_config': os.path.expanduser('~/.ssh/config'),
        'ssh_host': 'get_hostname()',
        'ssh_port': 22,
        'DATABASES': {'dialect': 'sqlite', 'query': {'cache': 'shared'}},
        'LOGGING': {
            'logdir': os.path.expanduser('~/log/eventor'),
            'datefmt': '%Y-%m-%d,%H:%M:%S.%f',
            'logging_level': 'logging.INFO',
            'level_formats': {
                'logging.DEBUG': ("[ %(asctime)-15s ][ %(host)s ][ %(processName)-11s ]"
                                  "[ %(levelname)-7s ][ %(message)s ]"
                                  "[ %(module)s.%(funcName)s(%(lineno)d) ]"),
                'default': ("[ %(asctime)-15s ][ %(host)s ][ %(processName)-11s ]"
                            "[ %(levelname)-7s ][ %(message)s ]"),
                },
            'consolidate': False,
            'console': True,
            'file_prefix': None,
            'file_suffix': None,
            'file_mode': 'a',
            'maxBytes': 0,
            'backupCount': 0,
            'encoding': 'utf8',
            'delay': False,
            'when': 'h',
            'interval': 1,
            'utc': False,
            'atTime': 86400,  # number of seconds in a day
        },
    }

    pprint(expandmap(config))