'''
Created on Sep 3, 2017

@author: arnon
'''

import inspect

class A(object):
    def do(self):
        frames = inspect.stack()
        frame = frames[1]
        #caller = inspect.getframeinfo(caller_frame)
        print(frame)
        
def caller():
    a = A()
    a.do()
    
caller()