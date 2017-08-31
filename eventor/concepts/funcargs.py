'''
Created on Aug 30, 2017

@author: arnon
'''

p = 7

class MyClass(object):
    l = 56
    
    def __init__(self, a, b):
        global p
        kwargs = locals()
        del kwargs['self']
        print(kwargs)
        y=5
        print(kwargs)
        print(locals())
        
m=MyClass(3,4)