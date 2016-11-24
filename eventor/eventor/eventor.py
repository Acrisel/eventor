'''
Created on Nov 23, 2016

@author: arnon
'''

import logging
from acris import Sequence, MpLogger
import multiprocessing as mp
from collections import ChainMap
import os

module_logger=logging.getLogger(__name__)

class Eventor(object):
    """Eventor manages events and steps that needs to be taken when raised.
    
    Eventor provides programming interface to create events, steps and associations among them.
    It provides means to raise events, and a service that would perform steps according to those events. 
        
        :func:__init__()
              :param start: instruct Steps how to start (resume, restart)
              :param workdir: path to folder where 
              :type start: gradior.Start enumerator value
              :type workdir: type description
              :return: Steps object
              :rtype: Steps
         
        :func:add_step()
              :param start: instruct Steps how to start (resume, restart)
              :param workdir: path to folder where 
              :type start: gradior.Start enumerator value
              :type workdir: type description
              :return: Steps object
              :rtype: Steps
         
        :func:add_event()
              :param start: instruct Steps how to start (resume, restart)
              :param workdir: path to folder where 
              :type start: gradior.Start enumerator value
              :type workdir: type description
              :return: Steps object
              :rtype: Steps
         
        :func:start() 
              :return: Steps object
              :rtype: Steps    
    
        :Example:
    
              followed by a blank line !
    
          which appears as follow:
    
          :Example:
    
          followed by a blank line
    
        - Finally special sections such as **See Also**, **Warnings**, **Notes**
          use the sphinx syntax (*paragraph directives*)::
    
              .. seealso:: blabla
              .. warnings also:: blabla
              .. note:: blabla
              .. todo:: blabla
    
        .. note::
            There are many other Info fields but they may be redundant:
                * param, parameter, arg, argument, key, keyword: Description of a
                  parameter.
                * type: Type of a parameter.
                * raises, raise, except, exception: That (and when) a specific
                  exception is raised.
                * var, ivar, cvar: Description of a variable.
                * returns, return: Description of the return value.
                * rtype: Return type.
    
        .. note::
            There are many other directives such as versionadded, versionchanged,
            rubric, centered, ... See the sphinx documentation for more details.
    
        Here below is the results of the :func:`function1` docstring.
    
    """
    defaults={'workdir':'/tmp', 
              'logdir': '/tmp', 
              'task_construct': mp.Process, 
              'max_parallel': -1, 
              'stop_on_exception': True,
              'sleep_between_loops': 1,
          }    
        
    def __init__(self, name='', config={}):
        self.evr_name=name
        self.config=ChainMap(config, os.environ, Eventor.defaults) 
        
    def add_event(self, name,):
        pass
    
    def add_step(self, name, func, args=(), kwargs={}):
        pass
    
    def add_assoc(self, event, atype, aobj):
        pass
    
    def trigger_event(self, event, sequence):
        pass
    
    def loop_once(self):
        pass
    
    def start_endless_loop(self):
        pass
    
    def stop_endless_loop(self):
        pass