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
import subprocess

'''
Prerequisite:

    set .profile with:
    
        source /var/venv/eventor/bin/activate
        
    add to authorized_keys proper key:
    
        command=". ~/.profile; if [ -n \"$SSH_ORIGINAL_COMMAND\" ]; 
        then eval \"$SSH_ORIGINAL_COMMAND\"; else exec \"$SHELL\"; fi" ssh-rsa ... 
'''

class SshAgent(object):
    def __init__(self, host, agentpy):
        try:
            self.remote = sshcmd(host, "python " + agentpy,)
        except Exception as e:
            raise
        self.qrequest = mp.Queue()
        self.qresouse = mp.Queue()

    def prepare_msg(self, msg):
        workload = pickle.dumps(msg)
        msgsize = len(workload)
        magsize_packed = struct.pack(">L", msgsize)
        return magsize_packed + workload
    
    def send(self, msg):
        request = self.prepare_msg(msg)
        self.remote.stdin.write(request)
        
    def close(self):
        self.send('Terminate')
        response = self.remote.communicate()
        return response
        

if __name__ == '__main__':
    mp.set_start_method('spawn')
    
    agent_dir = "/var/acrisel/sand/eventor/eventor/eventor/concepts"
    agentpy = os.path.join(agent_dir, "sshagent_popen_pipe.py")
    host='192.168.1.100'
    #host='172.31.99.104'
    sshagent = SshAgent(host, agentpy)
    
    worker = RemoteWorker()
    sshagent.send(worker)
    sshagent.send(worker)
    
    response = sshagent.close()
    print('response: ', response)
    

