'''
Created on Aug 26, 2017

@author: arnon
'''

from collections import namedtuple, Mapping

def namedtuple_with_defaults(typename, field_names, default_values=()):
    T = namedtuple(typename, field_names)
    T.__new__.__defaults__ = (None,) * len(T._fields)
    if isinstance(default_values, Mapping):
        prototype = T(**default_values)
    else:
        prototype = T(*default_values)
    T.__new__.__defaults__ = tuple(prototype)
    return T

MemEventor = namedtuple_with_defaults("MemEventor", ["steps", "events", "assocs", "delays", "kwargs"], (dict(), dict(), dict(), dict(), dict()))


if '__main__' == __name__:
    mem=MemEventor()
    mem.steps["ad"]=23
    mem.events['ty']=45
    
    print(mem)