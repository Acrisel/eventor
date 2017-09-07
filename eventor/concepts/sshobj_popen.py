'''
Created on Aug 27, 2017

@author: arnon
'''

from concepts.sshcmd_popen import sshcmd
import pickle
import os
from concepts.sshtypes import RemoteWorker
import struct
import multiprocessing as mp
import sys
from subprocess import Popen, PIPE
import threading as th
import queue

'''
Prerequisite:

    set .profile with:
    
        source /var/venv/eventor/bin/activate
        
    add to authorized_keys proper key:
    
        command=". ~/.profile; if [ -n \"$SSH_ORIGINAL_COMMAND\" ]; 
        then eval \"$SSH_ORIGINAL_COMMAND\"; else exec \"$SHELL\"; fi" ssh-rsa ... 
'''

def stdbin_decode(value, encodeing='ascii'):
    value = value.decode()
    if value.endswith('\n'):
        value = value[:-1]
    return value


class SSHAGENTERROR(Exception): pass


class SshAgent(object):
    def __init__(self, host, command, user=None, logger=None):
        
        self.logger = logger
        if logger:
            self.__debug = self.logger.debug
            self.__critical = self.logger.critical
            self.__excetion = self.logger.exception
        else:
            self.__debug = print
            self.__critical = print
            self.__excetion = print

        where = "%s%s" % ('' if user is None else "@%s" % user, host)
        ssh_command = ["ssh", where, 'python', command]
        self.__debug("Starting popen with: %s" % ssh_command)
        self.sshproc = Popen(ssh_command, shell=False, stdin=PIPE, stdout=PIPE, stderr=PIPE, close_fds=False,)
        
        self.__closeq = mp.Queue()
        self.__debug("Starting close watchdog.")
        self.__closeth = th.Thread(target=self.__wait, args=(self.__closeq, ))
        self.__closeth.start()
        
        # set stderr as none blocking
        #fl = fcntl.fcntl(self.stderr, fcntl.F_GETFL)
        #fcntl.fcntl(self.stderr, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        
    def is_alive(self):
        return self.__closeth.is_alive()
            
    def prepare(self, msg, pickle_msg=True):
        workload = msg
        if pickle_msg:
            workload = pickle.dumps(msg)
        msgsize = len(workload)
        magsize_packed = struct.pack(">L", msgsize)
        return magsize_packed + workload
    
    def send(self, msg, pickle_msg=True):
        request = self.prepare(msg, pickle_msg=pickle_msg)
        self.sshproc.stdin.write(request)
        
    def __wait(self, closeq):
        response = self.sshproc.communicate()
        closeq.put(self.sshproc.returncode, response[0], response[1])
        
    def close(self):
        self.send('TERM', pickle_msg=True)
        #self.wait()
        response = self.__closeq.get()
        return response
        
         

if __name__ == '__main__':
    mp.set_start_method('spawn')
    import signal
    
    agent_dir = "/var/acrisel/sand/eventor/eventor/eventor/concepts"
    agentpy = os.path.join(agent_dir, "sshagent_popene.py")
    host='192.168.1.100'
    #host='172.31.99.104'
    sshagent = SshAgent(host, agentpy)
    
    print("checking if alive.")
    result = sshagent.is_alive()
    if not result: 
        print("Dead 1:", sshagent.close())
        exit()
    
    worker = RemoteWorker()
    print('Sending worker.')
    sshagent.send(worker)
    
    #sshagent.send_signal(signal.SIGTERM)

    print("checking if alive.")
    result = sshagent.is_alive()
    if not result: 
        print("Dead 2:", sshagent.close())
        exit()

    print('Sending worker.')
    sshagent.send(worker)
    
    print('closing.')
    response = sshagent.close()
    print('response: ', response)
    

