'''
Created on Aug 26, 2017

@author: arnon
'''

from collections import namedtuple, Mapping
from namedlist import namedlist


def namedtuple_with_defaults(typename, field_names, default_values=()):
    T = namedtuple(typename, field_names)
    T.__new__.__defaults__ = (None,) * len(T._fields)
    if isinstance(default_values, Mapping):
        prototype = T(**default_values)
    else:
        prototype = T(*default_values)
    T.__new__.__defaults__ = tuple(prototype)
    return T

# MemEventor = namedtuple_with_defaults("MemEventor", ["steps", "events", "assocs", "delays", "kwargs"], (dict(), dict(), dict(), dict(), dict()))
# MemEventor = namedlist("MemEventor", [("steps", dict()), ("events", dict()), ("assocs", dict()), ("delays", dict()), ("kwargs", dict()), ("logger_info", None)])


class MemEventor(object):
    def __init__(self):
        self.steps = dict()
        self.events = dict()
        self.assocs = dict()
        self.delays = dict()
        self.kwargs = dict()
        self.logger_info = None

    def __repr__(self):
        result = ['Steps:']
        result.append('    {}'.format(', '.join([name for name in self.steps.keys()])))
        result.append('Events:')
        result.append('    {}'.format(', '.join([name for name in self.events.keys()])))
        return '\n'.join(result)


if '__main__' == __name__:
    mem = MemEventor()
    mem.steps["ad"] = 23
    mem.events['ty'] = 45

    print(mem)
