'''
Created on Aug 31, 2017

@author: arnon
'''

import pickle
import multiprocessing as mp

class MyClass(object):
    def __init__(self):
        self.a=4
    
    def func(self):
        print(self.a)
        
    def run(self):
        pickle.dumps(self.func)
        
myc = MyClass()
myc.run()